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

import logging
import socket
import json

# Define logger
logger = logging.getLogger(__name__)

# Daemon communication
DAEMON_ADDRESS = '127.0.0.1'
DAEMON_PORT = '7700'

def send_command(command):
    """Open socket and send command.
    """
    # Define socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    try:
        # Send
        sock.sendto(command.encode(), (DAEMON_ADDRESS, int(DAEMON_PORT)))

        logger.info('Command sent')
        logger.debug('Command sent: {}'.format(json.dumps(command)))
    except Exception as e:
        logger.error("Could not communicate with daemon! Check configuration. (err: %s)" % str(e))
        # Failed
        return False
    finally:
        # Close
        sock.close()

        # Success
        return True
