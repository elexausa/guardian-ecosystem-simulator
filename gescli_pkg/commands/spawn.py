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

import click
import logging

from . import Simulation_Commands
from util import daemon_helper

# Define logger
logger = logging.getLogger(__name__)

@click.group()
def spawn():
    pass

@spawn.command()
@click.option('-c', '--count', default=1, help='Number of Valve Controllers to spawn.')
def valve(type, count):
    # Create command
    command_str = Commands.SPAWN.format(type=type, count=count, data=None)

    # Send
    daemon.send_command(spawn)