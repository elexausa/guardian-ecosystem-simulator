
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
from recordclass import recordclass
from frozendict import frozendict
import dataclasses
import datetime
import string
import json
import simpy
import logging

from ges import util

# Define logger
logger = logging.getLogger(__name__)

# Define environment
ENV = simpy.rt.RealtimeEnvironment()

class Communicator(object):
    """Enables a process to perform many-to-many communication
    with other simulation processes.

    Based on `Process communication example` by Keith Smith
    in SimPy user manual 3.0.11.
    """

    class Type(Enum):
        """Enumeration defining different Communicator pipe types.
        """
        RF = 0
        TCPIP = 1
        BLUETOOTH_CLASSIC = 2
        BLUETOOTH_LE = 3

    @dataclasses.dataclass
    class RF_Packet:
        mac_address: str = 'unknown'
        battery: float = 0.0
        temperature: float = 0.0
        top: bool = False
        bottom: bool = False
        tilt: bool = False


    def __init__(self, capacity=simpy.core.Infinity, type=Type.RF):
        # Store pipe configuration
        # self._env = env
        self._capacity = capacity
        self._type = type

        # Create list to store pipes
        self._pipes = []

    @staticmethod
    def create_tunnel(type=Type.RF):
        """Tunnel factory.

        Create tunnel of given type.

        Arguments:
            env (simpy.Environment, required): The simpy environment to
                attach communication tunnel.
            type (Communicator.Type, optional): Defaults to
                Type.RF. The desired tunnel to create.
        """
        return Communicator(capacity=simpy.core.Infinity, type=type)

    def send(self, packet):
        """Send packet to all attached pipes.

        Args:
            packet (any): The data to send

        Raises:
            RuntimeError: No output pipes have been configured.

        Returns:
            simpy.events.AllOf: Returns an event instance that is
                triggered once all held events complete successfully.
        """
        # Pipes populated?
        if not self._pipes:
            logger.debug('No output pipes configured, packet dropped')
            raise RuntimeError('No output pipes configured')

        logger.debug("Sending packet to %d output pipes: %s" %
                    (len(self._pipes), packet))

        # Store events created by putting data in `simpy.Store`
        events = [pipe.put(packet) for pipe in self._pipes]

        # Return simpy
        return ENV.all_of(events)

    def get_output_pipe(self):
        """Generate a new output pipe (`simpy.resources.store.Store`).

        Other processes can use the returned pipe to receive messages
        from the `CommunicatorPipe` instance.

        Returns:
            simpy.resources.store.Store: New store instance
        """
        pipe = simpy.Store(ENV, capacity=self._capacity)
        self._pipes.append(pipe)
        return pipe



class Device(object):

    SERIAL_NUMBER_LENGTH = 16
    MAC_ADDRESS_LENGTH = 12

    COMM_TUNNEL_915 = Communicator.create_tunnel(Communicator.Type.RF)

    @dataclasses.dataclass
    class Data:
        """Convenient dataclass for storing cross-platform
        parsable data for device instance.
        """

        class Type(str, Enum):
            """Defines various possible data types.
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

        name: str = 'Data name'
        type: Type = Type.UNKNOWN
        value: object = None
        description: str = 'Data description'


    @dataclasses.dataclass
    class Metadata:
        """Frozen dataclass used to store immutable
        device information created upon generation of
        Metadata instance.
        """
        codename: str = 'unknown'
        serial_number: str = 'unknown'
        manufactured_at: str = 'unknown'
        mac_address: str = 'unknown'

    # Define slots to override `__dict__` and restrict dynamic class modification
    __slots__ = ('_instance_name', '_metadata', '_settings', '_states')

    def __init__(self, codename='unknown', instance_name=None):
        # Generate generic `metadata`
        self._metadata = Device.Metadata(
            codename=codename,
            serial_number=self.generate_serial(),
            manufactured_at=str(datetime.datetime.now()),
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
            self._instance_name = 'Device-' + self._metadata.mac_address[-4:]

        # Define generic settings for all compliant devices
        self._settings = []

        self.save_setting(
            Device.Data(
                name='heartbeat_period',
                type=Device.Data.Type.UINT16,
                value=360000,
                description='Device heartbeat period (in seconds)'
            )
        )

        # Define generic state for all compliant devices
        self._states = []

        self.save_state(
            Device.Data(
                name='firmware_version',
                type=Device.Data.Type.STRING,
                value='0.0.1',
                description='Device firmware version'
            )
        )

    @property
    def metadata(self):
        """Returns all device metadata"""
        return self._metadata

    @property
    def settings(self):
        """Returns all device settings"""
        return self._settings

    @property
    def states(self):
        """Returns all device states"""
        return self._states

    def get_setting(self, name: str):
        """Searches for and returns the specified setting.

        If a setting cannot be located, a RuntimeError is
        raised.

        Args:
            name (str): Name of the setting to locate.

        Raises:
            RuntimeError: Raised if setting cannot be located

        Returns:
            Device.Data: The dataclass with matching name
        """
        # Attempt to locate setting in this nasty loop
        for setting in self._settings:
            if setting.name == name:
                return setting

        # Can't find setting
        raise RuntimeError('Could not retrieve setting named "%s"' % name)

    def save_setting(self, setting: Data):
        """Saves provided setting.

        If setting with the given name already exists, it
        will be fully removed from the list and the new setting
        will be appended.

        Args:
            setting (Device.Data): Setting data to save
        """
        # Remove setting if it already exists
        for _setting in self._settings:
            if _setting.name == setting.name:
                # Delete
                self._settings.remove(_setting)

        # Append setting
        self._settings.append(setting)

    def get_state(self, name: str):
        """Searches for and returns the specified state.

        If a state cannot be located, a RuntimeError is
        raised.

        Args:
            name (str): Name of the state to locate.

        Raises:
            RuntimeError: Raised if state cannot be located

        Returns:
            Device.Data: The dataclass with matching name
        """
        # Attempt to locate state
        for _state in self._states:
            if _state.name == name:
                return _state

        # Can't find state
        raise RuntimeError('Could not retrieve state named "%s"' % name)

    def save_state(self, state: Data):
        """Saves provided state.

        If state with the given name already exists, it
        will be fully removed from the list and the new state
        will be appended.

        Args:
            state (Device.Data): State data to save
        """
        # Attempt to locate and update state if it already exists
        for _state in self._states:
            if _state.name == state.name:
                # Delete
                self._states.remove(_state)

        # Append setting
        self._states.append(state)

    def run(self):
        """
        Should be overridden by implementation and accurately
        portray transient device operation.
        """
        # todo: implement custom exceptions
        raise Exception('run() must be overridden by subclass!')

    def dump_json(self):
        """Returns device data as JSON object."""
        # Build device data
        output = {
            'metadata': dataclasses.asdict(self._metadata),
            'settings': [dataclasses.asdict(setting) for setting in self._settings],
            'state': [dataclasses.asdict(state) for state in self._states]
        }

        return json.dumps(output, indent=4, sort_keys=True)

    def generate_serial(self):
        """
        Should be overridden by implementation and be made
        to generate realistic serial numbers.
        """
        # Return a random string
        return util.string_generator(size=Device.SERIAL_NUMBER_LENGTH)

    def generate_mac_addr(self):
        """
        Should be overridden by implementation and be made
        to generate realistic MAC addresses.
        """
        # Return a random string
        return util.string_generator(size=Device.MAC_ADDRESS_LENGTH)

