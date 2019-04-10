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

import os
import setuptools

__location__ = os.path.realpath(os.path.join(os.getcwd(), os.path.dirname(__file__)))

# Open version file
version_file = open(os.path.join(__location__, 'VERSION'))

# Get version number
version = version_file.read().strip()

setuptools.setup(
    name='guardian-ecosystem-simulator-cli',
    version=version,
    scripts=['ges'] ,
    author="Alex Bennett",
    author_email="abennett@elexausa.com",
    description="Guardian IoT ecosystem simulator CLI",
    long_description="CLI for control of guardian-ecosystem-simulator-daemon_helper.",
    url="https://github.com/elexausa/guardian-ecosystem-simulator",
    packages=setuptools.find_packages(),
    install_requires=[
        'Click==7.0',
        'guardian-ecosystem-simulator'
    ],
    classifiers=[
        "Programming Language :: Python :: 3",
        "Operating System :: OS Independent",
    ],
 )
