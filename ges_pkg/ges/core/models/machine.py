
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
import dataclasses
import datetime
import string
import json
import simpy
import logging
import typing

from .. import util
from .. import communication
from .. import communicators

# Define logger
logger = logging.getLogger(__name__)


@dataclasses.dataclass
class Property:
    """Represents a generic property object.

    :param name: The property name.
    :param description: The property description.
    :param data: The property data.

    :type name: str
    :type description: str
    :type data: :class:`Property.Data`
    """
    @dataclasses.dataclass
    class Data:
        """Convenient class for storing cross-platform
        parsable data.

        :param type: The data type
        :param value: The value of the data

        :type type: :class:`Data.Type`
        :type value: typing.Any
        """
        class Type(str, Enum):
            """Defines various data types.
            """
            UNKNOWN = 'unknown'
            UINT8 = 'uint8'
            UINT16 = 'uint16'
            UINT32 = 'uint32'
            INT8 = 'int8'
            INT16 = 'int16'
            INT32 = 'int32'
            BOOLEAN = 'boolean'
            FLOAT = 'float'
            STRING = 'string'

        type: str = Type.UNKNOWN
        value: object = None

        ###############
        ## Utilities ##
        ###############

        def to_dict(self):
            """Return property data as dict.

            :return: The property data dictionary.
            :rtype: dict
            """
            return dataclasses.asdict(self)

    name: str
    description: str
    data: typing.List[dict]

    ###############
    ## Utilities ##
    ###############

    def to_dict(self):
        """Return property as dict.

        :return: The property dictionary.
        :rtype: dict
        """
        return dataclasses.asdict(self)


@dataclasses.dataclass
class Metadata:
    """Frozen dataclass used to store immutable
    device information created upon generation of
    Metadata instance.
    """
    codename: str = 'unknown'
    serial_number: str = 'unknown'
    programmed_on: str = 'unknown'
    mac_address: str = 'unknown'


