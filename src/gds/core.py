
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
from collections import namedtuple
from frozendict import frozendict
import datetime
import string
import json
import simpy
import logging

from gds import util

logger = logging.getLogger(__name__)

ENV = simpy.rt.RealtimeEnvironment()

class CommunicationTunnel(object):
    """Enables a process to perform many-to-many communication
    with other simulation processes.

    Based on `Process communication example` by Keith Smith
    in SimPy user manual 3.0.11.
    """

    class Type(Enum):
        """Enumeration defining different communication pipe types.
        """
        RF = 0
        TCPIP = 1
        BLUETOOTH_CLASSIC = 2
        BLUETOOTH_LE = 3

    def __init__(self, capacity=simpy.core.Infinity, type=Type.RF):
        # Store pipe configuration
        # self._env = env
        self._capacity = capacity
        self._type = type

        # Create list to store pipes
        self._pipes = []

    @staticmethod
    def create(type=Type.RF):
        """Tunnel factory.

        Create tunnel of given type.

        Arguments:
            env (simpy.Environment, required): The simpy environment to
                attach communication tunnel.
            type (core.CommunicationTunnel.Type, optional): Defaults to 
                Type.RF. The desired tunnel to create.
        """
        return CommunicationTunnel(capacity=simpy.core.Infinity, type=type)

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
        from the `CommunicationPipe` instance.

        Returns:
            simpy.resources.store.Store: New store instance
        """
        pipe = simpy.Store(ENV, capacity=self._capacity)
        self._pipes.append(pipe)
        return pipe


class Device(object):
    ## Probably temporary ####
    SERIAL_NUMBER_LENGTH = 16
    MAC_ADDRESS_LENGTH = 12
    ##########################

    # class CapabilityType(Enum):
    #     class Networking(Enum):
    #         RF_915MHZ = namedtuple('RF_915MHZ', [
    #             'rf_tx_func',
    #             'rf_rx_pipe'
    #         ])

    COMM_TUNNEL_915 = CommunicationTunnel.create(CommunicationTunnel.Type.RF)

    # Define slots to override `__dict__` and restrict dynamic class modification
    __slots__ = ('_metadata', '_settings', '_state', '_instance_name', '_rf_tx_func', '_rf_rx_pipe')

    def __init__(self, codename='generic', instance_name=None):
        # Store simulation environment
        # self._env = env

        # Generate generic `metadata` as frozendict; cannot be modified
        self._metadata = frozendict({
            'codename': str(codename),
            'serial_number': self.generate_serial(),
            'manufactured_at': str(datetime.datetime.now()),
            'mac_address': self.generate_mac_addr()
        })
    
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
            self._instance_name = 'Device-' + self._metadata['mac_address'][-4:]

        # Create internal capabilities list
        # self.__capabilities = []

        # Validate and store capabilities
        # if capabilities is not None:
        #     # TODO: enforce input
        #     for capability in capabilities:
        #         if capability is Device.CapabilityType.Networking.RF_915MHZ:
        #             # Validate provided data types
        #             # TODO: move these out to be processed automatically by each `CapabilityType`
        #             if not callable(capability.rf_tx_func):
        #                 raise RuntimeError("No or improper rf_tx_func provided")
        #             elif not isinstance(capability.rf_rx_pipe, simpy.Store):
        #                raise RuntimeError("No or improper rf_rx_pipe provided")
        #             else:
        #                 # All good, store capability
        #                 self.__capabilities.append(capability)

        # Define generic settings for all compliant devices
        self._settings = {}
        self._settings['heartbeat_period_s'] = {
            '_type': 'uint16',
            '_value': 360000,
            '_description': 'Device heartbeat period (in seconds)'
        }

        # Define generic state for all compliant devices
        self._state = {}
        self._state['firmware_version'] = {
            '_type': 'string',
            '_value': '0.0.1',
            '_description': 'Device firmware version'
        }

    @classmethod
    def from_json(cls, filepath: str):
        """Instantiates `Device` instance from JSON file."""
        pass

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
            # 'metadata': self._metadata.,
            'settings': self._settings,
            'state': self._state,
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

