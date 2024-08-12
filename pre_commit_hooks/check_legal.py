#!/usr/bin/env python
"""Script to check files for a license-notice."""
from __future__ import annotations

import argparse
import html
import re
import subprocess
from datetime import datetime
from enum import IntEnum
from pathlib import Path

GPL3_LICENSE_NOTICE = """ This file is part of {project_name}.

 {project_name} is free software: you can redistribute it and/or modify
 it under the terms of the GNU General Public License as published by
 the Free Software Foundation, either version 3 of the License, or
 (at your option) any later version.

 {project_name} is distributed in the hope that it will be useful,
 but WITHOUT ANY WARRANTY; without even the implied warranty of
 MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 GNU General Public License for more details.

 You should have received a copy of the GNU General Public License
 along with {project_name}.  If not, see <https://www.gnu.org/licenses/>."""

UNLICENSE_NOTICE = """ This file is part of {project_name}.

 This is free and unencumbered software released into the public domain.

 Anyone is free to copy, modify, publish, use, compile, sell, or
 distribute this software, either in source code form or as a compiled
 binary, for any purpose, commercial or non-commercial, and by any
 means.

 In jurisdictions that recognize copyright laws, the author or authors
 of this software dedicate any and all copyright interest in the
 software to the public domain. We make this dedication for the benefit
 of the public at large and to the detriment of our heirs and
 successors. We intend this dedication to be an overt act of
 relinquishment in perpetuity of all present and future rights to this
 software under copyright law.

 THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
 EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
 MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
 IN NO EVENT SHALL THE AUTHORS BE LIABLE FOR ANY CLAIM, DAMAGES OR
 OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE,
 ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
 OTHER DEALINGS IN THE SOFTWARE.

 For more information, please refer to <http://unlicense.org/>"""


class State(IntEnum):
    Initial = (0,)
    Start = (1,)
    Found = (2,)


def get_authors(filename, aliases, args):
    lines = []
    result = subprocess.run(
        [
            "git",
            "--no-pager",
            "log",
            "--pretty=format:%an|%ad",
            "--date=format:%Y",
            "--follow",
            "--",
            filename,
        ],
        stdout=subprocess.PIPE,
    )
    result = result.stdout.decode("utf-8")
    if result:
        lines = result.split("\n")
    if not lines:
        username = subprocess.run(
            ["git", "config", "user.name"],
            stdout=subprocess.PIPE,
        )
        username = username.stdout.decode("utf-8").strip()
        lines = ["|".join([username, datetime.now().strftime("%Y")])]
    authors = {}
    for line in lines:
        pair = line.split("|")
        author = aliases.get(pair[0], pair[0])
        date = pair[1]
        dates = authors.get(author, [])
        dates.append(date)
        authors[author] = sorted(set(dates))
    lines = []
    for author, dates in authors.items():
        lines.append(
            args.copyright_string + " " + ", ".join(dates) + " " + author,
        )
    return "\n".join(sorted(lines))


def full_notice(filename, aliases, args):
    result = []
    if args.preamble:
        result += args.preamble.format(
            project_name=args.programme_name,
            authors=get_authors(filename, aliases, args),
            license_notice=args.license_notice,
        ).splitlines()
    result += args.template.format(
        project_name=args.programme_name,
        authors=get_authors(filename, aliases, args),
        license_notice=args.license_notice,
    ).splitlines()
    if args.postamble:
        result += args.postamble.format(
            project_name=args.programme_name,
            authors=get_authors(filename, aliases, args),
            license_notice=args.license_notice,
        ).splitlines()
    string = args.line_start + f"\n{args.line_start}".join(result)
    return f"{args.comment_start}\n{string}\n{args.comment_end}"


