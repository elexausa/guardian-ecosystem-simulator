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

import core

logger = logging.getLogger(__name__)

class Dying_Cow(core.Device):
    # Disable object `__dict__`
    __slots__ = ('_process')

    def __init__(self, env=None, instance_name=None):
        super().__init__(env=env, codename='mooofasa', instance_name=instance_name)

        # Start simulation process
        self._process = self._env.process(self.run())

    @staticmethod
    def spawn(instance_name=None):
        """Dying cow factory.

            instance_name (str, optional): Defaults to None which triggers
                automatic naming by Device superclass. Provide unique

        Returns:
            DyingCow: new DyingCow instance
        """

        return DyingCow(instance_name=instance_name)

    def run(self):
        """Simulates dying cow mooing at 915 MHz.
        """
        while True:
            # Every 1 sec to 1 hour there's a moo, it's a slow death
            yield self._env.timeout(random.randint(1,1*60*60))

            # mooooooOOOooOOoOOOooOOoOOoOoo!!!
            logger.info('moooooOOOOoOOOooOOoooOOOOooooo!!')

            packet = {
                'moo_time': self._env.now,
                'who_mooed': self._instance_name,
                'content': 'mooooooooooOOOOOOOOOOOooOoOooOoooOOooo',
                'ear_tag': self._metadata['serial_number'],
                'birthday': self._metadata['manufactured_at']
            }

            msg = (self._env.now, json.dumps(packet, indent=4, sort_keys=True))

            core.Device.COMM_TUNNEL_915.send(msg)
