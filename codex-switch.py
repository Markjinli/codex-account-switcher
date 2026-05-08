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
    """Extract account email + id from a codex directory. Returns (email, account_id) or (None, None)."""
    auth_file = codex_dir / "auth.json"
    if not auth_file.exists():
        return None, None
    try:
        auth = json.loads(auth_file.read_text(encoding="utf-8"))
        tokens = auth.get("tokens", {})
        # id_token is a JWT — try decoding the payload for email
        id_token = tokens.get("id_token", "")
        email = None
        if id_token:
            try:
                import base64
                payload = id_token.split(".")[1]
                # fix padding
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
    """Best-effort check whether codex processes are alive."""
    import subprocess
    try:
        if sys.platform == "win32":
            result = subprocess.run(
                ["tasklist", "/FI", "IMAGENAME eq codex.exe", "/NH"],
                capture_output=True, text=True
            )
            return "codex.exe" in result.stdout.lower()
        else:
            result = subprocess.run(["pgrep", "-x", "codex"], capture_output=True, text=True)
            return result.returncode == 0
    except Exception:
        return False


def copy_codex_tree(src: Path, dst: Path):
    """Robust recursive copy. dst is removed first if it exists."""
    if dst.exists():
        shutil.rmtree(dst, ignore_errors=True)
    shutil.copytree(src, dst, symlinks=False, ignore_dangling_symlinks=True,
                    ignore=shutil.ignore_patterns(".tmp", ".sandbox-secrets"))


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
    """List all saved profiles."""
    ensure_dirs()
    profiles = sorted(PROFILES_DIR.iterdir()) if PROFILES_DIR.exists() else []
    if not profiles:
        print("No saved profiles. Use 'save <name>' to save the current account.")
        return

    current_email, _ = get_account_info()
    state = load_state()
    active_name = state.get("current_profile", "")

    print(f"{'':-<60}")
    print(f"  {'PROFILE':<20} {'ACCOUNT':<30} {'ACTIVE'}")
    print(f"{'':-<60}")
    for p in profiles:
        em, _ = get_account_info(p)
        marker = " * current" if em == current_email else ""
        if p.name == active_name:
            marker = " * active profile" + marker.replace("* current", "")
        elif em == current_email and not marker:
            marker = "   (current)"
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
    print(f"Saving current account ({email}) → profile '{name}' ...")
    copy_codex_tree(CODEX_DIR, dst)

    # update metadata
    state = load_state()
    state.setdefault("profiles", {})
    state["profiles"][name] = {
        "email": email,
        "saved_at": datetime.now().isoformat(),
    }
    state["current_profile"] = name
    save_state(state)

    print("Done. Profile '%s' saved (%s)." % (name, email))


def cmd_switch(name: str):
    """Switch to a previously saved profile."""
    src = PROFILES_DIR / name
    if not src.exists():
        print(f"Profile '{name}' not found. Use 'list' to see available profiles.")
        sys.exit(1)

    if is_codex_running():
        print("⚠  Codex appears to be running. Please quit Codex first before switching accounts.")
        sys.exit(1)

    # auto-save current as a safety net
    auto_name = None
    if CODEX_DIR.exists():
        email, _ = get_account_info()
        auto_name = f"_auto_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        print(f"Auto-saving current state → {auto_name} ...")
        copy_codex_tree(CODEX_DIR, PROFILES_DIR / auto_name)

    # swap
    print(f"Restoring profile '{name}' ...")
    if CODEX_DIR.exists():
        shutil.rmtree(CODEX_DIR, ignore_errors=True)
    copy_codex_tree(src, CODEX_DIR)

    # update state
    state = load_state()
    state["current_profile"] = name
    state["last_switch"] = datetime.now().isoformat()
    if auto_name:
        state.setdefault("auto_backups", []).append(auto_name)
    save_state(state)

    new_email, _ = get_account_info()
    print("Switched to '%s' (%s)." % (name, new_email))
    print("You can now start Codex again.")


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
    """Show what's different between the current .codex and a saved profile."""
    src = PROFILES_DIR / name if name else None
    if name and not src.exists():
        print(f"Profile '{name}' not found.")
        sys.exit(1)

    email, aid = get_account_info()
    print(f"Current account: {email} ({aid})")

    if src:
        p_email, p_aid = get_account_info(src)
        print(f"Profile '{name}': {p_email} ({p_aid})")

    # quick size comparison
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
    if not autos:
        print("No auto-backups to clean.")
        return

    print(f"Removing {len(autos)} auto-backup(s) ...")
    for name in autos:
        p = PROFILES_DIR / name
        if p.exists():
            shutil.rmtree(p, ignore_errors=True)
    state["auto_backups"] = []
    save_state(state)
    print("Done.")


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Codex Account Switcher — switch between Codex CLI accounts.",
        prog="codex-switch"
    )
    sub = parser.add_subparsers(dest="command", help="Available commands")

    sub.add_parser("current", help="Show current logged-in account")
    sub.add_parser("list", help="List all saved profiles")
    p_save = sub.add_parser("save", help="Save current account as a profile")
    p_save.add_argument("name", help="Profile name (e.g. home, work)")

    p_switch = sub.add_parser("switch", help="Switch to a saved profile")
    p_switch.add_argument("name", help="Profile name to switch to")

    p_del = sub.add_parser("delete", help="Delete a saved profile")
    p_del.add_argument("name", help="Profile name to delete")

    p_diff = sub.add_parser("diff", help="Compare current account with a profile")
    p_diff.add_argument("name", nargs="?", help="Profile name (omit to show current only)")

    sub.add_parser("clean", help="Remove auto-backup profiles")

    args = parser.parse_args()

    if not args.command:
        # Default: show current + list profiles
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
    }
    cmds[args.command]()


if __name__ == "__main__":
    main()
