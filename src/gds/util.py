#!/usr/bin/env python
#
# Copyright (C) 2019 Elexa Consumer Product, Inc.
#
# This file is part of the Guardian Device Simulator
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

import random
import string
import time

def string_generator(size=16, chars=string.hexdigits.upper()):
    """Generates string with provided `size` from characters in `chars`.

    Args:
        size (int, optional): Defaults to 16. Size of the string to generate
            in characters.
        chars ([type], optional): Defaults to string.hexdigits.upper(). Where
            to pull characters from for string.

    Returns:
        str: Randomly generated string
    """
    return ''.join(random.choice(chars) for _ in range(size))

