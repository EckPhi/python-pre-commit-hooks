#!/usr/bin/env python
"""Script to check C and C++ file header guards.
This script accepts a list of file or directory arguments. If a given
path is a file, it runs the checker on it. If the path is a directory,
it runs the checker on all files in that directory.
The following file
    src/abc_xyz/xyz.h
produces ABC_XYZ_XYZ_H_ as a header guard.
"""
from __future__ import annotations

import argparse
import collections
import os.path
import pathlib
import re
import sys

import git


all_header_guards = collections.defaultdict(list)
pragma_once = re.compile("^#pragma once$")


def get_header_guard(project_path, header_file):
    """A header guard can either be a #pragma once, or else a matching set of
        #ifndef PATH_TO_FILE_H_
        #define PATH_TO_FILE_H_
        ...
        #endif  // PATH_TO_FILE_H_
    preprocessor directives, where both '.' and '/' in the path are
    mapped to '_', and a trailing '_' is appended.
    """

    def dir_guard(path):
        """Convert a path to a header guard."""
        if type(path) in [list, tuple]:
            path = "_".join(path)
        return (
            path.upper()
            .replace(".", "_")
            .replace("/", "_")
            .replace("\\", "_")
            .replace("-", "_")
            + "_"
        )

    header_guard = dir_guard(
        [os.path.basename(project_path)]
        + list(
            pathlib.Path(os.path.relpath(header_file, project_path)).parts[1:],
        ),
    )

    return header_guard


def check_file(project_path, header_file):
    """Check whether the file has a correct header guard.
    In either the #pragma once case or the header guard case, it is
    assumed that there is no trailing or leading whitespace.
    """

    # Only check .h files
    if header_file[-2:] != ".h":
        return True
    header_guard = get_header_guard(project_path, header_file)
    all_header_guards[header_guard].append(header_file)
    ifndef = re.compile("^#ifndef %s$" % header_guard)
    define = re.compile("^#define %s$" % header_guard)
    endif = re.compile("^#endif +// %s$" % header_guard)
    found_pragma_once = False
    found_ifndef = False
    found_define = False
    found_endif = False
    with open(header_file) as f:
        for line in f.readlines():
            match = pragma_once.match(line)
            if match:
                if found_pragma_once:
                    print("%s contains multiple #pragma once" % header_file)
                    return False
                found_pragma_once = True
            match = ifndef.match(line)
            if match:
                if found_ifndef:
                    print(
                        "%s contains multiple ifndef header guards"
                        % header_file,
                    )
                    return False
                found_ifndef = True
            match = define.match(line)
            if match:
                if found_define:
                    print(
                        "%s contains multiple define header guards"
                        % header_file,
                    )
                    return False
                found_define = True
            match = endif.match(line)
            if match:
                if found_endif:
                    print(
                        "%s contains multiple endif header guards"
                        % header_file,
                    )
                    return False
                found_endif = True
    if found_pragma_once:
        if found_ifndef or found_define or found_endif:
            print(
                "%s contains both #pragma once and header guards" % header_file,
            )
            return False
        return True
    if found_ifndef and found_define and found_endif:
        return True
    if found_ifndef or found_define or found_endif:
        print("%s contained only part of a header guard" % header_file)
        return False
    print(
        f'{header_file} contained neither "{header_guard}" header guard nor #pragma once',
    )
    return False


def add_header_guard(project_path, header_file):
    # Only check .h files
    if header_file[-2:] != ".h":
        return True
    header_guard = get_header_guard(project_path, header_file)
    with open(header_file) as f:
        content = f.read()
    lines = content.split("\n")
    top = [
        f"#ifndef {header_guard}",
        f"#define {header_guard}",
        "",
    ]
    bottom = ["", f"#endif  // {header_guard}", ""]
    lines += bottom
    if len(lines) > 0 and "/*" in lines[0]:
        # find end of comment block
        license_end = 0
        for i, line in enumerate(lines):
            if "*/" in line:
                license_end = i + 1
                break
        lines = lines[:license_end] + [""] + top + lines[license_end:]
    else:
        lines = top + lines
    with open(header_file, "w") as f:
        f.write("\n".join(lines))
    all_header_guards[header_guard].append(header_file)


def check_and_fix_file(project_path, header_file, fix):
    result = check_file(project_path, header_file)
    if not result and fix:
        add_header_guard(project_path, header_file)
        print(f"Modified {header_file}")
    return result


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
            all_good &= check_and_fix_file(p, os.path.join(root, path), fix)
    return all_good


def check_collisions():
    all_good = True
    for header_guard, paths in all_header_guards.items():
        if len(paths) == 1:
            continue
        print("Multiple files could use %s as a header guard:" % header_guard)
        for path in paths:
            print("    %s" % path)
        all_good = False
    return all_good


def check_project(p, fix):
    p = os.path.abspath(p)
    if os.path.isdir(p):
        return check_dir(p, fix)
    else:
        git_repo = git.Repo(p, search_parent_directories=True)
        return check_and_fix_file(git_repo.working_dir, p, fix)


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="CheckHeaderGuards",
        description="Script to check C headers for correct include guards.",
    )
    parser.add_argument("filenames", nargs="*", help="Filenames to check")
    parser.add_argument(
        "--fix",
        action="store_true",
        help="Add missing include guards to files.",
        default=False,
    )
    args = parser.parse_args(argv)
    all_good = True
    for p in args.filenames:
        all_good &= check_project(p, args.fix)
    all_good &= check_collisions()
    if not all_good:
        print("Header guard check failed")
        return 1


if __name__ == "__main__":
    if (
        main(
            [
                "tests/a.h",
                "tests/b.h",
                "tests/c.h",
                "tests/a.c",
                "tests/b.c",
                "tests/c.c",
            ],
        )
        != 1
    ):
        exit(1)
    if (
        main(
            [
                "tests/a.h",
                "tests/b.h",
                "tests/c.h",
                "tests/a.c",
                "tests/b.c",
                "tests/c.c",
                "--fix",
            ],
        )
        != 1
    ):
        exit(1)
