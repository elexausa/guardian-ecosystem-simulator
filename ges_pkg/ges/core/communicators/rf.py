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

import dataclasses
import datetime
import string
import json
import simpy
import logging
import typing
from enum import Enum, IntEnum, auto

from ..communication import Communicator, BasePacket

# Define logger
logger = logging.getLogger(__name__)

##################
## Packet types ##
##################

@dataclasses.dataclass
class RadioPacket(BasePacket):

    class Message(IntEnum):
        HEARTBEAT = auto()
        MOVED = auto()
        WET = auto()
        DRY = auto()

    msg: Message

##################
## Communicator ##
##################

class RF(Communicator):
    """Simulated RF network.

    Inherits from communicator base type.
    """

    def __init__(self, env):
        super().__init__(env)

    def send(self, packet: BasePacket):
        """Passes packet to super().send_raw().

        More functionality can be added here to create a more
        intricate communicator.

        Args:
            packet (BasePacket): Requires Packet dataclass
        """
        # Pass to super for sending to communicator pipes
        self.send_raw(packet)