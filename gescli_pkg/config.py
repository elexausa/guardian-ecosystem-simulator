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

# Determine package location on host
__location__ = os.path.realpath(os.path.join(os.getcwd(), os.path.dirname(__file__)))

# Open version file
version_file = open(os.path.join(__location__, 'VERSION'))

# Get version number
version = version_file.read().strip()