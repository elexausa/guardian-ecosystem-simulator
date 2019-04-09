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

from util import config_helper

# Define logger
logger = logging.getLogger(__name__)

@click.group()
def config():
    pass

@config.command()
@click.option('-a', '--address', required=True, help='Daemon IP address.')
@click.option('-p', '--port', required=True, help='Daemon port.')
def update_address(address, port):
    """Updates the IP address and port GES CLI points to.
    """
    config = configparser.ConfigParser()
    config.read(CONFIG_FILE)

    # Update config
    config["daemon"]["address"] = address
    config["daemon"]["port"] = port

    # Write file
    with open(CONFIG_FILE, 'w') as config_file:
        config.write(config_file)

    # Reload config
    config.load_config()

    logging.info('Updated daemon IP address and port to {}:{}'.format(address, port))