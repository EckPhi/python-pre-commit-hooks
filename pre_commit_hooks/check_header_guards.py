#!/usr/bin/env python
"""Script to check C and C++ file header guards.
This script accepts a list of file or directory arguments. If a given
path is a file, it runs the checker on it. If the path is a directory,
it runs the checker on all files in that directory.
In addition, this script checks for potential header guard
collisions. This is useful since we munge / to _, and so
    lib/abc/xyz/xyz.h
and
    lib/abc_xyz/xyz.h
both want to use LIB_ABC_XYZ_XYZ_H_ as a header guard.
"""
from __future__ import annotations

import collections
import os.path
import pathlib
import re
import sys

import git


all_header_guards = collections.defaultdict(list)
pragma_once = re.compile("^#pragma once$")


def check_file(project_path, header_file):
    """Check whether the file has a correct header guard.
    A header guard can either be a #pragma once, or else a matching set of
        #ifndef PATH_TO_FILE_
        #define PATH_TO_FILE_
        ...
        #endif  // PATH_TO_FILE_
    preprocessor directives, where both '.' and '/' in the path are
    mapped to '_', and a trailing '_' is appended.
    In either the #pragma once case or the header guard case, it is
    assumed that there is no trailing or leading whitespace.
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

    # Only check .h files
    if header_file[-2:] != ".h":
        return True
    project_name = dir_guard(os.path.basename(project_path))
    header_guard = project_name + dir_guard(
        pathlib.Path(os.path.relpath(header_file, project_path)).parts[1:],
    )
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


def check_dir(p):
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
            all_good &= check_file(p, os.path.join(root, path))
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


def check_project(p):
    p = os.path.abspath(p)
    if os.path.isdir(p):
        return check_dir(p)
    else:
        git_repo = git.Repo(p, search_parent_directories=True)
        return check_file(git_repo.working_dir, p)


def main():
    all_good = True
    for p in sys.argv[1:]:
        all_good &= check_project(p)
    all_good &= check_collisions()
    if not all_good:
        print("Header guard check failed")
        sys.exit(1)


if __name__ == "__main__":
    sys.exit(main())
