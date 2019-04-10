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

from ..communication import BasePacket
from ..communicators import wan

# Define logger
logger = logging.getLogger(__name__)

# TODO: Remove from VCS
ENDPOINT = "https://us-central1-guardian-ecoystem-simulator.cloudfunctions.net/{function_name}"


class Cloud_Functions(str, Enum):
    FAMILY_ADD_CHILDREN = 'family_add_children'
    FAMILY_ADD_PERMISSIONS = 'family_add_permissions'
    FAMILY_ADD_USER = 'family_add_user'
    FAMILY_CREATE = 'family_create'
    FAMILY_DELETE = 'family_delete'
    FAMILY_DELETE_PERMISSIONS = 'family_delete_permissions'
    FAMILY_REMOVE_CHILD = 'family_remove_child'
    FAMILY_REMOVE_USER = 'family_remove_user'
    FAMILY_SET_PARENT = 'family_set_parent'

    INACTIVE_SET_INACTIVE = 'inactive_set_inactive'

    MACHINE_CREATE = 'machine_create'
    MACHINE_DELETE = 'machine_delete'
    MACHINE_REGISTER_SETTING = 'machine_register_setting'
    MACHINE_REGISTER_STATE = 'machine_register_state'
    MACHINE_UPDATE_SETTING = 'machine_update_setting'
    MACHINE_UPDATE_STATE = 'machine_update_state'

    USER_CREATE = 'user_create'
    USER_DELETE = 'user_delete'
    USER_SET_EMAIL = 'user_set_email'
    USER_SET_FNAME = 'user_set_fname' # Set user first name
    USER_SET_LNAME = 'user_set_lname' # Set user last name

    EVENTS_CREATE = 'events_create'

def call_function(name: str, data: dict):
    try:
        logger.debug('Calling {} with data: {}'.format(name, json.dumps(data)))
        r = requests.post(url=ENDPOINT.format(function_name=name), data=json.dumps(data), headers={'Content-type': 'application/json'})
    except Exception as e: # TODO: Handle specific exceptions
        logger.warn('Could not call {} (error: {})'.format(name, str(e)))
    else:
        ret = json.loads(r.content)
        status = ret['status']

        if status == 'ok':
            logger.debug('{}({}) -> succeeded at {}'.format(name, ret['data']['updated'],  ret['data']['timestamp']))
        else:
            logger.error('{} failed, response: {}'.format(name, str(r.content.decode())))

def process(packet: BasePacket):
    """Parse raw message and call relevant cloud function.
    """
    logger.debug("Processing packet")

    # Default values
    function_name = ''
    payload = {}

    # Set function depending on type of operation
    if isinstance(packet, wan.OperationPacket):
        ################
        ## Operations ##
        ################

        # Family
        if packet.type is wan.OperationType.FAMILY_ADD_CHILDREN:
            function_name = Cloud_Functions.FAMILY_ADD_CHILDREN.value
        if packet.type is wan.OperationType.FAMILY_ADD_GROUPS:
            function_name = Cloud_Functions.FAMILY_ADD_GROUPS.value
        if packet.type is wan.OperationType.FAMILY_ADD_PERMISSIONS:
            function_name = Cloud_Functions.FAMILY_ADD_PERMISSIONS.value
        if packet.type is wan.OperationType.FAMILY_ADD_USER:
            function_name = Cloud_Functions.FAMILY_ADD_USER.value
        if packet.type is wan.OperationType.FAMILY_CREATE:
            function_name = Cloud_Functions.FAMILY_CREATE.value
        if packet.type is wan.OperationType.FAMILY_REMOVE_GROUP:
            function_name = Cloud_Functions.FAMILY_REMOVE_GROUP.value
        if packet.type is wan.OperationType.FAMILY_DELETE_PERMISSIONS:
            function_name = Cloud_Functions.FAMILY_DELETE_PERMISSIONS.value
        if packet.type is wan.OperationType.FAMILY_REMOVE_USER:
            function_name = Cloud_Functions.FAMILY_REMOVE_USER.value
        if packet.type is wan.OperationType.FAMILY_REMOVE_CHILD:
            function_name = Cloud_Functions.FAMILY_REMOVE_CHILD.value
        if packet.type is wan.OperationType.FAMILY_SET_PARENT:
            function_name = Cloud_Functions.FAMILY_SET_PARENT.value

        # Inactive
        if packet.type is wan.OperationType.INACTIVE_SET_INACTIVE:
            function_name = Cloud_Functions.INACTIVE_SET_INACTIVE.value

        # Machine
        if packet.type is wan.OperationType.MACHINE_CREATE:
            function_name = Cloud_Functions.MACHINE_CREATE.value
        if packet.type is wan.OperationType.MACHINE_DELETE:
            function_name = Cloud_Functions.MACHINE_DELETE.value

        if packet.type is wan.OperationType.MACHINE_REGISTER_SETTING:
            function_name = Cloud_Functions.MACHINE_REGISTER_SETTING.value
        if packet.type is wan.OperationType.MACHINE_UPDATE_SETTING:
            function_name = Cloud_Functions.MACHINE_UPDATE_SETTING.value

        if packet.type is wan.OperationType.MACHINE_REGISTER_STATE:
            function_name = Cloud_Functions.MACHINE_REGISTER_STATE.value
        if packet.type is wan.OperationType.MACHINE_UPDATE_STATE:
            function_name = Cloud_Functions.MACHINE_UPDATE_STATE.value

        # User
        if packet.type is wan.OperationType.USER_CREATE:
            function_name = Cloud_Functions.USER_CREATE.value
        if packet.type is wan.OperationType.USER_DELETE:
            function_name = Cloud_Functions.USER_DELETE.value
        if packet.type is wan.OperationType.USER_SET_EMAIL:
            function_name = Cloud_Functions.USER_SET_EMAIL.value
        if packet.type is wan.OperationType.USER_SET_FNAME:
            function_name = Cloud_Functions.USER_SET_FNAME.value
        if packet.type is wan.OperationType.USER_SET_LNAME:
            function_name = Cloud_Functions.USER_SET_LNAME.value

        # Events
        if packet.type is wan.OperationType.EVENTS_CREATE:
            function_name = Cloud_Functions.EVENTS_CREATE.value
    else:
        logger.warn("Error processing packet, dropped")
        return

    # Set payload
    payload = packet.data

    # Call the function in separate thread
    threading.Thread(target=call_function, args=(function_name, payload,)).start()

    logger.debug("Packet processed")
