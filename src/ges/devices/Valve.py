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

from .. import util
from .. import core

logger = logging.getLogger(__name__)


class Valve(core.Device):
    # Disable object `__dict__`
    __slots__ = ('_main_process', '_leak_detect_process', '_rf_rx_pipe')

    LEAK_DETECT_TIMEFRAME_MIN = 1
    LEAK_DETECT_TIMEFRAME_MAX = 1*60*60*24*30 # 30 days

    def __init__(self, instance_name=None):
        super().__init__(codename='tiddymun', instance_name=instance_name)

        # Create RF 915MHz input pipe by grabbing from 915 tunnel
        self._rf_rx_pipe = core.Device.COMM_TUNNEL_915.get_output_pipe()

        # Configure settings
        self.set_setting(name='close_delay_s', type=core.Device.DataType.UINT16, value=5, description='Amount of time to wait (in seconds) before closing valve')
        self.set_setting(name='location_gps_lat', type=core.Device.DataType.FLOAT, value=5, description='Latitudinal GPS coordinate')
        self.set_setting(name='location_gps_lon', type=core.Device.DataType.FLOAT, value=5, description='Longitudinal GPS coordinate')

        # Initialize state
        self.set_state(name='valve', type=core.Device.DataType.STRING, value='opened', description='State of valve as opened/closed/stuck')
        self.set_state(name='motor', type=core.Device.DataType.STRING, value='resting', description='State of motor as opening/closing/resting')
        self.set_state(name='motor_current', type=core.Device.DataType.FLOAT, value=0.0, description='Current draw of motor (in Amps)')
        self.set_state(name='firmware_version', type=core.Device.DataType.STRING, value='4.0.0', description='Valve controller firmware version')
        self.set_state(name='probe1_wet', type=core.Device.DataType.BOOLEAN, value=False, description='True if water detected at probe1')

        # Spawn self processes
        self._main_process = core.ENV.process(self.run())
        self._leak_detect_process = core.ENV.process(self.detect_leak())

    def generate_mac_addr(self):
        return "30AEA402" + util.string_generator(size=4)

    def run(self):
        """Simulates device transient operation.

        During normal operation the device can be interrupted
        by other simulation events.
        """
        while True:
            try:
                # Get event for message pipe
                packet = yield self._rf_rx_pipe.get()

                if packet[0] < core.ENV.now:
                    # if message was already put into pipe, then
                    # message_consumer was late getting to it. Depending on what
                    # is being modeled this, may, or may not have some
                    # significance
                    logger.info('%s - received packet LATE - current time %d' % (self._instance_name, core.ENV.now))
                    # logger.info(json.dumps(json.loads(packet[1])))
                else:
                    # message_consumer is synchronized with message_generator
                    logger.info('%s - received packet - current time %d - data (after NL)\n%s' % (self._instance_name, core.ENV.now, json.dumps(json.loads(packet[1]), indent=4, sort_keys=True)))

                # "Turn off the valve", 5-10 seconds
                #yield core.ENV.timeout(random.randint(1, 3))
            except simpy.Interrupt:
                pass

    def detect_leak(self):
        """Occasionally triggers a leak."""
        while True:
            # yield self._env.timeout(random.expovariate(self.MEAN_LEAK_DETECTION_TIME))
            yield core.ENV.timeout(random.randint(60, 120))
            logger.warning(self._instance_name + ' LEAK DETECTED!')


class DyingCow(core.Device):
    # Disable object `__dict__`
    __slots__ = ('_process')

    def __init__(self, instance_name=None):
        super().__init__(codename='mooofasa', instance_name=instance_name)

        # Start simulation process
        self._process = core.ENV.process(self.run())

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
            yield core.ENV.timeout(random.randint(1,1*60*60))

            # mooooooOOOooOOoOOOooOOoOOoOoo!!!
            logger.info('moooooOOOOoOOOooOOoooOOOOooooo!!')

            packet = {
                'moo_time': core.ENV.now,
                'who_mooed': self._instance_name,
                'content': 'mooooooooooOOOOOOOOOOOooOoOooOoooOOooo',
                'ear_tag': self._metadata['serial_number'],
                'birthday': self._metadata['manufactured_at']
            }

            msg = (core.ENV.now, json.dumps(packet, indent=4, sort_keys=True))

            core.Device.COMM_TUNNEL_915.send(msg)
