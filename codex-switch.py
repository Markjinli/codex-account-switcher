#!/usr/bin/env python3
"""Codex Account Switcher — cross-platform profile manager for Codex CLI accounts.

Switches the entire ~/.codex directory so every piece of data follows the account:
auth, config, sessions, memories, plugins, skills, cache, logs, and state.
"""

import os
import sys
import json
import shutil
import argparse
import stat
import time
import subprocess
import base64
from pathlib import Path
from datetime import datetime

CODEX_DIR = Path.home() / ".codex"
SWITCHER_DIR = Path.home() / ".codex-switcher"
PROFILES_DIR = SWITCHER_DIR / "profiles"
STATE_FILE = SWITCHER_DIR / "state.json"


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def ensure_dirs():
    SWITCHER_DIR.mkdir(parents=True, exist_ok=True)
    PROFILES_DIR.mkdir(parents=True, exist_ok=True)


def load_state():
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return {}
    return {}


def save_state(state):
    STATE_FILE.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")


def get_account_info(codex_dir=CODEX_DIR):
    """Extract account email + id from a codex directory."""
    auth_file = codex_dir / "auth.json"
    if not auth_file.exists():
        return None, None
    try:
        auth = json.loads(auth_file.read_text(encoding="utf-8"))
        tokens = auth.get("tokens", {})
        email = None
        id_token = tokens.get("id_token", "")
        if id_token:
            try:
                payload = id_token.split(".")[1]
                payload += "=" * (4 - len(payload) % 4)
                decoded = json.loads(base64.urlsafe_b64decode(payload).decode("utf-8"))
                email = decoded.get("email")
            except Exception:
                pass
        account_id = tokens.get("account_id", "unknown")
        return email or "unknown", account_id
    except Exception:
        return None, None


def is_codex_running():
    """Check whether Codex processes are alive (Windows: Codex Proxy.exe, Mac: codex)."""
    try:
        if sys.platform == "win32":
            result = subprocess.run(["tasklist", "/NH"], capture_output=True, text=True)
            return "codex" in result.stdout.lower()
        else:
            result = subprocess.run(["pgrep", "-i", "-x", "codex"],
                                    capture_output=True, text=True)
            return result.returncode == 0
    except Exception:
        return False


def kill_codex():
    """Force-stop all Codex processes."""
    try:
        if sys.platform == "win32":
            subprocess.run(["taskkill", "/F", "/FI", "IMAGENAME eq Codex Proxy.exe"],
                           capture_output=True, text=True)
            subprocess.run(["taskkill", "/F", "/FI", "IMAGENAME eq codex.exe"],
                           capture_output=True, text=True)
        else:
            subprocess.run(["pkill", "-9", "-i", "codex"],
                           capture_output=True, text=True)
    except Exception:
        pass


def _remove_readonly(fn, path, excinfo):
    """shutil.rmtree onerror handler — clear read-only flag and retry."""
    try:
        os.chmod(path, stat.S_IWRITE)
        fn(path)
    except Exception:
        pass


def rmtree_force(path: Path):
    """rmtree that handles Windows read-only files (e.g. .git pack files)."""
    if not path.exists():
        return
    shutil.rmtree(str(path), onerror=_remove_readonly, ignore_errors=True)


# Directories that are safe to skip — cached or derived data that Codex
# rebuilds automatically.  Skipping these avoids Windows file-lock issues
# with read-only .git pack files inside vendor_imports.
SKIP_DIRS = {".tmp", ".sandbox-secrets", ".sandbox", "vendor_imports", "tmp"}


def copy_codex_tree(src: Path, dst: Path):
    """Replace dst contents with a clean copy of src.

    Copies src to a temp directory, then moves children into dst one-by-one.
    Directories in SKIP_DIRS are excluded — they contain cache/derived data
    that Codex regenerates on next launch.
    """
    tmp = dst.with_name(dst.name + ".tmp-" + str(int(time.time() * 1000)))

    def _ignore(root, names):
        return [n for n in names if n in SKIP_DIRS]

    rmtree_force(tmp)
    shutil.copytree(str(src), str(tmp), symlinks=False,
                    ignore_dangling_symlinks=True, ignore=_ignore)

    dst.mkdir(parents=True, exist_ok=True)
    for child in tmp.iterdir():
        target = dst / child.name
        rmtree_force(target)
        try:
            shutil.move(str(child), str(target))
        except OSError:
            if child.is_dir():
                shutil.copytree(str(child), str(target), symlinks=False,
                                ignore_dangling_symlinks=True, dirs_exist_ok=True,
                                ignore=_ignore)
            else:
                shutil.copy2(str(child), str(target))
            rmtree_force(child)
    rmtree_force(tmp)


