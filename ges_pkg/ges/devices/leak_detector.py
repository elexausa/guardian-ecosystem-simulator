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
import math
import datetime

from ..core import communication
from ..core import model
from ..core import communicators

logger = logging.getLogger(__name__)


class Leak_Detector(model.Device):
    """ Simulates a leak detector
    
    Attributes:
        LEAK_DETECT_TIMEFRAME_MIN (int): Minimum amount of time (in simulation seconds) before a leak is detected.
        LEAK_DETECT_TIMEFRAME_MAX (int): Maximum amount of time (in simulation seconds) before a leak is detected.
        INITIAL_TEMPERATURE (double): The initial reading of internal temperature (in fahrenheit).
        TEMPERATURE_STANDARD_DEVIATION (int): How far the temperature can stray from attribute INITIAL_TEMPERATURE.
        INITIAL_BATTERY_VOLTAGE (int): The initial battery voltage (in millivolts).
        HEARTBEAT_PERIOD (int): Time (in simulation seconds) before a heartbeat packet is sent out.
    """

    # Disable object `__dict__`
    __slots__ = ('_process', '_leak_detect_process')

    LEAK_DETECT_TIMEFRAME_MIN = 1
    LEAK_DETECT_TIMEFRAME_MAX = 5
    # LEAK_DETECT_TIMEFRAME_MAX = 1*60*60*24 # 24 hours
    INITIAL_TEMPERATURE = 73.0 # Fahrenheit
    TEMPERATURE_STANDARD_DEVIATION = 2 # +/- 2 degrees
    INITIAL_BATTERY_VOLTAGE = 3600 # millivolts
    HEARTBEAT_PERIOD = 1*60*60*12 # 12 hours -> seconds

    def __init__(self, env=None, comm_tunnels=None, instance_name=None):
        super().__init__(env=env, comm_tunnels=comm_tunnels, codename='ahurani', instance_name=instance_name)

        ###############################
        ## Configure device settings ##
        ###############################

        # Heartbeat period
        self.save_setting(
           model.Device.Data(
                name='heartbeat_period',
                type=model.Device.Data.Type.UINT16,
                value=Leak_Detector.HEARTBEAT_PERIOD,
                description='Device heartbeat period (in seconds)'
            )
        )

        ########################
        ## Setup device state ##
        ########################

        # Battery state
        self.save_state(
            model.Device.Data(
                name='battery_voltage',
                type=model.Device.Data.Type.UINT16,
                value=Leak_Detector.INITIAL_BATTERY_VOLTAGE,
                description='Battery voltage (in millivolts)'
            )
        )

        # Temperature state
        self.save_state(
            model.Device.Data(
                name='temperature',
                type=model.Device.Data.Type.FLOAT,
                value=Leak_Detector.INITIAL_TEMPERATURE,
                description='Ambient air temperature near the device (in Fahrenheit)'
            )
        )

        # Spawn simulation processes
        self._process = self._env.process(self.run())
        self._leak_detect_process = self._env.process(self.detect_leaks())

    @staticmethod
    def manufacture(instance_name=None):
        """Creates and returns new Leak_Detector instance.

            instance_name (str, optional): Defaults to None. Instance
                name for simulation state tracking.

        Returns:
            Leak_Detector: New leak detector device instance
        """
        return Leak_Detector(instance_name=instance_name)

    def run(self):
        """Simulates Leak Detector operation.
        """

        # On fresh call of `run()`, device starts up from unpowered state
        isPowered = False

        # Enter infinite loop for simulation
        while True:
            # Starting from unpowered
            if not isPowered:
                # Update temperature
                self.update_temperature()
                self.update_battery()

                # Now powered
                isPowered = True

                logger.info("POWERED ON")
            else:
                # Wait for heartbeat to report info
                yield self._env.timeout(self.get_setting('heartbeat_period').value)

                # It's this lil device's time to shine!
                packet = communication.Communicator.Packet(
                    sent_at=self._env.now,
                    created_at=str(datetime.datetime.now()),
                    sent_by=self._metadata.mac_address,
                    sent_to=self._metadata.mac_address,
                    data='ping'
                )

                # Send
                self.transmit(communicators.rf.RF, packet)

    def detect_leaks(self):
        """Generates LEAK DETECTION messages.

        Message is created every LEAK_DETECTION_TIMEFRAME_MIN
        to LEAK_DETECTION_TIMEFRAME_MAX seconds.
        """
        # Enter infinite loop for simulation
        while True:
            # Leak
            yield self._env.timeout(random.randint(Leak_Detector.LEAK_DETECT_TIMEFRAME_MIN, Leak_Detector.LEAK_DETECT_TIMEFRAME_MAX))

            packet = communication.Communicator.Packet(
                sent_at=self._env.now,
                created_at=str(datetime.datetime.now()),
                sent_by=self._metadata.mac_address,
                sent_to='unknown',
                data={"event": "leak_detected",
                      "sent_by": self._instance_name}
            )

            self.transmit(communicators.rf.RF, packet)

            logger.info("LEEEEEEEEEEEEEEEEEEEEEEEEEEEEAK!")

    def update_battery(self):
        """Updates simulated device battery.

        The "battery" is really just a fake voltage source that
        decreases through time according to

            V(t) = INITIAL_BATTERY_VOLTAGE * (1 - (5*10^-8))^(self._env.now)

        where time is given in simulation timesteps (self._env.now),
        expected in seconds. The above equation results in ~1 year
        "battery life" by decaying the initial battery voltage over
        its lifetime.
        """
        new_voltage = Leak_Detector.INITIAL_BATTERY_VOLTAGE * (1 - (5*10**-8))**(self._env.now)

        # Get battery voltage state and update
        battery_state = self.get_state('battery_voltage')
        battery_state.value = new_voltage

    def update_temperature(self):
        """Generates normally distributed temperature around
        `NORMAL_TEMPERATURE` with stddev of `TEMPERATURE_STANDARD_DEVIATION`.
        """
        # Randomly generate new temperature
        new_temperature = random.gauss(self.get_state('temperature').value, Leak_Detector.TEMPERATURE_STANDARD_DEVIATION)

        # Grab current temperature and update
        temperature_state = self.get_state('temperature')
        temperature_state.value = new_temperature
