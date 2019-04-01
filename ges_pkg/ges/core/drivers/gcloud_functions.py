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


class Cloud_Functions(str, Enum):
    # HELLO_CLOUD = 'hello_cloud' # Simple "ping/pong", returns ACK
    # SYNC_DEVICE = 'sync_device' # Syncs device to firebase, requires serialized device
    # CREATE_MACHINE = 'machine_create_machine' # Creates new machine in firebase

    FAMILY_ADD_CHILDREN = 'family_add_children'
    FAMILY_ADD_GROUP = 'family_add_group'
    FAMILY_ADD_PERMISSIONS = 'family_add_permissions'
    FAMILY_ADD_USER = 'family_add_user'
    FAMILY_CREATE_FAMILY = 'family_create_user'
    FAMILY_DELETE_GROUP = 'family_delete_group'
    FAMILY_DELETE_PERMISSIONS = 'family_delete_permissions'
    FAMILY_DELETE_USER = 'family_delete_user'
    FAMILY_KILL_CHILDREN = 'family_kill_children'
    FAMILY_SET_PARENT = 'family_set_parent'
    
    INACTIVE_SET_INACTIVE = 'inactive_set_inactive'

    MACHINE_CREATE_MACHINE = 'machine_create_machine'
    MACHINE_DELETE_MACHINE = 'machine_delete_machine'
    MACHINE_REGISTER_SETTING = 'machine_register_setting'
    MACHINE_REGISTER_STATE = 'machine_register_state'
    MACHINE_UPDATE_SETTING = 'machine_update_setting'
    MACHINE_UPDATE_STATE = 'machine_update_state'

    USER_ADD_FAMILIES = 'user_add_families'
    USER_CREATE_USER = 'user_create_user'
    USER_DELETE_FAMILIES = 'user_delete_families'
    USER_DELETE_USER = 'user_delete_user'
    USER_SET_EMAIL = 'user_set_email'
    USER_SET_FNAME = 'user_set_fname' # Sets user's first name
    USER_SET_LNAME = 'user_set_lname' # Sets user's last name

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

    # Default values
    function_name = 'hello_cloud'
    payload = {}

    # Handle operation packet
    if isinstance(packet, Communicator.OperationPacket):
        # Set function depending on type of operation
        if packet.type is Communicator.OperationPacket.Type.FAMILY_ADD_CHILDREN:
            function_name = Cloud_Functions.FAMILY_ADD_CHILDREN
        if packet.type is Communicator.OperationPacket.Type.FAMILY_ADD_GROUP:
            function_name = Cloud_Functions.FAMILY_ADD_GROUP
        if packet.type is Communicator.OperationPacket.Type.FAMILY_ADD_PERMISSIONS:
            function_name = Cloud_Functions.FAMILY_ADD_PERMISSIONS
        if packet.type is Communicator.OperationPacket.Type.FAMILY_ADD_USER:
            function_name = Cloud_Functions.FAMILY_ADD_USER
        if packet.type is Communicator.OperationPacket.Type.FAMILY_CREATE_FAMILY:
            function_name = Cloud_Functions.FAMILY_CREATE_FAMILY
        if packet.type is Communicator.OperationPacket.Type.FAMILY_DELETE_GROUP:
            function_name = Cloud_Functions.FAMILY_DELETE_GROUP
        if packet.type is Communicator.OperationPacket.Type.FAMILY_DELETE_PERMISSIONS:
            function_name = Cloud_Functions.FAMILY_DELETE_PERMISSIONS
        if packet.type is Communicator.OperationPacket.Type.FAMILY_DELETE_USER:
            function_name = Cloud_Functions.FAMILY_DELETE_USER
        if packet.type is Communicator.OperationPacket.Type.FAMILY_KILL_CHILDREN:
            function_name = Cloud_Functions.FAMILY_KILL_CHILDREN
        if packet.type is Communicator.OperationPacket.Type.FAMILY_SET_PARENT:
            function_name = Cloud_Functions.FAMILY_SET_PARENT
        
        if packet.type is Communicator.OperationPacket.Type.INACTIVE_SET_INACTIVE:
            function_name = Cloud_Functions.INACTIVE_SET_INACTIVE

        if packet.type is Communicator.OperationPacket.Type.MACHINE_CREATE_MACHINE:
            function_name = Cloud_Functions.MACHINE_CREATE_MACHINE
        if packet.type is Communicator.OperationPacket.Type.MACHINE_DELETE_MACHINE:
            function_name = Cloud_Functions.MACHINE_DELETE_MACHINE
        if packet.type is Communicator.OperationPacket.Type.MACHINE_REGISTER_SETTING:
            function_name = Cloud_Functions.MACHINE_REGISTER_SETTING
        if packet.type is Communicator.OperationPacket.Type.MACHINE_REGISTER_STATE:
            function_name = Cloud_Functions.MACHINE_REGISTER_STATE
        
        if packet.type is Communicator.OperationPacket.Type.USER_ADD_FAMILIES:
            function_name = Cloud_Functions.USER_ADD_FAMILIES
        if packet.type is Communicator.OperationPacket.Type.USER_CREATE_USER:
            function_name = Cloud_Functions.USER_CREATE_USER
        if packet.type is Communicator.OperationPacket.Type.USER_DELETE_FAMILIES:
            function_name = Cloud_Functions.USER_DELETE_FAMILIES
        if packet.type is Communicator.OperationPacket.Type.USER_DELETE_USER:
            function_name = Cloud_Functions.USER_DELETE_USER
        if packet.type is Communicator.OperationPacket.Type.USER_SET_EMAIL:
            function_name = Cloud_Functions.USER_SET_EMAIL
        if packet.type is Communicator.OperationPacket.Type.USER_SET_FNAME:
            function_name = Cloud_Functions.USER_SET_FNAME
        if packet.type is Communicator.OperationPacket.Type.USER_SET_LNAME:
            function_name = Cloud_Functions.USER_SET_LNAME

        # Set payload
        payload = packet.data

        # TODO: Handle event packet

        # Call the function in separate thread
        threading.Thread(target=call_function, args=(function_name, payload,)).start()
