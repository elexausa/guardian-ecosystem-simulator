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
from enum import Enum

from ..core import communication
from ..core import communicators
from ..core import util
from ..core.models import machine

# Define logger
logger = logging.getLogger(__name__)


class Leak_Detector(machine.Machine):
    """ Simulates a leak detector

    Attributes:
        LEAK_DETECT_TIMEFRAME_MIN (int): Minimum amount of time (in simulation seconds) before a leak is detected.
        LEAK_DETECT_TIMEFRAME_MAX (int): Maximum amount of time (in simulation seconds) before a leak is detected.
        INITIAL_TEMPERATURE (double): The initial reading of internal temperature (in fahrenheit).
        TEMPERATURE_STANDARD_DEVIATION (int): How far the temperature can stray from attribute INITIAL_TEMPERATURE.
        INITIAL_BATTERY_VOLTAGE (int): The initial battery voltage (in millivolts).
        HEARTBEAT_PERIOD (int): Time (in simulation seconds) before a heartbeat packet is sent out.
    """

    class WaterSensorState(str, Enum):
        """Defines possible motor states.
        """
        DRY = 'DRY'
        WET = 'WET'

        def __repr__(self):
            return str(self.value)

    # Disable object `__dict__`
    __slots__ = ('_main_process', '_heartbeat_process', '_rf_recv_pipe', '_phys_recv_pipe')

    LEAK_DETECT_TIMEFRAME_MIN = 1
    LEAK_DETECT_TIMEFRAME_MAX = 5
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
           model.Machine.Data(
                name='heartbeat_period',
                type=model.Machine.Data.Type.UINT16,
                value=Leak_Detector.HEARTBEAT_PERIOD,
                description='Device heartbeat period (in seconds)'
            )
        )

        ########################
        ## Setup device state ##
        ########################

        # Battery state
        self.save_state(
            model.Machine.Data(
                name='battery_voltage',
                type=model.Machine.Data.Type.UINT16,
                value=Leak_Detector.INITIAL_BATTERY_VOLTAGE,
                description='Battery voltage (in millivolts)'
            )
        )

        # Temperature state
        self.save_state(
            model.Machine.Data(
                name='temperature',
                type=model.Machine.Data.Type.FLOAT,
                value=Leak_Detector.INITIAL_TEMPERATURE,
                description='Ambient air temperature near the device (in Fahrenheit)'
            )
        )

        # Spawn simulation processes
        self._main_process = self._env.process(self.main_process())

    ###############
    ## Utilities ##
    ###############

    def transmit(self, message: communicators.rf.RadioPacket.Message):
        # Prep packet
        packet = communicators.rf.RadioPacket(
            # Packet()
            sender=self._instance_name,
            simulation_time=self._env.now,
            realworld_time=str(datetime.datetime.now()),

            # RadioPacket()
            sent_by=self._metadata.mac_address,
            msg=message,
            dump=self.to_dict()
        )

        # Send
        self.transmit(communicators.rf.RF, packet)

    def generate_serial(self):
        """Overrides super generator to force custom format.
        """
        # Return a random string
        return '{model}{revision}{week}{year}{unit_number}'.format(
            model='GLD1',
            revision='01',
            week=str(datetime.datetime.now().isocalendar()[1]), # Week number
            year=str(datetime.datetime.now().isocalendar()[0]), # Year
            unit_number=str(random.randint(0,999999)).zfill(6) # Ensure padded to 6 chars
        )

    def generate_mac_addr(self):
        """Overrides super generator to force custom format.
        """
        return "30AEA" + util.generate.string(size=7)

    def heartbeat_process(self):
        """Sends a heartbeat to show the valve controller is still online
        and update cloud information.
        """
        while True:
            # Update battery and temperature
            self.update_battery()
            self.update_temperature()

            self.transmit(message=communicators.rf.RadioPacket.Message.HEARTBEAT)

            # Wait for next heartbeat
            yield self._env.timeout(self.get_setting('heartbeat_period').data.value)

    def main_process(self):
        """Simulates Leak Detector operation.
        """
        # On fresh call of `main_process()`, device starts up from unpowered state
        isPowered = False

        # Enter infinite loop for simulation
        while True:
            # Starting from unpowered
            if not isPowered:
                # Now powered
                isPowered = True

                # Update temperature
                self.update_temperature()
                self.update_battery()

                # Success
                logger.info('machine-{}: RUNNING'.format(self.self._metadata.serial_number))

                # Start heartbeat
                self._env.process(self.heartbeat_process())
            else:
                # Leak
                yield self._env.timeout(random.randint(Leak_Detector.LEAK_DETECT_TIMEFRAME_MIN, Leak_Detector.LEAK_DETECT_TIMEFRAME_MAX))

                # Send sensor wet
                self.transmit(message=communicators.rf.RadioPacket.Message.WET)

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