class Machine(object):

    SERIAL_NUMBER_LENGTH = 16
    MAC_ADDRESS_LENGTH = 12

    # Define slots to override `__dict__` and restrict dynamic class modification
    __slots__ = ('_env', '_instance_name', '_metadata', '_settings', '_states', '_comm_tunnels')

    def __init__(self, env=None, comm_tunnels=None, codename='unknown', instance_name=None):
        # Validate environment
        if env is None:
            # TODO: needs rework - AB 03/12/2019
            raise RuntimeError("Invalid environment provided")
        else:
            self._env = env

        # Create communication tunnels list
        self._comm_tunnels = []

        # Define generic settings for all compliant devices
        self._settings = []

        # Define generic state for all compliant devices
        self._states = []

        # Generate default `metadata`
        self._metadata = Metadata(
            codename=codename,
            serial_number=self.generate_serial(),
            programmed_on=str(datetime.datetime.now()),
            mac_address=self.generate_mac_addr()
        )

        # Validate and save instance name
        if instance_name is not None:
            # Validate is string type
            if not isinstance(instance_name, str):
                raise RuntimeError("Invalid instance name type, must be str()")
            else:
                self._instance_name = instance_name
        else:
            # Set generic instance name from generated `mac_address`
            # TODO: move format out to configuration
            self._instance_name = 'machine-' + self._metadata.serial_number

        # Store tunnels
        if isinstance(comm_tunnels, list):
            for tnl in comm_tunnels:
                if isinstance(tnl, communication.Communicator):
                    self._comm_tunnels.append(tnl)

        # Add default heartbeat setting
        self.save_setting(
            Property(
                name='heartbeat_period',
                description='Device heartbeat period (in seconds)',
                data=Property.Data(
                    type=Property.Data.Type.UINT16,
                    value=360000
                )
            )
        )

        # Add default firmware version state
        self.save_state(
            Property(
                name='firmware_version',
                description='Device firmware version',
                data=Property.Data(
                    type=Property.Data.Type.STRING,
                    value='0.0.1'
                )
            )
        )

    ############################
    ## Simulation entry point ##
    ############################

    def main_process(self):
        """
        Should be overridden by implementation and accurately
        portray transient device operation.
        """
        # todo: implement custom exceptions
        raise Exception('run() must be overridden by subclass!')

    ###################
    ## Internal data ##
    ###################

    @property
    def metadata(self):
        """Returns all device metadata as dict"""
        return dataclasses.asdict(self._metadata)

    @property
    def settings(self):
        """Returns all device settings as dict"""
        return [dataclasses.asdict(setting) for setting in self._settings]

    def get_setting(self, name: str):
        """Searches for and returns the specified setting.

        If a setting cannot be located, a RuntimeError is
        raised.

        Args:
            name (str): Name of the setting to locate.

        Raises:
            RuntimeError: Raised if setting cannot be located

        Returns:
            Machine.Data: The dataclass with matching name
        """
        # Attempt to locate setting in this nasty loop
        for setting in self._settings:
            if setting.name == name:
                return setting

        # Can't find setting
        raise RuntimeError('Could not retrieve setting named "%s"' % name)

    def save_setting(self, setting: Property):
        """Saves provided setting.

        If setting with the given name already exists, it
        will be fully removed from the list and the new setting
        will be appended.

        Args:
            setting (Machine.Data): Setting data to save
        """
        # Remove setting if it already exists
        for _setting in self._settings:
            if _setting.name == setting.name:
                # Delete
                self._settings.remove(_setting)

        # Append setting
        self._settings.append(setting)

    @property
    def states(self):
        """Returns all device states as dict"""
        return [dataclasses.asdict(state) for state in self._states]

    def get_state(self, name: str):
        """Searches for and returns the specified state.

        If a state cannot be located, a RuntimeError is
        raised.

        Args:
            name (str): Name of the state to locate.

        Raises:
            RuntimeError: Raised if state cannot be located

        Returns:
            Machine.Data: The dataclass with matching name
        """
        # Attempt to locate state
        for _state in self._states:
            if _state.name == name:
                return _state

        # Can't find state
        raise RuntimeError('Could not retrieve state named "%s"' % name)

    def save_state(self, state: Property):
        """Saves provided state.

        If state with the given name already exists, it
        will be fully removed from the list and the new state
        will be appended.

        Args:
            state (Machine.Data): State data to save
        """
        # Attempt to locate and update state if it already exists
        for _state in self._states:
            if _state.name == state.name:
                # Delete
                self._states.remove(_state)

        # Append setting
        self._states.append(state)

    ###############
    ## Utilities ##
    ###############

    def sync_to_db(self):
        """Syncs local settings and states to the database.
        """
        logger.info('{}-{}: syncing to db...'.format(self._metadata.codename, self._metadata.serial_number))

        # Sync settings
        for setting in self._settings:
            data = dict(machine_id=self._metadata.serial_number, setting_name=setting.name, setting_data=dataclasses.asdict(setting.data))
            self.send_operation(type=communicators.wan.OperationType.MACHINE_UPDATE_SETTING, data=data)

        # Sync states
        for state in self._states:
            data = dict(machine_id=self._metadata.serial_number, state_name=state.name, state_data=dataclasses.asdict(state.data))
            self.send_operation(type=communicators.wan.OperationType.MACHINE_UPDATE_STATE, data=data)

        logger.info('{}-{}: synced!'.format(self._metadata.codename, self._metadata.serial_number))

    def to_dict(self):
        """Returns device data as dict object."""
        # Build device data
        output = {
            'metadata': dataclasses.asdict(self._metadata),
            'settings': [dataclasses.asdict(setting) for setting in self._settings],
            'states': [dataclasses.asdict(state) for state in self._states]
        }

        return output

    def to_json(self, indent=0):
        """Returns device data as JSON string.
        """
        return json.dumps(self.to_dict(), indent=indent, sort_keys=True)

    def generate_serial(self):
        """Should be overridden by implementation and be made
        to generate realistic serial numbers.
        """
        # Return a random string
        return util.generate.string(size=Machine.SERIAL_NUMBER_LENGTH)

    def generate_mac_addr(self):
        """Should be overridden by implementation and be made
        to generate realistic MAC addresses.
        """
        # Return a random string
        return util.generate.string(size=Machine.MAC_ADDRESS_LENGTH)

    def get_communicator_recv_pipe(self, type):
        """Returns a Communicator recieve pipe.

        Returns receive pipe of requested type, if it
        does not exist, raise exception.

        Arguments:
            type (Communicator subclass): Must be type of Communicator subclasses

        Raises:
            RuntimeError: pipe could not be created

        Returns:
            simpy.Store: recv pipe of requested communicator
                type
        """
        # Verify type
        if type not in [klass for klass in communication.Communicator.__subclasses__()]:
            raise RuntimeError('Unexpected type received')

        for tunnel in self._comm_tunnels:
            # Check that tunnel is requested type
            if isinstance(tunnel, type):
                return tunnel.get_output_pipe()

        raise RuntimeError('Communicator type (%s) not available' % type)

    ###################
    ## Communication ##
    ###################

    def send_event(self, type: communicators.wan.EventType, origin: str = 'self', extra_data: dict = None):
        # Prep data
        data = {
            "target": 'machine-{}'.format(str(self._metadata.serial_number)),
            "type": type.name,
            "origin": origin,
            "timestamp": str(datetime.datetime.now()),
            "data": extra_data
        }

        # Send operation
        self.send_operation(communicators.wan.OperationType.EVENTS_CREATE, data=data)

    def send_operation(self, type: communicators.wan.OperationType, data: dict):
        # Prep packet
        packet = communicators.wan.OperationPacket(
            # Packet()
            sender=self._instance_name,
            simulation_time=self._env.now,
            realworld_time=str(datetime.datetime.now()),

            # EventPacket()
            type=type,
            data=data
        )

        # Send
        self.transmit(communicators.wan.WAN, packet)

    def broadcast(self, message: communicators.rf.RadioPacket.Message):
        # Prep packet
        packet = communicators.rf.RadioPacket(
            # Packet()
            sender=self,
            simulation_time=self._env.now,
            realworld_time=str(datetime.datetime.now()),

            # RadioPacket()
            msg=message
        )

        # Send
        self.transmit(communicators.rf.RF, packet)

    def transmit(self, type, packet: communication.BasePacket):
        """Transmits provided packet to the communicator type given.

        Args:
            type (Communicator subclass): Must be type of Communicator subclasses
            packet (communication.BasePacket): Packet dataclass
                to send.

        Raises:
            RuntimeError: If unexpected type received
            RuntimeError: Communicator type not available to device
        """
        # Verify type
        if type not in [klass for klass in communication.Communicator.__subclasses__()]:
            raise RuntimeError('Unexpected type received')

        for tunnel in self._comm_tunnels:
            # Check that tunnel is requested type
            if isinstance(tunnel, type):
                # Send
                tunnel.send(packet)
                return True

        raise RuntimeError('Communicator type (%s) not available' % type)

