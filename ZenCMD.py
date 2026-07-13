print("ZenCMD/2 initializing...")
# =================================================
# Zeno OS Recovery
# =================================================
# This module is the "last resort" path: it must keep working even if
# /Services, PackageManager, Git, Network, or zeno.py are missing or
# corrupted. To guarantee that, it ONLY uses built-in MicroPython modules
# (network, urequests, json, os, time, urandom) and never imports
# anything from /Services.

import os
import json
import time

try:
    import urandom
except ImportError:                       # pragma: no cover - desktop fallback
    import random as urandom

try:
    import network
except ImportError:
    network = None

try:
    import urequests
except ImportError:
    urequests = None


PKGTABLE_URL = "https://raw.githubusercontent.com/FerrariForever95/Zeno-Micro-PC/main/pkgtable.json"
PKGLIST_PATH = "/pkglist.json"
ZENO_PATH    = "/zeno.py"

ZENO_TEMPLATE = """import urandom,time

ui=None
tsk=None
log=None
net=None
usr=None
fm=None

boot_cap=urandom.getrandbits(32)

wallpaper=f""

boot_time=None

authorized=False

password="{password}"

user="{user}"

gitsecret="{gitsecret}"

ssid="{ssid}"

wifi_password="{wifi_password}"
"""


class Recovery:
    """Lightweight, dependency-free recovery utility. Rebuilds every
    'core' package listed in pkgtable.json directly from GitHub."""

    def __init__(self):
        self._creds = {}          # kept only in RAM until recovery completes
        self._pkgtable = None
        self._results = {"installed": [], "updated_flagged": [], "failed": []}

    def help(self):
        print("  recover               Rebuild core OS components from pkgtable.json")
        print("                        Works even if Services/PackageManager/Git/")
        print("                        Network/zeno.py are missing or corrupted.")

    # =============================================
    # entry point
    # =============================================
    def run(self):
        print("\n=== Zeno OS Recovery ===")
        print("Rebuilding core OS components from pkgtable.json.\n")

        zeno_existed = self._file_exists(ZENO_PATH)

        if zeno_existed:
            print("[recover] Found existing zeno.py -- using its stored Wi-Fi credentials.")
            ssid, password = self._read_zeno_wifi()
            if not ssid:
                print("[recover] Could not read usable Wi-Fi credentials from zeno.py.")
                ssid, password = self._prompt_wifi_only()
        else:
            print("[recover] zeno.py not found -- collecting setup details.")
            self._creds = self._prompt_all()
            ssid = self._creds.get("ssid")
            password = self._creds.get("wifi_password")

        if not self._connect_wifi(ssid, password):
            print("[recover] Could not establish Wi-Fi connection. Aborting recovery.")
            return False

        self._pkgtable = self._download_pkgtable()
        if self._pkgtable is None:
            print("[recover] Could not download/parse pkgtable.json. Aborting recovery.")
            return False

        core_pkgs = [n for n, e in self._pkgtable.items() if e.get("core", False)]
        if not core_pkgs:
            print("[recover] No packages flagged core:true were found in pkgtable.json.")
        else:
            print("[recover] Core packages to restore: {}".format(", ".join(core_pkgs)))

        installed = self._load_pkglist()
        seen = set()
        for name in core_pkgs:
            self._restore_package(name, installed, seen)

        self._save_pkglist(installed)

        print("\n[recover] Recovery summary:")
        print("  Restored/repaired  : {}".format(", ".join(self._results["installed"]) or "none"))
        print("  Flagged for update : {}".format(", ".join(self._results["updated_flagged"]) or "none"))
        print("  Failed             : {}".format(", ".join(self._results["failed"]) or "none"))

        if not zeno_existed:
            if self._results["failed"]:
                print("[recover] Skipping zeno.py generation -- one or more core packages failed.")
            else:
                self._write_zeno_py(self._creds)
                print("[recover] Generated new zeno.py.")
            # credentials only ever lived in self._creds / locals -- drop them now
            self._creds = {}

        print("=== Recovery complete ===\n")
        return not self._results["failed"]

    # =============================================
    # prompts (only used when zeno.py is missing)
    # =============================================
    def _prompt_all(self):
        creds = {}
        creds["user"] = input("Username: ").strip()
        creds["password"] = input("Password: ").strip()
        creds["ssid"] = input("Wi-Fi SSID: ").strip()
        creds["wifi_password"] = input("Wi-Fi Password: ").strip()
        creds["gitsecret"] = input("Git Personal Access Token (optional, Enter to skip): ").strip()
        return creds

    def _prompt_wifi_only(self):
        ssid = input("Wi-Fi SSID: ").strip()
        password = input("Wi-Fi Password: ").strip()
        return ssid, password

    # =============================================
    # zeno.py handling -- read-only, never imports it (it may be broken)
    # =============================================
    def _file_exists(self, path):
        try:
            os.stat(path)
            return True
        except OSError:
            return False

    def _read_zeno_wifi(self):
        try:
            with open(ZENO_PATH) as f:
                text = f.read()
        except OSError:
            return None, None

        ssid = self._extract_assignment(text, "ssid")
        password = self._extract_assignment(text, "wifi_password")
        return ssid, password

    def _extract_assignment(self, text, var_name):
        for line in text.splitlines():
            line = line.strip()
            if line.startswith(var_name + "=") or line.startswith(var_name + " ="):
                _, _, rhs = line.partition("=")
                rhs = rhs.strip()
                if len(rhs) >= 2 and rhs[0] == rhs[-1] and rhs[0] in ("'", '"'):
                    return rhs[1:-1]
                return rhs or None
        return None

    def _write_zeno_py(self, creds):
        content = ZENO_TEMPLATE.format(
            password=creds.get("password", ""),
            user=creds.get("user", ""),
            gitsecret=creds.get("gitsecret", ""),
            ssid=creds.get("ssid", ""),
            wifi_password=creds.get("wifi_password", ""),
        )
        with open(ZENO_PATH, "w") as f:
            f.write(content)

    # =============================================
    # Wi-Fi -- connects directly via the 'network' module, never via
    # the Network service
    # =============================================
    def _connect_wifi(self, ssid, password):
        if not ssid:
            print("[recover] No SSID available to connect with.")
            return False
        if network is None:
            print("[recover] 'network' module unavailable on this platform -- "
                  "assuming an existing/wired connection and continuing.")
            return True
        try:
            wlan = network.WLAN(network.STA_IF)
            wlan.active(True)
            if wlan.isconnected():
                return True
            wlan.connect(ssid, password)
            for _ in range(20):
                if wlan.isconnected():
                    print("[recover] Wi-Fi connected.")
                    return True
                time.sleep(0.5)
            print("[recover] Wi-Fi connection timed out.")
            return False
        except Exception as e:
            print("[recover] Wi-Fi error: {}".format(e))
            return False

    # =============================================
    # HTTP / pkgtable
    # =============================================
    def _download_pkgtable(self):
        raw = self._http_get_text(PKGTABLE_URL)
        if raw is None:
            return None
        try:
            return json.loads(raw)
        except ValueError as e:
            print("[recover] pkgtable.json is not valid JSON: {}".format(e))
            return None

    def _http_get_text(self, url):
        if urequests is None:
            print("[recover] 'urequests' module unavailable -- cannot download {}".format(url))
            return None
        try:
            resp = urequests.get(url)
            try:
                if resp.status_code != 200:
                    print("[recover] HTTP {} fetching {}".format(resp.status_code, url))
                    return None
                return resp.text
            finally:
                resp.close()
        except Exception as e:
            print("[recover] Download failed for {}: {}".format(url, e))
            return None

    def _raw_url(self, author, repo, branch, file_path):
        return "https://raw.githubusercontent.com/{}/{}/{}/{}".format(
            author, repo, branch or "main", file_path)

    # =============================================
    # filesystem helpers -- raw os/open only, mkdir -p style
    # =============================================
    def _mkdirs(self, path):
        parts = [p for p in path.split("/") if p]
        cur = ""
        for p in parts:
            cur += "/" + p
            try:
                os.mkdir(cur)
            except OSError:
                pass  # already exists

    def _full_path(self, install_path, filename):
        return "{}/{}".format((install_path or "/").rstrip("/"), filename)

    def _write_and_verify(self, path, data):
        directory = path.rsplit("/", 1)[0] or "/"
        self._mkdirs(directory)
        try:
            with open(path, "w") as f:
                f.write(data)
        except OSError as e:
            print("[recover] Could not write '{}': {}".format(path, e))
            return False

        try:
            written_size = os.stat(path)[6]
        except OSError:
            print("[recover] Verification failed: '{}' missing after write.".format(path))
            return False

        if written_size != len(data):
            print("[recover] Verification failed: size mismatch writing '{}'.".format(path))
            return False
        return True

    def _file_is_healthy(self, path):
        try:
            return os.stat(path)[6] > 0
        except OSError:
            return False

    # =============================================
    # pkglist.json (read/write directly -- no PackageManager/FileManager)
    # =============================================
    def _load_pkglist(self):
        try:
            with open(PKGLIST_PATH) as f:
                data = json.load(f)
            return data if isinstance(data, dict) else {}
        except (OSError, ValueError):
            return {}

    def _save_pkglist(self, data):
        try:
            with open(PKGLIST_PATH, "w") as f:
                json.dump(data, f)
        except OSError as e:
            print("[recover] Could not write pkglist.json: {}".format(e))

    # =============================================
    # per-package restore, with dependency resolution
    # =============================================
    def _restore_package(self, name, installed, seen, chain=None):
        if name in seen:
            return name not in self._results["failed"]
        seen.add(name)
        chain = chain or []
        if name in chain:
            print("[recover] Dependency cycle detected involving '{}' -- skipping.".format(name))
            self._results["failed"].append(name)
            return False
        chain = chain + [name]

        entry = self._pkgtable.get(name)
        if entry is None:
            print("[recover] '{}' not found in pkgtable.json -- skipping.".format(name))
            self._results["failed"].append(name)
            return False

        try:
            for dep in entry.get("dependencies", []):
                dep_name = dep.get("name") if isinstance(dep, dict) else dep
                if not dep_name:
                    continue
                if not self._restore_package(dep_name, installed, seen, chain):
                    print("[recover] Dependency '{}' failed -- cannot restore '{}'.".format(dep_name, name))
                    self._results["failed"].append(name)
                    return False

            filename = entry.get("file", "").split("/")[-1]
            target_path = self._full_path(entry.get("install_path"), filename)
            record = installed.get(name)

            if record:
                existing_path = self._full_path(record.get("install_path"), record.get("filename"))
                healthy = self._file_is_healthy(existing_path)
                same_version = record.get("version") == entry.get("version")

                if healthy and same_version:
                    return True  # already good, nothing to do

                if healthy and not same_version:
                    # present and readable, just out of date -- don't
                    # clobber it, just flag it for a normal update later
                    record["update needed"] = True
                    self._results["updated_flagged"].append(name)
                    return True
                # else: missing or corrupted -- fall through and repair it

            data = self._http_get_text(self._raw_url(
                entry.get("author"), entry.get("repository"), entry.get("branch"), entry.get("file")))
            if data is None:
                self._results["failed"].append(name)
                return False

            if not self._write_and_verify(target_path, data):
                self._results["failed"].append(name)
                return False

            installed[name] = {
                "name": entry.get("name", name),
                "version": entry.get("version"),
                "author": entry.get("author"),
                "repository": entry.get("repository"),
                "branch": entry.get("branch") or "main",
                "install_path": entry.get("install_path"),
                "filename": filename,
                "dependencies": entry.get("dependencies", []),
                "core": bool(entry.get("core", False)),
            }
            self._results["installed"].append(name)
            print("[recover] Restored '{}' v{}.".format(name, entry.get("version")))
            return True

        except Exception as e:
            print("[recover] Unexpected error restoring '{}': {}".format(name, e))
            self._results["failed"].append(name)
            return False
