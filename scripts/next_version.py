import argparse
import re
import subprocess

TAG_PATTERN = re.compile(r"^v(\d+)\.(\d+)\.(\d+)$")
BREAKING_HEADER = re.compile(r"^\w+(\([^)]*\))?!:")
FEATURE_HEADER = re.compile(r"^feat(\([^)]*\))?:")
BREAKING_FOOTER = re.compile(r"^BREAKING[ -]CHANGE: ", re.MULTILINE)
INITIAL_VERSION = (0, 0, 0)


def git(*arguments):
    return subprocess.run(["git", *arguments], check=True, capture_output=True, text=True).stdout


def parse_tag(tag):
    match = TAG_PATTERN.match(tag)
    return tuple(int(part) for part in match.groups()) if match else None


def format_tag(version):
    return "v{}.{}.{}".format(*version)


def latest_version(tags):
    versions = [version for version in map(parse_tag, tags) if version is not None]
    return max(versions) if versions else None


def bump_kind(messages):
    kind = "patch"
    for message in messages:
        lines = message.strip().splitlines()
        header = lines[0] if lines else ""
        if BREAKING_HEADER.match(header) or BREAKING_FOOTER.search(message):
            return "major"
        if FEATURE_HEADER.match(header):
            kind = "minor"
    return kind


def bumped(version, kind):
    major, minor, patch = version
    if kind == "major":
        return major + 1, 0, 0
    if kind == "minor":
        return major, minor + 1, 0
    return major, minor, patch + 1


def next_tag():
    if latest_version(git("tag", "--points-at", "HEAD", "--list", "v*").split()):
        return None
    current = latest_version(git("tag", "--merged", "HEAD", "--list", "v*").split())
    log_range = f"{format_tag(current)}..HEAD" if current else "HEAD"
    messages = [
        message
        for message in git("log", log_range, "--format=%B%x00").split("\0")
        if message.strip()
    ]
    return format_tag(bumped(current or INITIAL_VERSION, bump_kind(messages)))


def main():
    argparse.ArgumentParser(
        description=(
            "Print the next vX.Y.Z tag from Conventional Commits since the latest tag: "
            "'feat:' bumps minor, '!:' or a 'BREAKING CHANGE:' footer bumps major, "
            "anything else bumps patch. Prints nothing when HEAD is already tagged."
        )
    ).parse_args()
    tag = next_tag()
    if tag:
        print(tag)


if __name__ == "__main__":
    main()
