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

import random
import simpy
import logging
import json
import datetime

from ..core import communication
from ..core import communicators
from ..core import model
from ..core.util import const

logger = logging.getLogger(__name__)


class Cow(model.Device):
    # Disable object `__dict__`
    __slots__ = ('_process')

    def __init__(self, env=None, comm_tunnels=None, instance_name=None):
        super().__init__(env=env, comm_tunnels=comm_tunnels, codename='moofasa', instance_name=instance_name)

        ###############################
        ## Configure device settings ##
        ###############################

        # Heartbeat period
        self.save_setting(
           model.Device.Data(
                name='heartbeat_period',
                type=model.Device.Data.Type.UINT16,
                value=300, # 5 minutes
                description='Device heartbeat period (in seconds)'
            )
        )

        # Start simulation process
        self._process = self._env.process(self.run())

    def run(self):
        """Simulates dying cow mooing at 915 MHz.
        """

        # On fresh call of `run()`, cow wakes up from a nice rest
        isAwake = False

        # Enter infinite loop for simulation
        while True:
            # Starting from rest
            if not isAwake:
                # Now awake
                isAwake = True

                logger.info("*pokes cow*")

                # 1-5 seconds to get the mind working
                yield self._env.timeout(random.randint(1,20))

                # Success
                logger.info("%s woke up! \"MooooOOO!\" says the cow", self._instance_name)
            else:
                # Wait for heartbeat to report info
                yield self._env.timeout(self.get_setting('heartbeat_period').value)

                diagnostics = {
                    'hunger': random.randint(0, 100),
                    'happiness': random.randint(90, 100) # happy cows are best
                }

                # Prep packet
                packet = communication.Communicator.Packet(
                    sent_at=self._env.now,
                    created_at=str(datetime.datetime.now()),
                    sent_by=self._metadata.mac_address,
                    sent_to=self._metadata.mac_address,
                    data=diagnostics
                )

                # Send
                self.transmit(communicators.rf.RF, packet)


class Calf(model.Device):
    # Disable object `__dict__`
    __slots__ = ('_process')

    def __init__(self, env=None, comm_tunnels=None, instance_name=None):
        super().__init__(env=env, comm_tunnels=comm_tunnels, codename='moofussa', instance_name=instance_name)

        ###############################
        ## Configure device settings ##
        ###############################

        # Heartbeat period
        self.save_setting(
           model.Device.Data(
                name='heartbeat_period',
                type=model.Device.Data.Type.UINT16,
                value=60,
                description='Device heartbeat period (in seconds)'
            )
        )

        # Start simulation process
        self._process = self._env.process(self.run())
        # self._hunger_process = self._env.process(self.update_hunger())

    def run(self):
        """Simulates lil cow.
        """
        # On fresh call of `run()`, cow wakes up from a nice rest
        isAwake = False

        # Enter infinite loop for simulation
        while True:
            # Starting from rest
            if not isAwake:
                # Now awake
                isAwake = True

                # Wait for stable legs
                yield self._env.timeout(random.randint(15,60))

                logger.info("Little %s says \"mooooommy im hungry\"", self._instance_name)
            else:
                # Wait for heartbeat to report info
                # yield self._env.timeout(self.get_setting('heartbeat_period').value)
                yield self._env.timeout(random.randint(1,500))

                # Prep packet
                packet = communication.Communicator.Packet(
                    sent_at=self._env.now,
                    created_at=str(datetime.datetime.now()),
                    sent_by=self._metadata.mac_address,
                    sent_to='broadcast',
                    data='*slurps milk*'
                )

                logger.info("*slurp slurp* - %s", self._instance_name)

                # Send
                self.transmit(communicators.rf.RF, packet)

    def update_hunger(self):
        pass