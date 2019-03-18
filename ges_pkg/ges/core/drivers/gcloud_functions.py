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

from enum import Enum
import requests
import json
import logging
import threading

from ..communication import Communicator

# Define logger
logger = logging.getLogger(__name__)

# TODO: Remove from VCS
ENDPOINT = "https://us-central1-guardian-ecoystem-simulator.cloudfunctions.net/{function_name}"


class Functions(Enum):
    hello_cloud = 'hello_cloud' # Simple "ping/pong", returns ACK
    sync_device = 'sync_device' # Syncs device to firebase, requires serialized device


def call_function(name: str, data: dict):
    try:
        logger.info('Calling cloud function %s' % name)
        r = requests.post(url=ENDPOINT.format(function_name=name), data=json.dumps(data), headers={'Content-type': 'application/json'})
    except Exception as e: # TODO: Handle specific exceptions
        logger.warn('Could not call cloud function (error: %s)' % str(e))
    else:
        logger.warn('Cloud function called, result: %s' % str(r.content))

def process(packet: Communicator.Packet):
    """Parse raw message and call relevant cloud function.
    """
    logger.debug("Processing packet")

    # Call the function in separate thread
    threading.Thread(target=call_function, args=('sync_device', packet.data,)).start()
