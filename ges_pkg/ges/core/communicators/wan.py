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

import multiprocessing
import threading
import dataclasses
import datetime
import string
import json
import logging
import socket
import simpy
import typing
from enum import Enum, IntEnum, auto

from ..communication import Communicator, BasePacket
from ..drivers import gcloud_functions

###################
## Configuration ##
###################

# Define logger
logger = logging.getLogger(__name__)

SERVER_IP = 'localhost'
SERVER_PORT = 7710

######################
## Setup TCP server ##
######################

# Define server
server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

# Bind
server.bind((SERVER_IP, SERVER_PORT))
server.listen()

##################
## Packet types ##
##################

class OperationType(IntEnum):
    UNKNOWN = auto()

    FAMILY_ADD_CHILDREN = auto()
    FAMILY_ADD_GROUPS = auto()
    FAMILY_ADD_PERMISSIONS = auto()
    FAMILY_ADD_USER = auto()
    FAMILY_CREATE = auto()
    FAMILY_DELETE = auto()
    FAMILY_DELETE_PERMISSIONS = auto()
    FAMILY_REMOVE_CHILD = auto()
    FAMILY_REMOVE_USER = auto()
    FAMILY_REMOVE_GROUP = auto()
    FAMILY_SET_PARENT = auto()

    INACTIVE_SET_INACTIVE = auto()

    MACHINE_CREATE = auto()
    MACHINE_DELETE = auto()
    MACHINE_REGISTER_SETTING = auto()
    MACHINE_REGISTER_STATE = auto()
    MACHINE_UPDATE_SETTING = auto()
    MACHINE_UPDATE_STATE = auto()

    USER_CREATE = auto()
    USER_DELETE = auto()
    USER_SET_EMAIL = auto()
    USER_SET_FNAME = auto()
    USER_SET_LNAME = auto()

    EVENTS_CREATE = auto()


@dataclasses.dataclass
class OperationPacket(BasePacket):
    type: OperationType = OperationType.UNKNOWN
    data: dict = typing.Dict


class EventType(IntEnum):
    UNKNOWN = auto()
    HEARTBEAT = auto()
    LEAK_DETECTED = auto()
    LEAK_CLEARED = auto()
    VALVE_OPENING = auto()
    VALVE_OPENED = auto()
    VALVE_CLOSING = auto()
    VALVE_CLOSED = auto()
    VALVE_STUCK = auto()


##################
## Communicator ##
##################

class WAN(Communicator, multiprocessing.Process):
    """Simulated WAN network.

    - Forwards message to configured Guardian Cloud
    endpoint to provide SITL integration.
    - Sets up TCP endpoint to receive messages
    """

    def __init__(self, env):
        """Initializes WAN

        Args:
            env (simpy.core.BaseEnvironment): simpy environment instance
        """
        Communicator.__init__(self, env)
        multiprocessing.Process.__init__(self, name='ges-ip-network')

        logging.info('Starting WAN communicator')

        # Immediately start self process
        self.start()

    def send(self, packet: BasePacket):
        """Preproccesses packet and performs relevant
        Cloud Function calls then forwards packet to
        super().send_raw().

        Args:
            packet (Packet): Requires Packet dataclass
        """
        # Pass to gcloud functions for processing
        gcloud_functions.process(packet)

        # Pass to super for sending to communicator pipes
        self.send_raw(packet)

    def handle_client_connection(self, client_socket):
        """Handles `client_socket`.

        Receives request and forwards data to local WAN
        for processing by any attached device instances.

        Also responds to request with acknowledgment.

        Args:
            client_socket (socket.socket): Socket to handle.
        """
        # Receive client data
        request = client_socket.recv(1024)
        logging.info('Received {}'.format(request))

        # Pass to super
        # TODO: Forward socket for responding - AB 03/12/2019
        self.send_raw(request)

        # Acknowledge
        # FIXME: send something else; let target device handle? - AB 03/12/2019
        client_socket.send('ACK')

        # Close connection
        client_socket.close()

    def run(self):
        """Runs continuously to process incoming connections.

        When external client connects, a thread is spawned to
        handle the request.
        """
        try:
            while True:
                # Wait for and accept next connection
                client_socket, address = server.accept()

                logging.info('Accepted connection from {}:{}'.format(address[0], address[1]))

                # Create handler thread
                client_handler = threading.Thread(
                    target=self.handle_client_connection,
                    args=(client_socket,)
                )

                # Start thread
                client_handler.start()
        except (KeyboardInterrupt, SystemExit):
            logging.warn('WAN server killed')
