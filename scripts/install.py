import argparse
import os
import shutil
import stat
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
PLUGIN_NAME = "isotone"


def default_pykrita_directory():
    if sys.platform == "win32":
        return Path(os.environ["APPDATA"]) / "krita" / "pykrita"
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "krita" / "pykrita"
    data_home = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
    return data_home / "krita" / "pykrita"


def is_junction(path):
    if sys.platform != "win32":
        return False
    try:
        attributes = os.lstat(path).st_file_attributes
    except FileNotFoundError:
        return False
    return bool(attributes & stat.FILE_ATTRIBUTE_REPARSE_POINT) and not path.is_symlink()


def remove_directory_or_link(path):
    if path.is_symlink():
        path.unlink()
    elif is_junction(path):
        os.rmdir(path)
    elif path.exists():
        shutil.rmtree(path)


def remove_plugin(pykrita):
    remove_directory_or_link(pykrita / PLUGIN_NAME)
    (pykrita / f"{PLUGIN_NAME}.desktop").unlink(missing_ok=True)


def link_package(source, target):
    if sys.platform == "win32":
        subprocess.run(
            ["cmd", "/c", "mklink", "/J", str(target), str(source)],
            check=True,
            capture_output=True,
        )
    else:
        target.symlink_to(source, target_is_directory=True)


def install_plugin(pykrita, linked):
    remove_plugin(pykrita)
    pykrita.mkdir(parents=True, exist_ok=True)
    source = REPO_ROOT / PLUGIN_NAME
    target = pykrita / PLUGIN_NAME
    if linked:
        link_package(source, target)
    else:
        shutil.copytree(source, target, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    shutil.copy2(REPO_ROOT / f"{PLUGIN_NAME}.desktop", pykrita)


def main():
    parser = argparse.ArgumentParser(description="Install the plugin into Krita's pykrita folder.")
    parser.add_argument(
        "mode",
        choices=("link", "copy", "remove"),
        help=(
            "link: live link to this checkout for development; "
            "copy: standalone copy; remove: uninstall"
        ),
    )
    parser.add_argument("--pykrita", type=Path, default=default_pykrita_directory())
    arguments = parser.parse_args()

    if arguments.mode == "remove":
        remove_plugin(arguments.pykrita)
        print(f"Removed {PLUGIN_NAME} from {arguments.pykrita}")
        return
    install_plugin(arguments.pykrita, linked=arguments.mode == "link")
    print(f"Installed {PLUGIN_NAME} into {arguments.pykrita} ({arguments.mode})")
    print("Enable it in Settings > Configure Krita > Python Plugin Manager and restart Krita.")


if __name__ == "__main__":
    main()