# =================================================
# SERVICES IMPORT  (must never prevent ZenCMD from booting)
# =================================================
# ZenCMD has to be able to boot -- and always offer 'recover' -- even if
# /Services is missing entirely, or any single class inside it is missing
# or broken. So the whole package is imported defensively and every
# individual service is resolved with getattr(..., None) rather than a
# plain "from Services import X, Y, Z" that would raise ImportError for
# the lot the moment any one name is unavailable.
try:
    import Services
except Exception as e:
    Services = None
    print("[ZenCMD] Warning: /Services unavailable ({}). Running in degraded/recovery mode.".format(e))


def _svc(name):
    return getattr(Services, name, None) if Services is not None else None


Network          = _svc("Network")
Disk             = _svc("Disk")
downloadhelper   = _svc("downloadhelper")
system           = _svc("system")
Logger           = _svc("Logger")
Git              = _svc("Git")
BluetoothManager = _svc("BluetoothManager")
BootConfig       = _svc("BootConfig")
usermanager      = _svc("usermanager")
FileManager      = _svc("FileManager")
PackageManager   = _svc("PackageManager")

import os
import sys

# zeno.py may be missing/corrupted too -- fall back to a stub object so
# every existing "zeno.user" / "zeno.hostname" reference below keeps
# working without needing to be rewritten one by one.
try:
    import zeno
except Exception as e:
    print("[ZenCMD] Warning: zeno.py unavailable ({}). Run 'recover' to rebuild it.".format(e))

    class _FallbackZeno:
        user = "recovery"
        hostname = "zeno-device"

    zeno = _FallbackZeno()

# =================================================
# VERSION
# =================================================
ZENCMD_VERSION = "2.2.0"
ZENOS_NAME     = "Zeno OS"

# =================================================
# LOGGER  (falls back to a no-op/print logger if the Logger service is gone)
# =================================================
class _NullLogger:
    def debug(self, msg, source=None):
        pass

    def warning(self, msg, source=None):
        print("[WARN] {}".format(msg))

    def error(self, msg, source=None):
        print("[ERROR] {}".format(msg))


logger = Logger() if Logger else _NullLogger()

