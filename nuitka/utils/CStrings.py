#     Copyright 2016, Kay Hayen, mailto:kay.hayen@gmail.com
#
#     Part of "Nuitka", an optimizing Python compiler that is compatible and
#     integrates with CPython, but also works on its own.
#
#     Licensed under the Apache License, Version 2.0 (the "License");
#     you may not use this file except in compliance with the License.
#     You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
#     Unless required by applicable law or agreed to in writing, software
#     distributed under the License is distributed on an "AS IS" BASIS,
#     WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#     See the License for the specific language governing permissions and
#     limitations under the License.
#
""" C++ string encoding

This contains the code to create string literals for C++ to represent the given
values and little more.
"""

import re

from nuitka.__past__ import unicode  # pylint: disable=W0622


def _encodePythonStringToC(value):
    """ Encode a string, so that it gives a C++ string literal.

        This doesn't handle limits.
    """
    assert type(value) is bytes, type(value)

    result = ""
    octal = False

    for c in value:
        if str is not unicode:
            cv = ord(c)
        else:
            cv = c

        if c in b'\\\t\r\n"?':
            result += r'\%o' % cv

            octal = True
        elif cv >= 32 and cv <= 127:
            if octal and c in b'0123456789':
                result += '" "'

            result += chr(cv)

            octal = False
        else:
            result += r'\%o' % cv

            octal = True

    result = result.replace('" "\\', '\\')

    return '"%s"' % result


def encodePythonStringToC(value):
    """ Encode a string, so that it gives a C string literal.

    """

    # Not all compilers don't allow arbitrary large C++ strings,
    # therefore split it up into chunks. That changes nothing to
    # the meanings, but is easier on the parser. Currently only
    # MSVC is known to have this issue, but the workaround can be
    # used universally.

    result = _encodePythonStringToC(value[:16000 ])
    value = value[16000:]

    while len(value) > 0:
        result += ' '
        result += _encodePythonStringToC(value[:16000 ])
        value = value[16000:]

    return result


def encodePythonIdentifierToC(value):
    """ Encode an identifier from a given Python string.

    """

    # Python identifiers allow almost of characters except a very
    # few, much more than C identifiers support. This attempts to
    # be bi-directional, so we can reverse it.

    def r(match):
        c = match.group()

        if c == '.':
            return '$'
        else:
            return "$$%d$" % ord(c)

    return "".join(
        re.sub("[^a-zA-Z0-9_]", r ,c)
        for c in
        value
    )
