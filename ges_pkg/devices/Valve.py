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
from core import util

logger = logging.getLogger(__name__)


class Valve(core.Device):
    # Disable object `__dict__`
    __slots__ = ('_main_process', '_leak_detect_process', '_rf_rx_pipe')

    LEAK_DETECT_TIMEFRAME_MIN = 1
    LEAK_DETECT_TIMEFRAME_MAX = 1*60*60*24*30 # 30 days

    def __init__(self, instance_name=None):
        super().__init__(codename='tiddymun', instance_name=instance_name)

        # Create RF 915MHz input pipe by grabbing from 915 tunnel
        self._rf_rx_pipe =core.Device.COMM_TUNNEL_915.get_output_pipe()

        # Configure settings
        self.save_setting(
           core.Device.Data(
                name='close_delay_s',
                type=core.Device.Data.Type.UINT16,
                value=5,
                description='Amount of time to wait (in seconds) before closing valve'
            )
        )
        self.save_setting(
           core.Device.Data(
                name='location_gps_lat',
                type=core.Device.Data.Type.FLOAT,
                value=5,
                description='Latitudinal GPS coordinate'
            )
        )
        self.save_setting(
           core.Device.Data(
                name='location_gps_lon',
                type=core.Device.Data.Type.FLOAT,
                value=5,
                description='Longitudinal GPS coordinate'
            )
        )

        # Initialize state
        self.save_state(
           core.Device.Data(
                name='valve',
                type=core.Device.Data.Type.STRING,
                value='opened',
                description=''
            )
        )
        self.save_state(
           core.Device.Data(
                name='motor',
                type=core.Device.Data.Type.STRING,
                value='resting',
                description='State of motor as opening/closing/resting'
            )
        )
        self.save_state(
           core.Device.Data(
                name='motor_current',
                type=core.Device.Data.Type.FLOAT,
                value=0.0,
                description='Current draw of motor (in Amps)'
            )
        )
        self.save_state(
           core.Device.Data(
                name='firmware_version',
                type=core.Device.Data.Type.STRING,
                value='4.0.0',
                description='Valve controller firmware version'
            )
        )
        self.save_state(
           core.Device.Data(
                name='probe1_wet',
                type=core.Device.Data.Type.BOOLEAN,
                value=False,
                description='True if water detected at probe1'
            )
        )
        self.save_state(
           core.Device.Data(
                name='valve',
                type=core.Device.Data.Type.STRING,
                value='opened',
                description='State of valve as opened/closed/stuck'
            )
        )

        # # Spawn self processes
        self._main_process = core.ENV.process(self.run())
        self._leak_detect_process = core.ENV.process(self.detect_leak())

    def generate_mac_addr(self):
        return "30AEA402" + util.generate.string(size=4)

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


