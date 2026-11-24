import argparse
import configparser
import sys
import zipfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
PLUGIN_NAME = "isotone"
DESKTOP_SECTION = "Desktop Entry"
EXCLUDED_DIRECTORIES = {"__pycache__"}
EXCLUDED_SUFFIXES = {".pyc", ".pyo"}


def check_plugin_layout(root):
    desktop = root / f"{PLUGIN_NAME}.desktop"
    package = root / PLUGIN_NAME
    entry = configparser.ConfigParser(interpolation=None)
    entry.optionxform = str
    entry.read(desktop, encoding="utf-8")
    library = entry.get(DESKTOP_SECTION, "X-KDE-Library", fallback=None)
    if library != PLUGIN_NAME:
        raise SystemExit(f"{desktop.name}: X-KDE-Library is {library!r}, expected {PLUGIN_NAME!r}")
    if not (package / "__init__.py").is_file():
        raise SystemExit(f"{package} is not a Python package")


def bundle_entries(root):
    desktop = root / f"{PLUGIN_NAME}.desktop"
    yield desktop, desktop.name
    for path in sorted((root / PLUGIN_NAME).rglob("*")):
        relative = path.relative_to(root)
        if path.is_dir() or path.suffix in EXCLUDED_SUFFIXES:
            continue
        if EXCLUDED_DIRECTORIES.intersection(relative.parts):
            continue
        yield path, relative.as_posix()


def build_bundle(root, version, output_directory):
    check_plugin_layout(root)
    output_directory.mkdir(parents=True, exist_ok=True)
    archive = output_directory / f"{PLUGIN_NAME}-{version.removeprefix('v')}.zip"
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as bundle:
        for source, name in bundle_entries(root):
            bundle.write(source, name)
    return archive


def main():
    parser = argparse.ArgumentParser(
        description=(
            "pack the plugin into a zip for Tools > Scripts > Import Python Plugin from File"
        )
    )
    parser.add_argument("--version", default="dev", help="version or tag (eg v1.2.3)")
    parser.add_argument("--output", type=Path, default=REPO_ROOT / "dist")
    arguments = parser.parse_args()
    archive = build_bundle(REPO_ROOT, arguments.version, arguments.output)
    print(archive)


if __name__ == "__main__":
    sys.exit(main())