# =================================================
# USER MANAGER / FILE MANAGER / PACKAGE MANAGER  (single instances, never
# duplicated -- any of these may legitimately be None if Services is
# missing or corrupted; every call site below is expected to tolerate that)
# =================================================
_um = usermanager() if usermanager else None
_fm = FileManager() if FileManager else None   # <-- ALL filesystem access goes through here when available
_pm = PackageManager() if PackageManager else None
# =================================================
# MODULE REGISTRY
# =================================================
# NOTE: "encrypter": ZenZip was removed -- ZenZip is never imported
# anywhere in Services, so leaving it wired in here would crash ZenCMD
# at import time with NameError the moment MODULES is built. Re-add it
# once a real ZenZip implementation exists and is imported above.
#
# Only services that actually loaded are registered here -- if Services
# is missing or partially broken, "enter <module>" / "pkg install ..."
# just reports "No such module" instead of crashing ZenCMD.
_ALL_MODULES = {
    "net":          Network,
    "disk":         Disk,
    "downserv":     downloadhelper,
    "system":       system,
    "log":          Logger,
    "git":          Git,
    "bootmgr":      BootConfig,
    "bluetoothmgr": BluetoothManager,
    "pkg":          PackageManager,
}
MODULES = {k: v for k, v in _ALL_MODULES.items() if v is not None}

# Commands that require Super Mode.
# Checked as prefix-match so "bootmgr <anything>" is caught.
# NOTE: this list is matched against the *bare command word* (either a
# top-level builtin, or the method name called on a module), so it also
# gates package-manager methods -- "install", "uninstall", "reinstall"
# and "update" all require Super Mode whether typed as "pkg install foo",
# as a one-shot module call, or from inside "enter pkg".
#
# 'recover' is deliberately NOT in this list: it must remain usable even
# when usermanager/Super Mode itself is unavailable (e.g. Services is gone).
PRIVILEGED_PREFIXES = (
    "bootmgr",
    "mount",
    "umount",
    "unmount",
    "format",
    "mkfs",
    "shutdown",
    "reboot",
    "factory",
    "removeuser",
    "elevate",
    "delevate",
    "service",
    "reload",
    "reloadmodule",
    "kernel",
    "driver",
    "pkg",
    "install",
    "remove",
    "uninstall",
    "reinstall",
    "update",
    "mountzfs",
    "bootlog",
)

# =================================================
# STATE
# =================================================
current_path   = "/Home"
active_module  = None        # str key
module_instance = None       # live object

history_log    = []          # command history
aliases        = {}          # user-defined aliases
env_vars       = {}          # shell environment
jobs           = []          # background job stubs

_PIPE_IN       = None        # list[str] of lines fed in from a "|" pipeline, else None

# =================================================
# PRIVILEGE HELPERS
# =================================================

def _is_super():
    if _um is None:
        return False
    try:
        return _um.isrooted(zeno.user)
    except Exception:
        return False


def _require_super(cmd_word):
    for prefix in PRIVILEGED_PREFIXES:
        if cmd_word == prefix or cmd_word.startswith(prefix + " "):
            if not _is_super():
                print("Access denied. Command requires Super Mode. Use 'super' first.")
                return True   # caller should skip
    return False


# =================================================
# PROMPT
# =================================================

def _prompt():
    d = current_path.rstrip("/") or ""
    if d.startswith("/"):
        d = d[1:]                   # strip leading slash for display

    if _is_super():
        path_part = f"root/{d}" if d else "root/"
        return f"{path_part}#:$"
    else:
        path_part = f"{zeno.user}/{d}:$" if d else f"{zeno.user}/:$"
        if active_module:
            return f"{path_part}[{active_module}]> "
        return f"{path_part}>"


# =================================================
# PATH HELPERS  (pure string helpers -- no I/O here; all real I/O goes
# through FileManager, which does its own normalisation internally)
# =================================================

def _normalize_path(path):
    """Collapse '.', '..' and repeated slashes into a clean absolute path.
    This is what makes 'cd ..', 'cd ../foo', 'cat ../x.txt' etc. actually work --
    previously paths were just string-concatenated and '..' was never resolved."""
    parts = []
    for p in path.split("/"):
        if p in ("", "."):
            continue
        if p == "..":
            if parts:
                parts.pop()
            continue
        parts.append(p)
    return "/" + "/".join(parts) if parts else "/"


def _abs(path):
    """Resolve a path to a normalized absolute path using current_path."""
    if path.startswith("/"):
        combined = path
    else:
        base = current_path if current_path.endswith("/") else current_path + "/"
        combined = base + path
    return _normalize_path(combined)


def _pjoin(parent, name):
    parent = parent.rstrip("/") or "/"
    return name if parent == "/" else parent + "/" + name


def human_size(size):
    if size < 1024:
        return f"{size} B"
    if size < 1024 * 1024:
        return f"{size / 1024:.2f} KB"
    return f"{size / (1024 * 1024):.2f} MB"


def _is_dir(path):
    try:
        return _fm.metadata(path).get("type") == "directory"
    except Exception:
        return False


# =================================================
# PROGRAM SEARCH / EXECUTION  (routed through FileManager so read/exec
# permission is actually enforced, not just faked with a path guard)
# =================================================

def _fs_file(path):
    """True if path exists and is a plain file (not a directory)."""
    if not _fm.exists(path):
        return False
    try:
        return _fm.metadata(path).get("type") != "directory"
    except Exception:
        return False


def resolve_program(name, cwd):
    targets = [name] if name.endswith(".py") else [name, name + ".py"]

    if name.startswith("/"):
        for t in targets:
            if _fs_file(t):
                return t
        return None

    for t in targets:
        p = _pjoin(cwd, t)
        if _fs_file(p):
            return p

    print("[SYSRUN] Searching filesystem...")
    stack = ["/"]
    seen  = set()
    while stack:
        base = stack.pop()
        if base in seen:
            continue
        seen.add(base)
        try:
            entries = _fm.listdir(base, show_hidden=True)
        except Exception:
            continue
        for e in entries:
            full = _pjoin(base, e)
            try:
                is_dir = _fm.metadata(full).get("type") == "directory"
            except Exception:
                continue
            if is_dir:
                stack.append(full)
            elif e in targets:
                return full
    return None


def run_python_file(path):
    """Read (with permission enforcement) and exec a .py file."""
    fd = _fm.open(path, "r")
    try:
        code = _fm.read(fd)
    finally:
        _fm.close(fd)
    exec(code, {"__name__": "__main__", "__file__": path})


# =================================================
# DIRECTORY DISPLAY
# =================================================

def list_dir(path, long=False):
    try:
        entries = _fm.listdir(path, show_hidden=True)
    except Exception as e:
        print("[ls] Cannot list:", e)
        return

    print(f"\n{path}")
    print("-" * 40)
    for f in entries:
        full = _pjoin(path, f)
        # hide protected root-level .py unless super (system files)
        if path == "/" and (f.endswith(".py") or f.endswith(".mpy")) and not _is_super():
            continue
        if f in ["pkglist.json", "pkgtable.json"]:
            continue
        try:
            meta = _fm.metadata(full)
        except Exception:
            meta = {"type": "unknown", "size": 0, "owner": "?"}
        is_d = meta.get("type") == "directory"
        if long:
            sz     = human_size(meta.get("size", 0))
            kind   = "<DIR> " if is_d else "      "
            owner  = meta.get("owner", "?")
            print(f"  {kind}{f:28} {sz:>10}  owner={owner}")
        else:
            tag = "/" if is_d else ""
            print(f"  {f}{tag}")
    print()


