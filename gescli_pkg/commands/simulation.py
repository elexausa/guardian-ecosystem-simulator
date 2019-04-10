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

from . import DaemonCommand
from util import daemon_helper

# Define logger
logger = logging.getLogger(__name__)

@click.group()
def simulation():
    pass

@simulation.command()
@click.option('-t', '--time', type=int, help="How long to run the simulation (in seconds)")
def run(time):
    # Create command
    if time is not None:
        command_str = DaemonCommand.RUN_WITH_TIME_LIMIT.format(time=time)
    else:
        command_str = DaemonCommand.RUN

    # Send
    daemon_helper.send_command(command_str)

@simulation.command()
def kill():
    # Create command
    command_str = DaemonCommand.KILL

    # Send
    daemon_helper.send_command(command_str)