# ---------------------------------------------------------------------------
# commands
# ---------------------------------------------------------------------------

def cmd_current():
    """Show the currently active Codex account."""
    if not CODEX_DIR.exists():
        print("Codex directory not found at", str(CODEX_DIR))
        return

    email, account_id = get_account_info()
    state = load_state()

    print(f"  Account : {email}")
    print(f"  ID      : {account_id}")
    if state.get("current_profile"):
        print(f"  Profile : {state['current_profile']}")
        print(f"  Switched: {state.get('last_switch', 'unknown')}")


def cmd_list():
    """List all saved profiles (excluding auto-backups)."""
    ensure_dirs()
    profiles = sorted(PROFILES_DIR.iterdir()) if PROFILES_DIR.exists() else []
    profiles = [p for p in profiles if not p.name.startswith("_auto_")]
    if not profiles:
        print("No saved profiles. Use 'save <name>' to save the current account.")
        return

    current_email, _ = get_account_info()
    state = load_state()
    active_name = state.get("current_profile", "")

    print(f"{'':-<60}")
    print(f"  {'PROFILE':<20} {'ACCOUNT':<30} {'STATUS'}")
    print(f"{'':-<60}")
    for p in profiles:
        em, _ = get_account_info(p)
        marker = ""
        if p.name == active_name and em == current_email:
            marker = " * active"
        elif em == current_email:
            marker = " * current"
        print(f"  {p.name:<20} {em or 'unknown':<30}{marker}")
    print(f"{'':-<60}")


def cmd_save(name: str):
    """Save the current .codex directory as a named profile."""
    if not CODEX_DIR.exists():
        print("Nothing to save — .codex directory does not exist.")
        sys.exit(1)

    email, _ = get_account_info()
    if not email or email == "unknown":
        print("Warning: could not determine account email from auth.json.")

    ensure_dirs()
    dst = PROFILES_DIR / name
    print(f"Saving current account ({email}) -> profile '{name}' ...")
    copy_codex_tree(CODEX_DIR, dst)

    state = load_state()
    state.setdefault("profiles", {})
    state["profiles"][name] = {
        "email": email,
        "saved_at": datetime.now().isoformat(),
    }
    state["current_profile"] = name
    save_state(state)

    print(f"Done. Profile '{name}' saved ({email}).")


def cmd_switch(name: str):
    """Switch to a saved profile. Auto-stops Codex if running."""
    src = PROFILES_DIR / name
    if not src.exists():
        print(f"Profile '{name}' not found. Use 'list' to see available profiles.")
        sys.exit(1)

    if is_codex_running():
        print("Stopping Codex before switching ...")
        kill_codex()
        time.sleep(0.5)

    # auto-save current as safety net
    auto_name = None
    if CODEX_DIR.exists():
        email, _ = get_account_info()
        if email and email != "unknown":
            auto_name = f"_auto_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            print(f"Auto-saving current state -> {auto_name} ...")
            copy_codex_tree(CODEX_DIR, PROFILES_DIR / auto_name)

    # swap
    print(f"Restoring profile '{name}' ...")
    copy_codex_tree(src, CODEX_DIR)

    state = load_state()
    state["current_profile"] = name
    state["last_switch"] = datetime.now().isoformat()
    if auto_name:
        state.setdefault("auto_backups", []).append(auto_name)
    save_state(state)

    new_email, _ = get_account_info()
    print(f"Switched to '{name}' ({new_email}).")


def cmd_delete(name: str):
    """Delete a saved profile."""
    src = PROFILES_DIR / name
    if not src.exists():
        print(f"Profile '{name}' does not exist.")
        sys.exit(1)

    email, _ = get_account_info(src)
    print(f"Delete profile '{name}' ({email})? [y/N] ", end="")
    answer = input().strip().lower()
    if answer not in ("y", "yes"):
        print("Cancelled.")
        return

    shutil.rmtree(src, ignore_errors=True)
    state = load_state()
    state.get("profiles", {}).pop(name, None)
    if state.get("current_profile") == name:
        state.pop("current_profile", None)
    save_state(state)
    print("Deleted.")


