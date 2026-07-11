print("ZenCMD/2 initializing...")

from Services import (
    Network, Disk, downloadhelper, system, Logger, Git,
    BluetoothManager, BootConfig, usermanager, FileManager, PackageManager,
)
import os
import sys
import zeno

# =================================================
# VERSION
# =================================================
ZENCMD_VERSION = "2.1.0"
ZENOS_NAME     = "Zeno OS"

# =================================================
# LOGGER
# =================================================
logger = Logger()

# =================================================
# USER MANAGER / FILE MANAGER  (single instances, never duplicated)
# =================================================
_um = usermanager()
_fm = FileManager()   # <-- all filesystem access now goes through here

# =================================================
# MODULE REGISTRY
# =================================================
# NOTE: "encrypter": ZenZip was removed -- ZenZip is never imported
# anywhere in Services, so leaving it wired in here would crash ZenCMD
# at import time with NameError the moment MODULES is built. Re-add it
# once a real ZenZip implementation exists and is imported above.
MODULES = {
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

# Commands that require Super Mode.
# Checked as prefix-match so "bootmgr <anything>" is caught.
# NOTE: this list is matched against the *bare command word* (either a
# top-level builtin, or the method name called on a module), so it also
# gates package-manager methods -- "install", "uninstall", "reinstall"
# and "update" all require Super Mode whether typed as "pkg install foo",
# as a one-shot module call, or from inside "enter pkg".
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
current_path   = "/"
active_module  = None        # str key
module_instance = None       # live object

history_log    = []          # command history
aliases        = {}          # user-defined aliases
env_vars       = {}          # shell environment
jobs           = []          # background job stubs

# =================================================
# PRIVILEGE HELPERS
# =================================================

def _is_super():
    return _um.isrooted(zeno.user)


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
        return f"{path_part}# "
    else:
        path_part = f"{zeno.user}/{d}" if d else f"{zeno.user}/"
        if active_module:
            return f"{path_part}[{active_module}]> "
        return f"{path_part}> "


# =================================================
# PATH HELPERS  (pure string helpers -- no I/O here; all real I/O goes
# through FileManager, which does its own normalisation internally)
# =================================================

def _abs(path):
    """Resolve a path to absolute using current_path."""
    if path.startswith("/"):
        return path
    base = current_path if current_path.endswith("/") else current_path + "/"
    return base + path


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
        if path == "/" and f.endswith(".py") and not _is_super():
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


def _split(cmd):
    """Split command line respecting quoted strings."""
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


# =================================================
# BUILT-IN COMMAND HELP STRINGS
# =================================================
BUILTIN_HELP = {
    "pwd":         "pwd                   Print working directory",
    "cd":          "cd <path>             Change directory",
    "ls":          "ls [-l]               List directory contents",
    "dir":         "dir                   Alias for ls",
    "tree":        "tree [path]           Show directory tree",
    "mkdir":       "mkdir <dir>           Create directory",
    "rmdir":       "rmdir <dir>           Remove empty directory",
    "rm":          "rm <path>             Remove file",
    "cp":          "cp <src> <dst>        Copy file",
    "mv":          "mv <src> <dst>        Move/rename file",
    "touch":       "touch <file>          Create empty file",
    "cat":         "cat <file>            Print file contents",
    "head":        "head <file> [n]       Print first n lines (default 10)",
    "tail":        "tail <file> [n]       Print last n lines (default 10)",
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
    for k in ("cat", "head", "tail", "echo", "stat", "file", "find", "which", "whereis"):
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
    print("\nPackages: 'enter pkg' or 'pkg <install|uninstall|reinstall|update|")
    print("info|list|verify|run> ...'. install/uninstall/reinstall/update")
    print("require Super Mode. Use 'pkgrun <pkg> [args]' to run one directly.")
    print("\nType 'help <command>' for details, or '<module> help' for module help.")
    print()


# =================================================
# SUPER MODE
# =================================================

def _cmd_super():
    if _is_super():
        print("Already in Super Mode.")
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
    if not args:
        print("Usage: cat <file>")
        return
    p = _abs(args[0])
    try:
        fd = _fm.open(p, "r")
        try:
            print(_fm.read(fd))
        finally:
            _fm.close(fd)
    except Exception as e:
        print("[cat]", e)


def _cmd_head(args):
    if not args:
        print("Usage: head <file> [n]")
        return
    p = _abs(args[0])
    n = int(args[1]) if len(args) > 1 else 10
    try:
        fd = _fm.open(p, "r")
        try:
            data = _fm.read(fd)
        finally:
            _fm.close(fd)
        for line in data.splitlines()[:n]:
            print(line)
    except Exception as e:
        print("[head]", e)


def _cmd_tail(args):
    if not args:
        print("Usage: tail <file> [n]")
        return
    p = _abs(args[0])
    n = int(args[1]) if len(args) > 1 else 10
    try:
        fd = _fm.open(p, "r")
        try:
            data = _fm.read(fd)
        finally:
            _fm.close(fd)
        for line in data.splitlines()[-n:]:
            print(line)
    except Exception as e:
        print("[tail]", e)


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
    debug = _um.userdebug() if hasattr(_um, "userdebug") else _um.userinfo()
    print(f"  User   : {debug.get('user', '?')}")
    print(f"  Rooted : {debug.get('root', False)}")


def _cmd_whoisroot(args):
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
    try:
        with open("/bootlog.txt", "r") as f:
            print(f.read())
    except:
        print("[bootlog] No boot log found.")


def _cmd_log(args):
    try:
        with open("/log.txt", "r") as f:
            print(f.read())
    except:
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
    name     = args[0]
    pkg_args = [convert_arg(a) for a in args[1:]]
    pm = PackageManager()
    pm.run(name, *pkg_args)


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
aliases["ll"]  = "ls -l"
aliases["cls"] = "clear"
aliases["q"]   = "exit"


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
# TOP-LEVEL COMMAND HANDLER
# =================================================

def handle(raw):
    global current_path, active_module, module_instance

    cmd  = _preprocess(raw).strip()
    if not cmd:
        return

    parts = _split(cmd)
    verb  = parts[0].lower()
    args  = parts[1:]

    history_log.append(raw)

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

    print(f"Unknown command: {verb}  (type 'help')")


# =================================================
# STARTUP BANNER
# =================================================
print(f"\n{ZENOS_NAME} — ZenCMD {ZENCMD_VERSION}")
print(f"Logged in as: {zeno.user}")
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
