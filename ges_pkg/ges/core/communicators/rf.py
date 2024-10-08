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

from ..communication import Communicator

# Define logger
logger = logging.getLogger(__name__)


class RF(Communicator):
    """Simulated RF network.

    Inherits from communicator base type.
    """

    def __init__(self, env):
        super().__init__(env)

    def send(self, packet: Communicator.Packet):
        """Passes packet to super().send_raw().

        More functionality can be added here to create a more
        intricate communicator.

        Args:
            packet (Communicator.Packet): Requires Packet dataclass
        """
        # Pass to super for sending to communicator pipes
        self.send_raw(packet)