def cmd_diff(name: str = None):
    """Compare current account with a saved profile."""
    if name:
        src = PROFILES_DIR / name
        if not src.exists():
            print(f"Profile '{name}' not found.")
            sys.exit(1)
    else:
        src = None

    email, aid = get_account_info()
    print(f"Current account: {email} ({aid})")

    if src:
        p_email, p_aid = get_account_info(src)
        print(f"Profile '{name}': {p_email} ({p_aid})")

    if CODEX_DIR.exists():
        current_size = sum(f.stat().st_size for f in CODEX_DIR.rglob("*") if f.is_file())
        print(f"\nCurrent .codex size: {current_size / 1024 / 1024:.1f} MB")
    if src and src.exists():
        profile_size = sum(f.stat().st_size for f in src.rglob("*") if f.is_file())
        print(f"Profile .codex size:  {profile_size / 1024 / 1024:.1f} MB")


def cmd_clean_autos():
    """Remove auto-backup profiles to free disk space."""
    state = load_state()
    autos = state.get("auto_backups", [])
    removed = 0
    for name in autos:
        p = PROFILES_DIR / name
        if p.exists():
            shutil.rmtree(p, ignore_errors=True)
            removed += 1
    # also clean any orphaned _auto_ dirs not in state
    for p in PROFILES_DIR.glob("_auto_*"):
        rmtree_force(p)
        removed += 1
    state["auto_backups"] = []
    save_state(state)
    if removed:
        print(f"Removed {removed} auto-backup(s).")
    else:
        print("No auto-backups to clean.")


def cmd_logout():
    """Clear current login state so you can log into a different account."""
    auth_file = CODEX_DIR / "auth.json"
    if not auth_file.exists():
        print("No auth.json found — already logged out.")
        return

    email, _ = get_account_info()
    print(f"Current account: {email}")
    print("This will clear the login state so you can sign in with a new account.")
    print(f"Proceed? [y/N] ", end="")
    answer = input().strip().lower()
    if answer not in ("y", "yes"):
        print("Cancelled.")
        return

    if is_codex_running():
        print("Stopping Codex ...")
        kill_codex()
        time.sleep(0.5)

    to_delete = [
        "auth.json",
        ".codex-global-state.json",
        ".codex-global-state.json.bak",
    ]
    for f in to_delete:
        p = CODEX_DIR / f
        if p.exists():
            p.unlink(missing_ok=True)

    sessions_dir = CODEX_DIR / "sessions"
    if sessions_dir.exists():
        shutil.rmtree(sessions_dir, ignore_errors=True)

    print("Login state cleared. Run 'codex login' to sign in with a new account.")
    print("After login, use 'codex-switch save <name>' to save the new profile.")


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Codex Account Switcher — switch between Codex CLI accounts.",
        prog="codex-switch"
    )
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("current", help="Show current logged-in account")
    sub.add_parser("list", help="List all saved profiles")

    p_save = sub.add_parser("save", help="Save current account as a profile")
    p_save.add_argument("name", help="Profile name (e.g. personal, work)")

    p_switch = sub.add_parser("switch", help="Switch to a saved profile")
    p_switch.add_argument("name", help="Profile name to switch to")

    p_del = sub.add_parser("delete", help="Delete a saved profile")
    p_del.add_argument("name", help="Profile name to delete")

    p_diff = sub.add_parser("diff", help="Compare current account with a profile")
    p_diff.add_argument("name", nargs="?", help="Profile name (omit to show current only)")

    sub.add_parser("clean", help="Remove auto-backup profiles")
    sub.add_parser("logout", help="Clear login state to switch to a new account")

    args = parser.parse_args()

    if not args.command:
        print("=== Codex Account Switcher ===\n")
        if CODEX_DIR.exists():
            cmd_current()
            print()
        cmd_list()
        return

    cmds = {
        "current": cmd_current,
        "list": cmd_list,
        "save": lambda: cmd_save(args.name),
        "switch": lambda: cmd_switch(args.name),
        "delete": lambda: cmd_delete(args.name),
        "diff": lambda: cmd_diff(args.name),
        "clean": cmd_clean_autos,
        "logout": cmd_logout,
    }
    cmds[args.command]()


if __name__ == "__main__":
    main()