def tree_dir(path, prefix=""):
    try:
        entries = _fm.listdir(path, show_hidden=True)
    except Exception:
        print(prefix + "[unreadable]")
        return
    for e in entries:
        full = _pjoin(path, e)
        if path == "/" and e.endswith(".py") and not _is_super():
            continue
        if _is_dir(full):
            print(prefix + "|-- " + e + "/")
            tree_dir(full, prefix + "|   ")
        else:
            print(prefix + "|-- " + e)


# =================================================
# ARGUMENT HELPERS
# =================================================

def convert_arg(arg):
    try:
        return float(arg) if "." in arg else int(arg)
    except:
        return arg


def _is_intlike(s):
    try:
        int(s)
        return True
    except Exception:
        return False


def _split(cmd):
    """Split a single command into tokens, respecting quoted strings.
    Quote characters themselves are stripped (used for the final,
    per-command argument split)."""
    parts  = []
    buf    = []
    in_q   = False
    q_char = None
    for ch in cmd:
        if in_q:
            if ch == q_char:
                in_q = False
            else:
                buf.append(ch)
        elif ch in ('"', "'"):
            in_q   = True
            q_char = ch
        elif ch == " ":
            if buf:
                parts.append("".join(buf))
                buf = []
        else:
            buf.append(ch)
    if buf:
        parts.append("".join(buf))
    return parts


def _split_top(raw, delims):
    """Split raw text on any character in `delims` (e.g. ';' or '|'),
    but never inside quotes. Quote characters are PRESERVED here (unlike
    _split) since each resulting segment is itself re-tokenized later."""
    segments = []
    buf    = []
    in_q   = False
    q_char = None
    for ch in raw:
        if in_q:
            buf.append(ch)
            if ch == q_char:
                in_q = False
        elif ch in ('"', "'"):
            in_q   = True
            q_char = ch
            buf.append(ch)
        elif ch in delims:
            segments.append("".join(buf))
            buf = []
        else:
            buf.append(ch)
    segments.append("".join(buf))
    return segments


# =================================================
# STDOUT CAPTURE  (backs the "|" pipeline -- lets one command's printed
# output become the next command's piped-in lines)
# =================================================

class _OutputCapture:
    def __init__(self):
        self.lines = []
        self._buf = ""

    def write(self, s):
        self._buf += s
        while "\n" in self._buf:
            line, self._buf = self._buf.split("\n", 1)
            self.lines.append(line)

    def flush(self):
        pass


def _read_lines(args, idx=0):
    """Get a list of text lines for commands like cat/head/tail/search.
    Priority: an explicit file argument at args[idx], otherwise whatever
    came in through a '|' pipe. Returns None if neither is available."""
    if len(args) > idx:
        p = _abs(args[idx])
        try:
            fd = _fm.open(p, "r")
            try:
                data = _fm.read(fd)
            finally:
                _fm.close(fd)
            return data.splitlines()
        except Exception as e:
            print("[read]", e)
            return None
    if _PIPE_IN is not None:
        return _PIPE_IN
    return None


# =================================================
# BUILT-IN COMMAND HELP STRINGS
# =================================================
BUILTIN_HELP = {
    "pwd":         "pwd                   Print working directory",
    "cd":          "cd <path>             Change directory (supports .. and .)",
    "ls":          "ls [-l]               List directory contents",
    "dir":         "dir                   Alias for ls",
    "tree":        "tree [path]           Show directory tree",
    "mkdir":       "mkdir <dir>           Create directory",
    "rmdir":       "rmdir <dir>           Remove empty directory",
    "rm":          "rm <path>             Remove file",
    "cp":          "cp <src> <dst>        Copy file",
    "mv":          "mv <src> <dst>        Move/rename file",
    "touch":       "touch <file>          Create empty file",
    "cat":         "cat <file>            Print file contents (or piped input)",
    "head":        "head <file> [n]       Print first n lines (default 10; or piped input)",
    "tail":        "tail <file> [n]       Print last n lines (default 10; or piped input)",
    "search":      "search <pat> [file]   Grep-like search (alias: grep; supports piped input)",
    "echo":        "echo <text>           Print text",
    "clear":       "clear                 Clear terminal  (cls alias)",
    "cls":         "cls                   Alias for clear",
    "history":     "history               Show command history",
    "which":       "which <cmd>           Find command location",
    "whereis":     "whereis <name>        Locate binary on filesystem",
    "find":        "find <path> <name>    Search for files",
    "stat":        "stat <path>           File status information",
    "file":        "file <path>           Describe file type",
    "whoami":      "whoami                Show current user",
    "id":          "id                    Show user identity",
    "hostname":    "hostname              Show device hostname",
    "date":        "date                  Show current date",
    "time":        "time                  Show current time",
    "uptime":      "uptime                Show system uptime",
    "version":     "version               Show ZenCMD and OS version",
    "df":          "df                    Disk free (filesystem usage)",
    "du":          "du <path>             Disk usage of path",
    "free":        "free                  Show free memory",
    "memdebug":    "memdebug              Detailed memory debug",
    "ps":          "ps                    Show running processes",
    "kill":        "kill <pid>            Kill process by ID",
    "jobs":        "jobs                  List background jobs",
    "env":         "env                   Show environment variables",
    "export":      "export KEY=VALUE      Set environment variable",
    "alias":       "alias [name=cmd]      Define or list aliases",
    "unalias":     "unalias <name>        Remove alias",
    "mount":       "mount [src dst]       Mount filesystem  (SUPER)",
    "mountzfs":    "mountzfs              Mount ZFS volume  (SUPER)",
    "sync":        "sync                  Sync filesystem buffers",
    "bootlog":     "bootlog               Show boot log  (SUPER)",
    "log":         "log                   Show ZenCMD log",
    "service":     "service <name> <op>   Manage services  (SUPER)",
    "services":    "services              List all services",
    "reload":      "reload                Reload ZenCMD config  (SUPER)",
    "reloadmodule":"reloadmodule <mod>    Reload a module  (SUPER)",
    "shutdown":    "shutdown              Power off device  (SUPER)",
    "reboot":      "reboot                Reboot device  (SUPER)",
    "factory":     "factory               Factory reset  (SUPER)",
    "super":       "super                 Elevate to Super Mode",
    "unsuper":     "unsuper               Exit Super Mode",
    "userdebug":   "userdebug             Show current user debug",
    "whoisroot":   "whoisroot             Check if current user is rooted",
    "modules":     "modules               List available modules",
    "enter":       "enter <module>        Enter module context",
    "leave":       "leave                 Leave current module",
    "sysrun":      "sysrun <file>         Run a .py file or open a file",
    "pkgrun":      "pkgrun <pkg> [args]   Run an installed package",
    "recover":     "recover               Rebuild core OS from pkgtable.json (always works)",
    "help":        "help [cmd|module]     Show help",
    "exit":        "exit / quit           Exit module or ZenCMD",
    "quit":        "quit                  Alias for exit",
}


