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

def abort_if_false(ctx, param, value):
    """Utility to abort command execution if provided boolean is false.
    """
    if not value:
        ctx.abort()

@click.group()
def data():
    pass

@data.command()
@click.option('-f', '--from', required=True, type=click.Choice(['file', 'db']))
@click.option('-y', '--yes', is_flag=True, callback=abort_if_false, expose_value=False,
              prompt='This will overwrite all current data on the simulator. Proceed?')
def load():
    logging.error('Not implemented')

