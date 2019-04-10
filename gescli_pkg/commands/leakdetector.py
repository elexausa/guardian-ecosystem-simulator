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
def leakdetector():
    pass

@leakdetector.command()
@click.option('-n', '--number', default=1, help='Number of leak detectors to spawn.')
def spawn(number):
    # Create command
    command_str = DaemonCommand.SPAWN_LEAK_DETECTOR.format(number=number)

    # Send
    ret = daemon_helper.send_command(command_str)

    if 'status' in ret:
        if ret['status'] == 'ok':
            print('Spawned {} leak detector(s)\n'.format(number))
            print('Metadata (Serial #, UUID):')
            for key, val in ret['data'].items():
                print('  - ({}, {})'.format(key, val))
        else:
            print('Error spawning! Daemon returned:\n\n{}'.format(json.dumps(ret, indent=4)))

@leakdetector.command()
@click.option('--uuid', required=True, help='The UUID (mac address) of the leak detector to pair.')
@click.option('--parent', required=True, help='The UUID (mac address) of the parent (valve controller) to pair.')
def pair(uuid, parent):
# Create command
    command_str = DaemonCommand.PAIR_LEAK_DETECTOR.format(uuid=uuid, parent=parent)

    # Send
    ret = daemon_helper.send_command(command_str)

    if 'status' in ret:
        if ret['status'] == 'ok':
            print('Successfully paired leak detector')
        else:
            print('Error pairing! Daemon returned:\n\n{}'.format(json.dumps(ret, indent=4)))