def _shell_help():
    print(f"\nZenCMD {ZENCMD_VERSION} — {ZENOS_NAME}")
    print("=" * 48)
    print("Navigation")
    for k in ("pwd", "cd", "ls", "tree", "mkdir", "rmdir", "rm", "cp", "mv", "touch"):
        print(" ", BUILTIN_HELP[k])
    print("\nFile Operations")
    for k in ("cat", "head", "tail", "search", "echo", "stat", "file", "find", "which", "whereis"):
        print(" ", BUILTIN_HELP[k])
    print("\nSystem")
    for k in ("whoami", "id", "hostname", "date", "time", "uptime", "version",
              "df", "du", "free", "memdebug", "ps", "kill", "jobs", "sync"):
        print(" ", BUILTIN_HELP[k])
    print("\nEnvironment")
    for k in ("env", "export", "alias", "unalias", "history", "clear"):
        print(" ", BUILTIN_HELP[k])
    print("\nZeno-specific")
    for k in ("super", "unsuper", "userdebug", "whoisroot", "modules",
              "enter", "leave", "sysrun", "pkgrun", "service", "services",
              "reload", "reloadmodule", "mountzfs", "bootlog", "log",
              "shutdown", "reboot", "factory"):
        print(" ", BUILTIN_HELP[k])
    print("\nRecovery (always available, even with a broken /Services)")
    print(" ", BUILTIN_HELP["recover"])
    print("\nPackages: 'enter pkg' or 'pkg <install|uninstall|reinstall|update|")
    print("info|list|verify|run> ...'. install/uninstall/reinstall/update")
    print("require Super Mode. Use 'pkgrun <pkg> [args]' to run one directly.")
    print("\nChaining: use ';' to run commands one after another")
    print("  e.g.  clear ; ls")
    print("and '|' to pipe one command's output into the next")
    print("  e.g.  cat /LOGS/systemlog.txt | search ERROR")
    print("  e.g.  ls -l | search .py")
    print("\nType 'help <command>' for details, or '<module> help' for module help.")
    print()


# =================================================
# SUPER MODE
# =================================================

def _cmd_super():
    if _is_super():
        print("Already in Super Mode.")
        return
    if _um is None:
        print("Super Mode is unavailable (usermanager service is missing). "
              "Recovery-critical commands like 'recover' don't need it.")
        return
    try:
        pwd = input(f"Enter password for {zeno.user}: ")
    except KeyboardInterrupt:
        print()
        return
    _um.elevate(zeno.user, pwd)
    if _is_super():
        logger.debug(f"Super Mode entered by {zeno.user}", source="ZenCMD")
        print("Entering Super Mode...")
    else:
        logger.warning(f"Failed Super Mode attempt by {zeno.user}", source="ZenCMD")
        print("Authentication failed.")


def _cmd_unsuper():
    if not _is_super():
        print("Not in Super Mode.")
        return
    try:
        pwd = input(f"Confirm password for {zeno.user}: ")
    except KeyboardInterrupt:
        print()
        return
    _um.delevate(zeno.user, pwd)
    if not _is_super():
        logger.debug(f"Super Mode exited by {zeno.user}", source="ZenCMD")
        print("Exited Super Mode.")
    else:
        print("Authentication failed. Remaining in Super Mode.")


# =================================================
# BUILT-IN IMPLEMENTATIONS  (filesystem ones all go through _fm)
# =================================================

def _cmd_ls(args):
    long  = "-l" in args
    paths = [a for a in args if not a.startswith("-")]
    path  = _abs(paths[0]) if paths else current_path
    list_dir(path, long=long)


def _cmd_cd(args):
    global current_path
    if not args:
        current_path = "/"
        return
    target = _abs(args[0])
    if not _fm.exists(target) or not _is_dir(target):
        print(f"[cd] Not a directory: {target}")
        return
    current_path = target


def _cmd_mkdir(args):
    if not args:
        print("Usage: mkdir <dir>")
        return
    for d in args:
        try:
            _fm.mkdir(_abs(d))
            print("Created:", d)
        except Exception as e:
            print("[mkdir]", e)


def _cmd_rmdir(args):
    if not args:
        print("Usage: rmdir <dir>")
        return
    p = _abs(args[0])
    try:
        if not _is_dir(p):
            print(f"[rmdir] Not a directory: {p}")
            return
        if _fm.listdir(p, show_hidden=True):
            print(f"[rmdir] Directory not empty: {p}")
            return
        _fm.delete(p)
        print("Removed:", p)
    except Exception as e:
        print("[rmdir]", e)


def _cmd_rm(args):
    if not args:
        print("Usage: rm <file>")
        return
    p = _abs(args[0])
    try:
        if _is_dir(p):
            print(f"[rm] Is a directory (use rmdir): {p}")
            return
        _fm.delete(p)
        print("Removed:", p)
    except Exception as e:
        print("[rm]", e)


def _cmd_cp(args):
    if len(args) < 2:
        print("Usage: cp <src> <dst>")
        return
    src, dst = _abs(args[0]), _abs(args[1])
    try:
        _fm.copy(src, dst)
        print(f"Copied {src} -> {dst}")
    except Exception as e:
        print("[cp]", e)


def _cmd_mv(args):
    if len(args) < 2:
        print("Usage: mv <src> <dst>")
        return
    src, dst = _abs(args[0]), _abs(args[1])
    try:
        _fm.move(src, dst)
        print(f"Moved {src} -> {dst}")
    except Exception as e:
        print("[mv]", e)


def _cmd_touch(args):
    if not args:
        print("Usage: touch <file>")
        return
    p = _abs(args[0])
    try:
        if _fm.exists(p):
            fd = _fm.open(p, "a")
            _fm.close(fd)
        else:
            _fm.create(p, "")
        print("Touched:", p)
    except Exception as e:
        print("[touch]", e)


def _cmd_cat(args):
    lines = _read_lines(args, 0)
    if lines is None:
        print("Usage: cat <file>  (or pipe input, e.g. ls | cat)")
        return
    print("\n".join(lines))


def _cmd_head(args):
    n = 10
    file_args = args
    if _PIPE_IN is not None and (not args or _is_intlike(args[0])):
        if args:
            n = int(args[0])
        file_args = []
    elif len(args) > 1:
        n = int(args[1])
        file_args = args[:1]
    else:
        file_args = args[:1]

    lines = _read_lines(file_args, 0)
    if lines is None:
        print("Usage: head <file> [n]  (or pipe input)")
        return
    for line in lines[:n]:
        print(line)


def _cmd_tail(args):
    n = 10
    file_args = args
    if _PIPE_IN is not None and (not args or _is_intlike(args[0])):
        if args:
            n = int(args[0])
        file_args = []
    elif len(args) > 1:
        n = int(args[1])
        file_args = args[:1]
    else:
        file_args = args[:1]

    lines = _read_lines(file_args, 0)
    if lines is None:
        print("Usage: tail <file> [n]  (or pipe input)")
        return
    for line in lines[-n:]:
        print(line)


def _cmd_search(args):
    """grep-like: search <pattern> [file] -- reads from file if given,
    otherwise from piped input (e.g. cat log.txt | search ERROR)."""
    if not args:
        print("Usage: search <pattern> [file]  (or pipe input, e.g. cat file | search foo)")
        return
    pattern = args[0]
    lines = _read_lines(args, 1)
    if lines is None:
        print("Usage: search <pattern> [file]  (or pipe input)")
        return
    matched = 0
    for line in lines:
        if pattern in line:
            print(line)
            matched += 1
    if matched == 0:
        print("[search] no matches")


