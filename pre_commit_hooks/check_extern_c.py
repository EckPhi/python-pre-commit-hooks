#!/usr/bin/env python
"""Script to check C headers for extern c."""
from __future__ import annotations

import argparse
import os.path
import pathlib
import re
import sys

import git

extern_c = {
    "condition": "#ifdef __cplusplus",
    "content_head": 'extern "C" {',
    "content_tail": "}",
    "end_condition": "#endif",
}
extern_c_regex = (
    "^({condition})[\n\r]{{0,2}}\\s*({content})[\n\r]{{0,2}}({end_condition})$"
)
extern_c_head = re.compile(
    extern_c_regex.format(
        condition=extern_c["condition"],
        content=extern_c["content_head"],
        end_condition=extern_c["end_condition"],
    ),
    re.MULTILINE,
)
extern_c_tail = re.compile(
    extern_c_regex.format(
        condition=extern_c["condition"],
        content=extern_c["content_tail"],
        end_condition=extern_c["end_condition"],
    ),
    re.MULTILINE,
)
extern_c_head_after = re.compile(
    "^(/\\* -+)[\n\r]{0,2}\\s*(\\*\\sfunction declarations)[\n\r]{0,2}\\s*(\\* -+ \\*/)[\n\r]{0,2}",
    re.MULTILINE,
)
extern_c_tail_before = re.compile(r"^#endif\s+//\s+[A-Z_\d]+_H_", re.MULTILINE)


def check_file(project_path, header_file, fix):
    """Check whether the file contains a correct extern c.
        #ifdef __cplusplus
        extern "C" {
        #endif
        ...
        #ifdef __cplusplus
        }
        #endif
    it is assumed that there is no trailing or leading whitespace.
    """
    # Only check .h files
    if header_file[-2:] != ".h":
        return True
    found_head = False
    found_tail = False
    with open(header_file) as f:
        content = f.read()
    found_head = extern_c_head.search(content)
    found_tail = extern_c_tail.search(content)
    if found_head and found_tail:
        return True
    if fix:
        insert_extern_c(project_path, header_file)
        print(
            'Inserted extern "C" linkage-specification into %s' % (header_file),
        )
    else:
        print(
            '%s contained no extern "C" linkage-specification' % (header_file),
        )
    return False


def insert_extern_c(project_path, header_file):
    """Insert the extern "C" linkage-specification into the content"""
    # function declaration section
    head_insert = f'{extern_c["condition"]}\n{extern_c["content_head"]}\n{extern_c["end_condition"]}\n\n'
    tail_insert = f'{extern_c["condition"]}\n{extern_c["content_tail"]}\n{extern_c["end_condition"]}\n\n'
    with open(header_file) as f:
        content = f.read()
    extern_c_head_after_found = extern_c_head_after.search(content)
    if extern_c_head_after_found:
        content = (
            content[: extern_c_head_after_found.end()]
            + head_insert
            + content[extern_c_head_after_found.end() :]
        )
    extern_c_tail_before_found = extern_c_tail_before.search(content)
    if extern_c_tail_before_found:
        if extern_c_head_after_found:
            content = (
                content[: extern_c_tail_before_found.start()]
                + tail_insert
                + content[extern_c_tail_before_found.start() :]
            )
        else:
            content = (
                content[: extern_c_tail_before_found.start()]
                + head_insert
                + tail_insert
                + content[extern_c_tail_before_found.start() :]
            )
    else:
        content = head_insert + content + tail_insert
    with open(header_file, "w") as f:
        f.write(content)


def check_dir(p, fix):
    """Walk recursively over a directory checking .h files"""

    def prune(d):
        """Check if dir is invisible/starts with '.'"""
        if d[0] == ".":
            return True
        return False

    all_good = True
    for root, dirs, paths in os.walk(p):
        # Prune dot directories like .git
        [dirs.remove(d) for d in list(dirs) if prune(d)]
        for path in paths:
            all_good &= check_file(p, os.path.join(root, path), fix)


def check_project(p, fix=False):
    """Check an entire project directory"""
    p = os.path.abspath(p)
    if os.path.isdir(p):
        return check_dir(p, fix)
    else:
        git_repo = git.Repo(p, search_parent_directories=True)
        return check_file(git_repo.working_dir, p, fix)


def main():
    parser = argparse.ArgumentParser(
        prog="CheckExternC",
        description="Script to check C headers for extern c.",
    )
    parser.add_argument("filenames", nargs="*", help="Filenames to check")
    parser.add_argument(
        "--fix",
        action="store_true",
        help='Add missing extern "C" linkage-specification',
        default=False,
    )
    args = parser.parse_args()
    all_good = True
    for p in args.filenames:
        all_good &= check_project(p, args.fix)
    if not all_good:
        print('Extern "C" linkage-specification check failed')
        sys.exit(1)


if __name__ == "__main__":
    sys.exit(main())
