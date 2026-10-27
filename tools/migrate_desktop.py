#!/usr/bin/env python3
"""Move this computer's desktop from Nixe to Nyx (docs/RENAME_NYX.md, section 4.4).

    tools/migrate_desktop.py prepare            # what it would do
    tools/migrate_desktop.py prepare --apply    # back up, stop units, move folders, rewrite config
    (install the Nyx apps)
    tools/migrate_desktop.py cleanup [--apply]  # remove the Nixe programs, launchers and units

`--keep NAME` (repeatable) leaves an app on its Nixe names, e.g. `--keep assistant`.
Root-owned files (/usr/local/lib, polkit, pacman packages) are listed, not changed.
"""

import argparse
import os
import re
import shutil
import subprocess
import sys
import tarfile
import time
from pathlib import Path

HOME = Path.home()
CONFIG = Path(os.environ.get("XDG_CONFIG_HOME") or HOME / ".config")
DATA = Path(os.environ.get("XDG_DATA_HOME") or HOME / ".local/share")
STATE = Path(os.environ.get("XDG_STATE_HOME") or HOME / ".local/state")
CACHE = Path(os.environ.get("XDG_CACHE_HOME") or HOME / ".cache")
BIN = HOME / ".local/bin"
UNITS = CONFIG / "systemd/user"


class Run:
    def __init__(self, apply, keep):
        self.apply = apply
        keep = "|".join(re.escape(k) for k in keep)
        # "nixe" as a word or prefix, in each casing, except names of the apps kept.
        tail = rf"(?![-_.](?:{keep}))" if keep else ""
        self.word = re.compile(rf"(?<![A-Za-z])(NIXE|Nixe|nixe){tail}")
        self.kept = re.compile(rf"(?:nixe[-_.](?:{keep}))", re.I) if keep else None

    def rename(self, text):
        return self.word.sub(lambda m: {"NIXE": "NYX", "Nixe": "Nyx", "nixe": "nyx"}[m.group(1)], text)

    def ours(self, name):
        """A file or folder name of the suite that moves (not a kept app's)."""
        return self.rename(name) != name

    def say(self, what):
        print(("" if self.apply else "would ") + what)

    def sh(self, *cmd):
        self.say(" ".join(map(str, cmd)))
        if self.apply:
            subprocess.run(cmd, check=False)


def units(r):
    if not UNITS.is_dir():
        return []
    return sorted(p.name for p in UNITS.iterdir() if p.name.endswith(".service") and r.ours(p.name))


def running(r):
    out = subprocess.run(["ps", "-eo", "pid=,comm=,args="], capture_output=True, text=True).stdout
    found = []
    for line in out.splitlines():
        pid, comm, *args = line.split(None, 2)
        exe = (args[0].split()[0] if args else comm).rsplit("/", 1)[-1]
        if exe.startswith("nixe") and r.ours(exe) and int(pid) != os.getpid():
            found.append(f"{pid} {exe}")
    return found


def move(r, old, new, link=True):
    if not old.is_dir() or old.is_symlink():
        return
    if new.exists():
        print(f"skip {old}: {new} already exists")
        return
    r.say(f"move {old} -> {new}")
    if r.apply:
        old.rename(new)
        if link:
            old.symlink_to(new.name)


def rewrite(r, path):
    if not path.is_file() or path.is_symlink():
        return
    try:
        text = path.read_text()
    except UnicodeDecodeError:
        return
    new = r.rename(text)
    if new != text:
        n = sum(a != b for a, b in zip(text.splitlines(), new.splitlines()))
        r.say(f"rewrite {path} ({n} lines)")
        if r.apply:
            path.write_text(new)


def config_files():
    """Desktop configuration outside the suite's own folders that names its programs."""
    hypr = CONFIG / "hypr"
    files = sorted(hypr.glob("*.lua")) if hypr.is_dir() else []
    files += [CONFIG / "omarchy/shell.json", CONFIG / "mimeapps.list", DATA / "applications/mimeapps.list"]
    hooks = CONFIG / "omarchy/hooks"
    if hooks.is_dir():
        files += sorted(p for p in hooks.rglob("*") if p.is_file())
    plugins = CONFIG / "omarchy/plugins"
    if plugins.is_dir():
        files += sorted(p for p in plugins.rglob("*") if p.is_file())
    # Glimpse checks its block in hyprland.lua against this copy, byte for byte.
    files.append(STATE / "nyx-glimpse/hypr-block.lua")
    return files