def _cmd_stat(args):
    if not args:
        print("Usage: stat <path>")
        return
    p = _abs(args[0])
    try:
        meta = _fm.metadata(p)
    except Exception as e:
        print("[stat] Not found:", p)
        return
    print(f"  Path       : {p}")
    print(f"  Type       : {meta.get('type')}")
    print(f"  Size       : {human_size(meta.get('size', 0))}")
    print(f"  Owner      : {meta.get('owner')}")
    print(f"  Permission : {meta.get('permission')}")


def _cmd_file(args):
    if not args:
        print("Usage: file <path>")
        return
    p = _abs(args[0])
    try:
        meta = _fm.metadata(p)
    except Exception:
        print(p + ": no such file")
        return
    print(p + ": " + meta.get("type", "unknown"))


def _cmd_find(args):
    if len(args) < 2:
        print("Usage: find <path> <name>")
        return
    base  = _abs(args[0])
    query = args[1]
    stack = [base]
    found = 0
    while stack:
        d = stack.pop()
        try:
            entries = _fm.listdir(d, show_hidden=True)
        except Exception:
            continue
        for e in entries:
            full = _pjoin(d, e)
            if query in e:
                print(full)
                found += 1
            if _is_dir(full):
                stack.append(full)
    if found == 0:
        print("No matches.")


def _cmd_which(args):
    if not args:
        print("Usage: which <cmd>")
        return
    name = args[0]
    if name in BUILTIN_HELP:
        print(f"{name}: ZenCMD built-in")
        return
    if name in MODULES:
        print(f"{name}: ZenCMD module")
        return
    p = resolve_program(name, current_path)
    if p:
        print(p)
    else:
        print(f"{name}: not found")


def _cmd_whereis(args):
    _cmd_which(args)


def _cmd_echo(args):
    out = []
    for a in args:
        if a.startswith("$"):
            out.append(str(env_vars.get(a[1:], "")))
        else:
            out.append(a)
    print(" ".join(out))


def _cmd_env(args):
    for k, v in env_vars.items():
        print(f"  {k}={v}")


def _cmd_export(args):
    if not args:
        _cmd_env([])
        return
    for a in args:
        if "=" in a:
            k, v = a.split("=", 1)
            env_vars[k.strip()] = v.strip()
            print(f"Set {k}={v}")
        else:
            print(f"export: invalid: {a}")


def _cmd_alias(args):
    if not args:
        for k, v in aliases.items():
            print(f"  alias {k}='{v}'")
        return
    for a in args:
        if "=" in a:
            k, v = a.split("=", 1)
            aliases[k.strip()] = v.strip()
        else:
            if a in aliases:
                print(f"  alias {a}='{aliases[a]}'")
            else:
                print(f"alias: {a}: not found")


def _cmd_unalias(args):
    if not args:
        print("Usage: unalias <name>")
        return
    for a in args:
        if a in aliases:
            del aliases[a]
            print(f"Removed alias: {a}")
        else:
            print(f"unalias: {a}: not found")


def _cmd_history(args):
    for i, h in enumerate(history_log, 1):
        print(f"  {i:4}  {h}")


def _cmd_userdebug(args):
    if _um is None:
        print("  usermanager service unavailable.")
        return
    debug = _um.userdebug() if hasattr(_um, "userdebug") else _um.userinfo()
    print(f"  User   : {debug.get('user', '?')}")
    print(f"  Rooted : {debug.get('root', False)}")


def _cmd_whoisroot(args):
    if _um is None:
        print("usermanager service unavailable.")
        return
    rooted = _um.isrooted(zeno.user)
    if rooted:
        print(f"{zeno.user} is in Super Mode (rooted).")
    else:
        print(f"{zeno.user} is not rooted.")


def _cmd_whoami(args):
    print("root" if _is_super() else zeno.user)


def _cmd_id(args):
    uid = 0 if _is_super() else 1000
    print(f"uid={uid}({_cmd_whoami_str()}) gid={uid}")


def _cmd_whoami_str():
    return "root" if _is_super() else zeno.user


def _cmd_hostname(args):
    try:
        import network
        print(network.WLAN().config("hostname"))
    except:
        print(getattr(zeno, "hostname", "zeno-device"))


def _cmd_version(args):
    print(f"{ZENOS_NAME}")
    print(f"ZenCMD {ZENCMD_VERSION}")
    try:
        import sys as _s
        print(f"MicroPython {_s.version}")
    except:
        pass


def _cmd_uptime(args):
    try:
        import time
        t = time.ticks_ms() // 1000
        h = t // 3600
        m = (t % 3600) // 60
        s = t % 60
        print(f"Uptime: {h}h {m}m {s}s")
    except Exception as e:
        print("[uptime]", e)


def _cmd_date(args):
    try:
        import utime
        t = utime.localtime()
        print(f"{t[0]}-{t[1]:02d}-{t[2]:02d}")
    except Exception as e:
        print("[date]", e)


def _cmd_time_cmd(args):
    try:
        import utime
        t = utime.localtime()
        print(f"{t[3]:02d}:{t[4]:02d}:{t[5]:02d}")
    except Exception as e:
        print("[time]", e)


def _cmd_df(args):
    try:
        import uos
        st = uos.statvfs("/")
        block_size  = st[0]
        total       = st[2] * block_size
        free        = st[3] * block_size
        used        = total - free
        print(f"  Total : {human_size(total)}")
        print(f"  Used  : {human_size(used)}")
        print(f"  Free  : {human_size(free)}")
    except Exception as e:
        print("[df]", e)


def _cmd_du(args):
    path = _abs(args[0]) if args else current_path
    total = 0
    stack = [path]
    while stack:
        d = stack.pop()
        try:
            entries = _fm.listdir(d, show_hidden=True)
        except Exception:
            continue
        for e in entries:
            full = _pjoin(d, e)
            if _is_dir(full):
                stack.append(full)
            else:
                try:
                    total += _fm.metadata(full).get("size", 0)
                except Exception:
                    pass
    print(f"  {human_size(total)}  {path}")


def _cmd_free(args):
    try:
        import gc
        gc.collect()
        free  = gc.mem_free()
        alloc = gc.mem_alloc()
        total = free + alloc
        print(f"  Total : {human_size(total)}")
        print(f"  Used  : {human_size(alloc)}")
        print(f"  Free  : {human_size(free)}")
    except Exception as e:
        print("[free]", e)


def _cmd_memdebug(args):
    _cmd_free(args)
    try:
        import micropython
        micropython.mem_debug()
    except:
        pass


def _cmd_ps(args):
    print("  PID  NAME")
    print("    1  zencmd (this shell)")
    for i, j in enumerate(jobs, 2):
        print(f"  {i:3}  {j}")


def _cmd_kill(args):
    if not args:
        print("Usage: kill <pid>")
        return
    print(f"[kill] Signal sent to PID {args[0]} (stub)")


def _cmd_jobs(args):
    if not jobs:
        print("No background jobs.")
    for i, j in enumerate(jobs, 1):
        print(f"  [{i}] {j}")


def _cmd_sync(args):
    try:
        import uos
        uos.sync()
        print("Synced.")
    except Exception as e:
        print("[sync]", e)


def _cmd_mount(args):
    if len(args) < 2:
        print("Usage: mount <src> <dst>")
        return
    print(f"[mount] Mounting {args[0]} -> {args[1]} (stub)")


