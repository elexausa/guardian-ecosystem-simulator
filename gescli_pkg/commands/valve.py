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
@click.option('-n', '--number', default=1, help='Number of valve controllers to spawn.')
@click.option('--leakdetectors', default=0, help='Number of leak detectors to spawn and auto pair (per valve!).')
def spawn(number, leakdetectors):
    # Create command
    command_str = DaemonCommand.SPAWN_VALVE.format(number=number)

    # Send
    ret = daemon_helper.send_command(command_str)

    # Check status
    if 'status' in ret:
        if ret['status'] == 'ok':
            print('Spawned {} valve controller(s)\n'.format(number))
            print('Metadata (serial #, UUID):')

            for valve_key, valve_val in ret['data'].items():
                print('  - {}, {}'.format(valve_key, valve_val))

                # Spawn leak detectors
                if leakdetectors > 0:
                    command_str = DaemonCommand.SPAWN_LEAK_DETECTOR.format(number=leakdetectors)
                    ret = daemon_helper.send_command(command_str)

                    # Check status
                    if 'status' in ret:
                        if ret['status'] == 'ok':
                            print('    > Spawned {} leak detector(s)'.format(leakdetectors))

                            # Pair to valve
                            for leakdetector_key, leakdetector_val in ret['data'].items():
                                command_str = DaemonCommand.PAIR_LEAK_DETECTOR.format(uuid=leakdetector_val, parent=valve_val)
                                ret = daemon_helper.send_command(command_str)

                                # Good pair?
                                if 'status' in ret:
                                    if ret['status'] == 'ok':
                                        print('        paired {} to {}'.format(leakdetector_key, valve_key))
                                    else:
                                        print('Error pairing! Daemon returned:\n\n{}'.format(json.dumps(ret, indent=4)))
                        else:
                            print('Error spawning! Daemon returned:\n\n{}'.format(json.dumps(ret, indent=4)))
        else:
            print('Error spawning! Daemon returned:\n\n{}'.format(json.dumps(ret, indent=4)))