def prepare(r):
    # 1. Backup: the suite's settings and every file rewritten below.
    stamp = time.strftime("%Y%m%d-%H%M%S")
    backup = DATA / f"nixe-to-nyx-backup-{stamp}.tar.gz"
    keep = [p for p in CONFIG.glob("nixe*") if r.ours(p.name) and p.is_dir() and not p.is_symlink()]
    keep += [p for p in config_files() if p.is_file()] + [UNITS / u for u in units(r)]
    keep += [p for p in [STATE / "nixe-glimpse/hypr-block.lua"] if p.is_file()]
    r.say(f"back up {len(keep)} folders and files to {backup}")
    if r.apply:
        with tarfile.open(backup, "w:gz") as tar:
            for p in keep:
                tar.add(p, arcname=str(p.relative_to(HOME)))
    # 2. Stop the old units; the new installers enable theirs.
    for u in units(r):
        r.sh("systemctl", "--user", "disable", "--now", u)
    left = running(r)
    if left and r.apply:
        names = ", ".join(sorted({p.split()[1] for p in left}))
        sys.exit(f"Close these apps, then run prepare --apply again: {names}")
    # 3. Folders: nixe -> nyx and nixe-<app> -> nyx-<app>, a link left behind.
    for base in (CONFIG, DATA, STATE, CACHE):
        for old in sorted(base.glob("nixe*")):
            if r.ours(old.name) and old.name.split(".")[0] == old.name and old.is_dir():
                move(r, old, base / r.rename(old.name))
    # Fonts: no link, or fontconfig lists every font twice.
    fonts = DATA / "fonts"
    if (fonts / "nixe-fonts").is_dir():
        move(r, fonts / "nixe-fonts", fonts / "nyx-fonts", link=False)
        rewrite(r, STATE / "nyx-fonts/installed.toml")
        r.sh("fc-cache", "-f", str(fonts))
    # 4. Text that names the suite's programs, classes and files. The window rules
    # file moves first, so Hyprland never reloads a require of a missing file.
    hypr = CONFIG / "hypr"
    move_file(r, hypr / "nixe.lua", hypr / "nyx.lua")
    for f in config_files():
        rewrite(r, f)
    # Assistant's settings start its helpers by name, and its installed abilities and
    # their grants are keyed by id (nixe-apps).
    for f in sorted((CONFIG / "nyx-assistant").glob("*")) if r.apply else []:
        rewrite(r, f)
    abilities = DATA / "nyx-assistant/abilities"
    if r.apply and abilities.is_dir():
        for old in sorted(abilities.glob("nixe-*")):
            move(r, old, abilities / r.rename(old.name), link=False)
        for f in sorted(abilities.glob("*/plugin.toml")):
            rewrite(r, f)
    for p in sorted((CONFIG / "omarchy/plugins").glob("*nixe*")) if (CONFIG / "omarchy/plugins").is_dir() else []:
        if r.ours(p.name):
            move(r, p, p.with_name(r.rename(p.name)), link=False)
    if r.apply:
        print(f"\nBackup: {backup}\nNext: install the Nyx apps, then run `cleanup`.")


def move_file(r, old, new):
    if old.is_file() and not new.exists():
        r.say(f"move {old} -> {new}")
        if r.apply:
            old.rename(new)


def cleanup(r):
    removed = []
    for p in sorted(BIN.glob("nixe*")):
        if r.ours(p.name):
            removed.append(p)
    apps = DATA / "applications"
    removed += [p for p in sorted(apps.glob("io.github.design_nexus.nixe.*")) if r.ours(p.name)]
    icons = DATA / "icons/hicolor"
    if icons.is_dir():
        removed += [p for p in sorted(icons.rglob("*nixe*")) if p.is_file() and r.ours(p.name)]
    removed += [p for p in sorted((DATA / "dbus-1/services").glob("*nixe*")) if r.ours(p.name)]
    removed += [p for p in sorted(UNITS.glob("nixe*")) if r.ours(p.name)] if UNITS.is_dir() else []
    removed += [DATA / "mime/packages/nixe-office.xml"]
    for d in [HOME / ".mozilla/native-messaging-hosts", CONFIG / "google-chrome/NativeMessagingHosts",
              CONFIG / "chromium/NativeMessagingHosts", CONFIG / "BraveSoftware/Brave-Browser/NativeMessagingHosts"]:
        removed += sorted(d.glob("io.github.design_nexus.nixe.*")) if d.is_dir() else []
    for p in removed:
        if p.exists() or p.is_symlink():
            r.say(f"remove {p}")
            if r.apply:
                shutil.rmtree(p) if p.is_dir() and not p.is_symlink() else p.unlink()
    r.sh("systemctl", "--user", "daemon-reload")
    r.sh("update-desktop-database", str(apps))
    r.sh("update-mime-database", str(DATA / "mime"))
    root = [p for p in [Path("/usr/bin/nixe-git"), *Path("/usr/local/lib").glob("nixe-*"),
                        *Path("/usr/share/polkit-1/actions").glob("*nixe*"), Path("/var/log/nixe-assistant")]
            if p.exists() and r.ours(p.name)]
    if root:
        print("\nNeeds root (run yourself):")
        for p in root:
            print(f"  {p}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("phase", choices=["prepare", "cleanup"])
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--keep", action="append", default=[], metavar="APP")
    a = ap.parse_args()
    r = Run(a.apply, a.keep)
    (prepare if a.phase == "prepare" else cleanup)(r)


if __name__ == "__main__":
    main()
