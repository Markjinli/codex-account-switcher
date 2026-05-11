"""Core logic for Codex account management — extracted from the CLI tool."""

import os
import sys
import json
import shutil
import time
import stat
import subprocess
import base64
from pathlib import Path
from datetime import datetime

CODEX_DIR = Path.home() / ".codex"
SWITCHER_DIR = Path.home() / ".codex-switcher"
PROFILES_DIR = SWITCHER_DIR / "profiles"
STATE_FILE = SWITCHER_DIR / "state.json"

SKIP_DIRS = {".tmp", ".sandbox-secrets", ".sandbox", "vendor_imports", "tmp"}


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def ensure_dirs():
    PROFILES_DIR.mkdir(parents=True, exist_ok=True)


def load_state():
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def save_state(state):
    STATE_FILE.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")


def get_account_info(codex_dir=CODEX_DIR):
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
    try:
        if sys.platform == "win32":
            result = subprocess.run(["tasklist", "/NH"], capture_output=True, text=True)
            return "codex" in result.stdout.lower()
        else:
            result = subprocess.run(["pgrep", "-i", "-x", "codex"], capture_output=True, text=True)
            return result.returncode == 0
    except Exception:
        return False


def kill_codex():
    try:
        if sys.platform == "win32":
            subprocess.run(["taskkill", "/F", "/FI", "IMAGENAME eq Codex Proxy.exe"],
                           capture_output=True, text=True)
            subprocess.run(["taskkill", "/F", "/FI", "IMAGENAME eq codex.exe"],
                           capture_output=True, text=True)
        else:
            subprocess.run(["pkill", "-9", "-i", "codex"], capture_output=True, text=True)
    except Exception:
        pass


def _remove_readonly(fn, path, excinfo):
    try:
        os.chmod(path, stat.S_IWRITE)
        fn(path)
    except Exception:
        pass


def rmtree_force(path: Path):
    if not path.exists():
        return
    shutil.rmtree(str(path), onerror=_remove_readonly, ignore_errors=True)


def copy_codex_tree(src: Path, dst: Path):
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
# operations
# ---------------------------------------------------------------------------

def get_current():
    """Return (email, account_id, profile_name) for the current account."""
    if not CODEX_DIR.exists():
        return None, None, None
    email, aid = get_account_info()
    state = load_state()
    profile = state.get("current_profile", "")
    saved = state.get("profiles", {})
    if email and profile in saved:
        pass
    elif email:
        for name, info in saved.items():
            if info.get("email") == email:
                profile = name
                break
    return email, aid, profile


def list_profiles():
    """Return list of (name, email) for all saved profiles (excl. auto-backups)."""
    ensure_dirs()
    result = []
    for p in sorted(PROFILES_DIR.iterdir()):
        if p.name.startswith("_auto_"):
            continue
        if not p.is_dir():
            continue
        try:
            em, _ = get_account_info(p)
            result.append((p.name, em or "unknown"))
        except Exception:
            result.append((p.name, "unknown"))
    return result


def save_profile(name: str) -> str:
    """Save current .codex as named profile. Returns email string."""
    if not CODEX_DIR.exists():
        raise FileNotFoundError("Codex directory not found")
    email, _ = get_account_info()
    if not email or email == "unknown":
        raise RuntimeError("Could not determine account email")
    ensure_dirs()
    copy_codex_tree(CODEX_DIR, PROFILES_DIR / name)
    state = load_state()
    state.setdefault("profiles", {})
    state["profiles"][name] = {"email": email, "saved_at": datetime.now().isoformat()}
    state["current_profile"] = name
    save_state(state)
    return email


def switch_profile(name: str) -> str:
    """Switch to a saved profile. Returns the new email."""
    src = PROFILES_DIR / name
    if not src.exists():
        raise FileNotFoundError(f"Profile '{name}' not found")

    if is_codex_running():
        kill_codex()
        time.sleep(0.5)

    # auto-save current
    if CODEX_DIR.exists():
        try:
            email, _ = get_account_info()
            if email and email != "unknown":
                auto_name = f"_auto_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                copy_codex_tree(CODEX_DIR, PROFILES_DIR / auto_name)
        except Exception:
            pass  # auto-save failure should not block switching

    copy_codex_tree(src, CODEX_DIR)

    state = load_state()
    state["current_profile"] = name
    state["last_switch"] = datetime.now().isoformat()
    save_state(state)

    new_email, _ = get_account_info()
    return new_email


def delete_profile(name: str):
    """Delete a saved profile."""
    src = PROFILES_DIR / name
    if src.exists():
        rmtree_force(src)
    state = load_state()
    state.get("profiles", {}).pop(name, None)
    if state.get("current_profile") == name:
        state.pop("current_profile", None)
    save_state(state)


def logout():
    """Clear current login state."""
    if is_codex_running():
        kill_codex()
        time.sleep(0.5)
    for f in ["auth.json", ".codex-global-state.json", ".codex-global-state.json.bak"]:
        p = CODEX_DIR / f
        if p.exists():
            p.unlink(missing_ok=True)
    sessions = CODEX_DIR / "sessions"
    if sessions.exists():
        shutil.rmtree(sessions, ignore_errors=True)