def _cmd_mountzfs(args):
    try:
        import zfs
        zfs.mount()
        print("ZFS mounted.")
    except Exception as e:
        print("[mountzfs]", e)


def _cmd_bootlog(args):
    p = "/bootlog.txt"
    try:
        fd = _fm.open(p, "r")
        try:
            print(_fm.read(fd))
        finally:
            _fm.close(fd)
    except Exception:
        print("[bootlog] No boot log found.")


def _cmd_log(args):
    p = "/log.txt"
    try:
        fd = _fm.open(p, "r")
        try:
            print(_fm.read(fd))
        finally:
            _fm.close(fd)
    except Exception:
        print("[log] No log file found.")


def _cmd_services(args):
    print("Services: (stub — integrate service manager)")


def _cmd_service(args):
    if len(args) < 2:
        print("Usage: service <name> <start|stop|restart|status>")
        return
    print(f"[service] {args[0]} {args[1]} (stub)")


def _cmd_reload(args):
    print("[reload] Reloading ZenCMD config... (stub)")


def _cmd_reloadmodule(args):
    global module_instance
    if not args:
        print("Usage: reloadmodule <module>")
        return
    name = args[0].lower()
    if name not in MODULES:
        print("Unknown module:", name)
        return
    if active_module == name:
        module_instance = MODULES[name]()
        print(f"Reloaded module: {name}")
    else:
        print(f"Module {name} not active. Enter it first.")


def _cmd_shutdown(args):
    logger.debug("System shutdown requested", source="ZenCMD")
    print("Shutting down...")
    try:
        import machine
        machine.poweroff()
    except:
        print("[shutdown] machine.poweroff() not available.")


def _cmd_reboot(args):
    logger.debug("System reboot requested", source="ZenCMD")
    print("Rebooting...")
    try:
        import machine
        machine.reset()
    except:
        print("[reboot] machine.reset() not available.")


def _cmd_factory(args):
    logger.warning("Factory reset requested", source="ZenCMD")
    confirm = input("This will erase all data. Type YES to confirm: ")
    if confirm.strip() == "YES":
        print("Factory reset initiated... (stub)")
    else:
        print("Cancelled.")


def _cmd_modules(args):
    print("\nAvailable modules:")
    for k in MODULES:
        print(f"  {k}")
    print()


def _cmd_sysrun(args):
    if not args:
        print("Usage: sysrun <file>")
        return
    name = args[0]
    path = resolve_program(name, current_path)
    if not path:
        print(f"[sysrun] Not found: {name}")
        return
    if path.endswith(".py"):
        print("[sysrun] Running", path)
        try:
            run_python_file(path)
        except KeyboardInterrupt:
            print("\n[sysrun] Interrupted")
        except Exception as e:
            print("[sysrun] Error:", e)
    else:
        try:
            fd = _fm.open(path, "r")
            try:
                print(_fm.read(fd))
            finally:
                _fm.close(fd)
        except Exception as e:
            print("[sysrun] Cannot open:", e)


def _cmd_pkgrun(args):
    """pkgrun <package> [args...] -- run an installed package.
    Does NOT require Super Mode; only install/uninstall/reinstall/update do.
    """
    if not args:
        print("Usage: pkgrun <package> [args...]")
        return
    if PackageManager is None:
        print("[pkgrun] PackageManager service is unavailable. Try 'recover' first.")
        return
    name     = args[0]
    pkg_args = [convert_arg(a) for a in args[1:]]
    pm = PackageManager()
    pm.run(name, *pkg_args)


def _cmd_recover(args):
    """recover -- rebuild core OS components from pkgtable.json.
    Deliberately implemented in a standalone /Recovery.py module that never
    imports anything from /Services, so this works even when Services,
    PackageManager, Git, Network, or zeno.py are missing/corrupted."""
    try:
        rec = Recovery()
        rec.run()
    except KeyboardInterrupt:
        print("\n[recover] Interrupted.")
    except Exception as e:
        print("[recover] Recovery failed:", e)


# =================================================
# MODULE DISPATCH
# =================================================

def _enter_module(name):
    global active_module, module_instance
    cls = MODULES.get(name.lower())
    if cls is None:
        print(f"No such module: {name}")
        return
    module_instance = cls()
    active_module   = name.lower()
    logger.debug(f"Module entered: {active_module}", source="ZenCMD")
    print(f">> {active_module}")


def _leave_module():
    global active_module, module_instance
    if active_module:
        logger.debug(f"Module exited: {active_module}", source="ZenCMD")
        print(f"Left module: {active_module}")
        active_module   = None
        module_instance = None
    else:
        print("Not inside a module.")


def _dispatch_module(instance, fn, args):
    if hasattr(instance, fn):
        r = getattr(instance, fn)(*args)
        if r is not None:
            print(r)
    else:
        print(f"No method: {fn}")


# =================================================
# COMMAND DISPATCH TABLE
# =================================================
BUILTINS = {
    # Navigation
    "pwd":          (lambda a: print(current_path),  False),
    "cd":           (_cmd_cd,        False),
    "ls":           (_cmd_ls,        False),
    "dir":          (_cmd_ls,        False),
    "tree":         (lambda a: (tree_dir(_abs(a[0]) if a else current_path) or print()), False),
    "mkdir":        (_cmd_mkdir,     False),
    "rmdir":        (_cmd_rmdir,     False),
    "rm":           (_cmd_rm,        False),
    "cp":           (_cmd_cp,        False),
    "mv":           (_cmd_mv,        False),
    "touch":        (_cmd_touch,     False),
    # File content
    "cat":          (_cmd_cat,       False),
    "head":         (_cmd_head,      False),
    "tail":         (_cmd_tail,      False),
    "search":       (_cmd_search,    False),
    "echo":         (_cmd_echo,      False),
    "stat":         (_cmd_stat,      False),
    "file":         (_cmd_file,      False),
    "find":         (_cmd_find,      False),
    "which":        (_cmd_which,     False),
    "whereis":      (_cmd_whereis,   False),
    # System debug
    "whoami":       (lambda a: print(_cmd_whoami_str()), False),
    "id":           (_cmd_id,        False),
    "hostname":     (_cmd_hostname,  False),
    "date":         (_cmd_date,      False),
    "time":         (_cmd_time_cmd,  False),
    "uptime":       (_cmd_uptime,    False),
    "version":      (_cmd_version,   False),
    "df":           (_cmd_df,        False),
    "du":           (_cmd_du,        False),
    "free":         (_cmd_free,      False),
    "memdebug":     (_cmd_memdebug,  False),
    "ps":           (_cmd_ps,        False),
    "kill":         (_cmd_kill,      False),
    "jobs":         (_cmd_jobs,      False),
    # Environment
    "env":          (_cmd_env,       False),
    "export":       (_cmd_export,    False),
    "alias":        (_cmd_alias,     False),
    "unalias":      (_cmd_unalias,   False),
    "history":      (_cmd_history,   False),
    "clear":        (lambda a: print("\n" * 40), False),
    "cls":          (lambda a: print("\n" * 40), False),
    # User
    "userdebug":    (_cmd_userdebug, False),
    "whoisroot":    (_cmd_whoisroot, False),
    # Modules
    "modules":      (_cmd_modules,   False),
    "sysrun":       (_cmd_sysrun,    False),
    "pkgrun":       (_cmd_pkgrun,    False),
    # Recovery -- always available, no Super Mode required
    "recover":      (_cmd_recover,   False),
    # Privileged
    "mount":        (_cmd_mount,     True),
    "mountzfs":     (_cmd_mountzfs,  True),
    "sync":         (_cmd_sync,      False),
    "bootlog":      (_cmd_bootlog,   True),
    "log":          (_cmd_log,       False),
    "service":      (_cmd_service,   True),
    "services":     (_cmd_services,  False),
    "reload":       (_cmd_reload,    True),
    "reloadmodule": (_cmd_reloadmodule, True),
    "shutdown":     (_cmd_shutdown,  True),
    "reboot":       (_cmd_reboot,    True),
    "factory":      (_cmd_factory,   True),
}

