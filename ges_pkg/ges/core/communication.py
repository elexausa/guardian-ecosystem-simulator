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

import typing
import dataclasses
import datetime
import string
import json
import simpy
import logging
from enum import IntEnum

# Define logger
logger = logging.getLogger(__name__)


@dataclasses.dataclass
class BasePacket:
    """Generic communicator packet.

    Requires sender, simulation time, realworld
    time, and the data to send.
    """
    sender: str
    simulation_time: int
    realworld_time: str


class Communicator:
    """Enables a process to perform many-to-many communication
    with other simulation processes.

    Based on `Process communication example` by Keith Smith
    in SimPy user manual 3.0.11.
    """

    __slots__ = ('_env', '_capacity', '_pipes')

    def __init__(self, env: simpy.core.BaseEnvironment, capacity=simpy.core.Infinity):
        # Set environment
        self._env = env

        # Store pipe configuration
        self._capacity = capacity

        # Create list to store pipes
        self._pipes = []

    def send_raw(self, packet: str):
        """Send raw packet to all attached pipes.

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
            raise RuntimeError('No output pipes configured, packet dropped')

        logger.debug("Sending packet to %d output pipes: %s" % (len(self._pipes), packet))

        # Store events created by putting data in `simpy.Store`
        events = [pipe.put(packet) for pipe in self._pipes]

        # Return simpy
        return self._env.all_of(events)

    def get_output_pipe(self):
        """Generate a new output pipe (`simpy.resources.store.Store`).

        Other processes can use the returned pipe to receive messages
        from the `CommunicatorPipe` instance.

        Returns:
            simpy.resources.store.Store: New store instance
        """
        pipe = simpy.Store(self._env, capacity=self._capacity)
        self._pipes.append(pipe)
        return pipe
