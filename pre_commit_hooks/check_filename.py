#!/usr/bin/env python
# check against any src-files (.c, .h, .cpp) with capital letters in it. Suggest regex to fix it.(e.g. "MyFile.h" -> "my_file.h")
# search: ([a-z\d])([A-Z])
# replace: $1_\L$2
# check against folder naming convention (e.g. "MyFolder" -> "my-folder", "my_folder" -> "my-folder")
from __future__ import annotations

import os
import re
import sys

import git

allowed_filenames = re.compile(
    r"^([a-z\d\_\.]+|CMakeLists.txt|[A-Z\_]+.md|LICENSE)$",
)  # only lowercase letters, digits,  underscore and dot
allowed_folder_names = re.compile(
    r"^[a-z\d\_\-]+$",
)  # only lowercase letters, digits, underscore and hyphen


def check_file(project_path, filename):
    # check against folder naming convention (e.g. "MyFolder" -> "my-folder", "my_folder" -> "my-folder")
    path_elements = filename.relative_to(project_path).parts
    for element in path_elements:
        if not allowed_folder_names.match(element):
            print(f"Illegal folder name: {element} in {filename}")
            return False
    if not allowed_filenames.match(filename.name):
        print(f"Illegal file name: {filename}")
        return False
    return True


def check_dir(project_dir):
    """Walk recursively over a directory checking all files"""

    def prune(d):
        if d[0] == ".":
            return True
        return False

    all_good = True
    for root, dirs, paths in os.walk(project_dir):
        # Prune dot directories like .git
        [dirs.remove(d) for d in list(dirs) if prune(d)]
        for path in paths:
            all_good &= check_file(project_dir, os.path.join(root, path))
    return all_good


def check_project(project):
    p = os.path.abspath(project)
    if os.path.isdir(project):
        return check_dir(project)
    else:
        git_repo = git.Repo(project, search_parent_directories=True)
        return check_file(git_repo.working_dir, project)


def main():
    all_good = True
    for p in sys.argv[1:]:
        all_good &= check_project(p)
    if not all_good:
        print("Filename check failed")
        sys.exit(1)


if __name__ == "__main__":
    sys.exit(main())