# Default aliases (user can override)
aliases["ll"]   = "ls -l"
aliases["cls"]  = "clear"
aliases["q"]    = "exit"
aliases["grep"] = "search"


# =================================================
# COMMAND PREPROCESSOR
# =================================================

def _preprocess(raw):
    """Expand aliases, handle env-var substitutions."""
    parts = _split(raw)
    if not parts:
        return raw
    first = parts[0]
    if first in aliases:
        expansion = aliases[first]
        rest      = raw[len(first):].lstrip()
        return (expansion + " " + rest).strip() if rest else expansion
    return raw


# =================================================
# SINGLE-COMMAND EXECUTION  (one command word + its args -- no ';' or '|')
# =================================================

def _execute(raw):
    global current_path, active_module, module_instance

    cmd = _preprocess(raw).strip()
    if not cmd:
        return

    parts = _split(cmd)
    verb  = parts[0].lower()
    args  = parts[1:]

    # ---- exit / quit ----
    if verb in ("exit", "quit"):
        if active_module:
            _leave_module()
        else:
            print("Exiting ZenCMD.")
            raise SystemExit(0)
        return

    # ---- leave ----
    if verb == "leave":
        _leave_module()
        return

    # ---- help (contextual) ----
    if verb == "help":
        if not args:
            if active_module and module_instance and hasattr(module_instance, "help"):
                module_instance.help()
            else:
                _shell_help()
        else:
            topic = args[0].lower()
            if topic in BUILTIN_HELP:
                print("\n  " + BUILTIN_HELP[topic] + "\n")
            elif topic in MODULES:
                m = MODULES[topic]()
                if hasattr(m, "help"):
                    m.help()
                else:
                    print(f"Module '{topic}' has no help().")
            else:
                print(f"No help for '{topic}'.")
        return

    # ---- super / unsuper ----
    if verb == "super":
        _cmd_super()
        return

    if verb == "unsuper":
        _cmd_unsuper()
        return

    # ---- <module> help  (e.g. "pkg help") ----
    if verb in MODULES and args and args[0].lower() == "help":
        m = MODULES[verb]()
        if hasattr(m, "help"):
            m.help()
        else:
            print(f"Module '{verb}' has no help().")
        return

    # ---- enter <module> or bare module name ----
    if verb == "enter":
        if args:
            _enter_module(args[0])
        else:
            print("Usage: enter <module>")
        return

    if verb in MODULES and not args:
        _enter_module(verb)
        return

    # ---- inside-module command dispatch ----
    if active_module and module_instance:
        if verb not in BUILTINS and verb not in MODULES:
            if _require_super(verb):
                return
            _dispatch_module(module_instance, verb, [convert_arg(a) for a in args])
            return

    # ---- one-shot module call: "pkg install foo", "git status" ----
    if verb in MODULES and args:
        fn    = args[0]
        margs = [convert_arg(a) for a in args[1:]]
        if fn.lower() == "help":
            m = MODULES[verb]()
            if hasattr(m, "help"):
                m.help()
            else:
                print(f"Module '{verb}' has no help().")
            return
        # Enforce Super Mode at the shell level too -- not just inside
        # PackageManager -- so one-shot calls get the same gate as
        # "enter pkg" -> "install foo".
        if _require_super(fn):
            return
        m = MODULES[verb]()
        logger.debug(f"Module call: {verb}.{fn}", source="ZenCMD")
        _dispatch_module(m, fn, margs)
        return

    # ---- built-in commands ----
    if verb in BUILTINS:
        handler, needs_super = BUILTINS[verb]
        if needs_super and not _is_super():
            print("Access denied. Command requires Super Mode. Use 'super' first.")
            return
        handler(args)
        return
    if _pm is not None and verb in _pm.list():
        _pm.run(verb)
        logger.debug(f"Module call: {verb}", source="ZenCMD")
        return
    print(f"Unknown command: {verb}  (type 'help')")


# =================================================
# PIPELINE ("|") + STATEMENT SEQUENCING (";")
# =================================================

def _run_single(cmd_line, pipe_in=None, capture=False):
    """Run one pipeline segment. If capture=True, stdout is redirected
    and the printed lines are returned (for the next segment); otherwise
    output goes straight to the real terminal and None is returned."""
    global _PIPE_IN
    _PIPE_IN = pipe_in

    if not capture:
        try:
            _execute(cmd_line)
        finally:
            _PIPE_IN = None
        return None

    old_stdout = sys.stdout
    cap = _OutputCapture()
    sys.stdout = cap
    try:
        _execute(cmd_line)
    finally:
        sys.stdout = old_stdout
        _PIPE_IN = None
    if cap._buf:
        cap.lines.append(cap._buf)
    return cap.lines


def _run_statement(stmt):
    """Run one ';'-separated statement, handling any '|' pipeline within it."""
    segments = [s.strip() for s in _split_top(stmt, "|")]
    segments = [s for s in segments if s]
    if not segments:
        return
    if len(segments) == 1:
        _run_single(segments[0], pipe_in=None, capture=False)
        return

    data = None
    for i, seg in enumerate(segments):
        is_last = (i == len(segments) - 1)
        data = _run_single(seg, pipe_in=data, capture=not is_last)


# =================================================
# TOP-LEVEL COMMAND HANDLER
# =================================================

def handle(raw):
    raw = raw.strip()
    if not raw:
        return

    statements = [s.strip() for s in _split_top(raw, ";")]
    for stmt in statements:
        if not stmt:
            continue
        history_log.append(stmt)
        _run_statement(stmt)


# =================================================
# STARTUP BANNER
# =================================================
print(f"\n{ZENOS_NAME} — ZenCMD {ZENCMD_VERSION}")
print(f"Logged in as: {zeno.user}")
if Services is None:
    print("[ZenCMD] Services unavailable -- most commands are disabled.")
    print("[ZenCMD] Run 'recover' to rebuild the OS from pkgtable.json.")
print("Type 'help' for commands.\n")
logger.debug(f"ZenCMD started, user={zeno.user}", source="ZenCMD")

# =================================================
# MAIN LOOP
# =================================================
while True:
    try:
        line = input(_prompt()).strip()
        handle(line)

    except SystemExit:
        logger.debug("ZenCMD exited normally", source="ZenCMD")
        break

    except KeyboardInterrupt:
        print("\n[ZenCMD] ^C")

    except Exception as e:
        print("[ZenCMD] Error:", e)
        logger.error(str(e), source="ZenCMD")