def add_comment(content, filename, aliases, full_notice):
    position = 0
    length = len(content)
    state = State.Initial
    start = 0
    end = 0
    while position != length:
        if state == State.Initial:
            idx = content.find("/*", position)
            if idx != -1:
                state = State.Start
                position = idx
                start = idx
            else:
                position = length
        elif state == State.Start:
            idx1 = content.find(full_notice, position)
            idx2 = content.find("*/", position)
            if idx1 != -1 and idx2 != -1 and idx1 < idx2:
                state = State.Found
                end = idx2 + 2
                position = length
            elif idx1 != -1 and idx2 != -1:
                state = State.Initial
                position = min(idx1, idx2)
            elif idx1 != -1 and idx2 == -1:
                state = State.Initial
                position = idx1
            elif idx1 == -1 and idx2 != -1:
                state = State.Initial
                position = idx2
            else:
                state = State.Initial
                position = length
    if state == State.Found:
        content = content[:start] + full_notice + content[end:]
    else:
        content = full_notice + "\n\n" + content
    return content


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Prepend/update copyright and license notices",
    )
    parser.add_argument("filenames", nargs="*", help="Filenames to check")
    parser.add_argument(
        "-c",
        "--copyright-string",
        help="Minimum copyright string that must be present in the comment, defaults to template",
        default="",
    )
    parser.add_argument(
        "-p",
        "--name",
        help="Name of the project",
        default="Foobar",
        dest="programme_name",
    )
    parser.add_argument("--preamble", help="Comment preamble", default="")
    parser.add_argument(
        "-l",
        "--license-notice",
        help="License template",
        default="gpl3+",
        choices=["gpl3+", "unlicense", "custom"],
    )
    parser.add_argument(
        "--template",
        help="Custom license template",
        default="",
    )
    parser.add_argument("--postamble", help="Comment postamble", default="")
    parser.add_argument(
        "--alias",
        action="append",
        help="Define author alias",
        default=[],
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Do not change files",
    )
    parser.add_argument(
        "--dir",
        action="store_true",
        help="The root directory of the Project.",
        dest="_dir",
        default=".",
    )
    parser.add_argument(
        "--comment-start",
        help="The start of the comment block.",
        default="/*",
    )
    parser.add_argument(
        "--comment-end",
        help="The end of the comment block.",
        default=" */",
    )
    parser.add_argument(
        "--line-start",
        help="Start of each line new line in the comment block.",
        default=" *",
    )
    args = parser.parse_args(argv)
    if args.license_notice == "gpl3+":
        args.template = GPL3_LICENSE_NOTICE
    elif args.license_notice == "unlicense":
        args.template = UNLICENSE_NOTICE
    elif not args.template:
        print("No license template provided")
        return 1
    args.template = html.unescape(args.template)
    args.copyright_string = html.unescape(args.copyright_string)
    aliases = {}
    for alias in args.alias:
        pair = alias.split(":")
        aliases[pair[0]] = pair[1]
    ret = 0
    _dir = Path(args._dir)
    for filename in args.filenames:
        notice = full_notice(filename, aliases, args)
        if not args.copyright_string:
            args.copyright_string = notice
        content = None
        file = _dir / filename
        with open(file.resolve(), encoding="utf-8") as f:
            content = f.read()
        if re.search(args.copyright_string, content, re.IGNORECASE):
            continue
        new_content = add_comment(content, filename, aliases, notice)
        if new_content != content:
            content = new_content
            ret = 1
            if args.dry_run:
                print(f"{filename}: missing copyright/license notice")
            else:
                print(f"{filename}: update copyright/license notice")
                with open(filename, "w", encoding="utf-8") as f:
                    f.write(content)
    return ret


if __name__ == "__main__":
    if (
        main(
            [
                "tests/a.h",
                "tests/b.h",
                "-l",
                "custom",
                "--template",
                "Some\nmultiline\nlicense",
                "--alias",
                "John:Doe",
                "--alias",
                "Jane:Smith",
                "-c",
                "license",
            ],
        )
        != 1
    ):
        exit(1)
    if (
        main(
            [
                "tests/c.h",
                "-l",
                "custom",
                "--template",
                "Some\nmultiline\nlicense",
                "--alias",
                "John:Doe",
                "--alias",
                "Jane:Smith",
                "-c",
                "license",
            ],
        )
        != 0
    ):
        exit(1)
    if (
        main(
            [
                "tests/c.h",
                "-l",
                "gpl3+",
                "--alias",
                "John:Doe",
                "--alias",
                "Jane:Smith",
                "--name",
                "test-project",
            ],
        )
        != 0
    ):
        exit(1)
    if (
        main(
            [
                "tests/c.h",
                "-l",
                "custom",
                "--alias",
                "John:Doe",
                "--alias",
                "Jane:Smith",
                "--name",
                "test-project",
            ],
        )
        != 1
    ):
        exit(1)
