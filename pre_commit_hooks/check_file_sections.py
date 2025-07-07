#!/usr/bin/env python
"""Script to check C-header and C-source files for the correct file sections."""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

settings = {
    "template": """
/* --------------------------------------------------------------------------
 * {title}
 * -------------------------------------------------------------------------- */""",
    "prefix": r"/\* -+",
    "suffix": r" \* -+ \*/",
    "header": [
        "includes",
        "macros/defines",
        "type declarations",
        "function declarations",
    ],
    "source": [
        "includes",
        "macros/defines",
        "type declarations",
        "global variables",
        "local function declarations",
        "function implementations",
        "local function implementations",
    ],
    "replace": {
        "header": [],
        "source": [("function declarations", "local function declarations")],
    },
    "deduplicate": True,
}
section_regex = r"^{prefix}[\n\r]{{1,2}}\s\* {title}[\n\r]{{1,2}}{suffix}$"
section_area_start = (
    r"#ifndef\s[A-Z\d_]+_H_[\n\r]{{1,2}}#define\s[A-Z\d_]+_H_[\n\r]{{1,2}}",
)
section_area_end = r"#endif\s+//\s[A-Z\d_]+_H_"


def insert_section_at_end(content, title, end_index):
    """Check if section is in content"""
    stri = section_regex.format(
        prefix=settings["prefix"],
        title=title,
        suffix=settings["suffix"],
    )
    regex = re.compile(stri, re.MULTILINE)
    if m := regex.search(content):
        return content, False, m.start()
    return (
        content[:end_index]
        + settings["template"].format(title=title)
        + "\n\n"
        + content[end_index:],
        True,
        end_index,
    )


def replace_section(content, title, new_title):
    """Check if section is in content"""
    stre = section_regex.format(
        prefix=settings["prefix"],
        title=title,
        suffix=settings["suffix"],
    )
    regex = re.compile(stre, re.MULTILINE)
    t = regex.subn(settings["template"].format(title=new_title), content)
    return t[0], t[1] > 0


def deduplicate_sections(content, title):
    """Check if section is in content"""
    stre = section_regex.format(
        prefix=settings["prefix"],
        title=title,
        suffix=(settings["suffix"] + r"[\n\r]*"),
    )
    regex = re.compile(stre, re.MULTILINE)
    if m := regex.search(content):
        # Remove all following instances of the section
        clean, changes = regex.subn("", content[m.end() :])
        if changes > 0:
            # Add the section back at the first instance
            content = content[: m.end()] + clean
        return content, changes > 0
    return content, False


def check_file(file: Path, fix):
    sections = []
    replace = []
    modified_file = False
    with open(file) as f:
        content = f.read()
    if file.suffix == ".h":
        sections = settings.get("header", [])
        replace = settings.get("replace", {}).get("header", [])
    elif file.suffix == ".c":
        sections = settings.get("source", [])
        replace = settings.get("replace", {}).get("source", [])
    for r in replace:
        content, changed = replace_section(content, r[0], r[1])
        modified_file |= changed
    end_index = len(content)
    if file.suffix == ".h":
        reg = re.search(section_area_end, content)
        end_index = reg.start() if reg else end_index
    for section in reversed(sections):
        content, changed, end_index = insert_section_at_end(
            content,
            section,
            end_index,
        )
        modified_file |= changed
    if settings["deduplicate"]:
        for section in sections:
            content, changed = deduplicate_sections(content, section)
            modified_file |= changed
    if not modified_file:
        return True
    if fix:
        with open(file, "w") as f:
            f.write(content)
        print("Inserted section(s) into %s" % (file))
    else:
        print("%s is missing section(s)" % (file))
    return False


def check_dir(p, fix):
    """Walk recursively over a directory checking .h files"""

    def prune(d):
        if d[0] == ".":
            return True
        return False

    all_good = True
    for root, dirs, paths in p.walk():
        # Prune dot directories like .git
        [dirs.remove(d) for d in list(dirs) if prune(d)]
        for path in paths:
            all_good &= check_file(root / path, fix)


def check_project(p, fix=False):
    p = Path(p).resolve()
    if p.is_dir():
        return check_dir(p, fix)
    else:
        return check_file(p, fix)


def main():
    parser = argparse.ArgumentParser(
        prog="CheckSections",
        description="Script to check source and header files for sections.",
    )
    parser.add_argument("filenames", nargs="*", help="Filenames to check")
    parser.add_argument(
        "--fix",
        action="store_true",
        help="Add missing section(s)",
        default=False,
    )
    args = parser.parse_args()
    all_good = True
    for p in args.filenames:
        all_good &= check_project(p, args.fix)
    if not all_good:
        print("Section(s) check failed")
        sys.exit(1)


if __name__ == "__main__":
    sys.exit(main())
