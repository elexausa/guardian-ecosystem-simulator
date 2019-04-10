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
import json
import logging

from . import DaemonCommand
from util import daemon_helper

# Define logger
logger = logging.getLogger(__name__)

@click.group()
def valve():
    pass

@valve.command()
@click.option('-c', '--count', default=1, help='Number of Valve Controllers to spawn.')
def spawn(count):
    # Create command
    command_str = DaemonCommand.SPAWN_VALVE.format(count=count)

    # Send
    ret = daemon_helper.send_command(command_str)
    
    if 'status' in ret:
        if ret['status'] == 'ok':
            print('Spawned {} valve controller(s)\n'.format(count))
            print('Metadata (Serial #, UUID):')
            for key, val in ret['data'].items():
                print('  - ({}, {})'.format(key, val))
        else:
            print('Error spawning! Daemon returned:\n\n{}'.format(json.dumps(ret, indent=4)))