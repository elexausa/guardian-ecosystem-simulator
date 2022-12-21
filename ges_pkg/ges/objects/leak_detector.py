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
    """Simulates a leak detector.
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

    # Heartbeat
    HEARTBEAT_PERIOD = 1*60*60*1 # 1 hours -> seconds

    # Internal detection
    LEAK_DETECT_TIMEFRAME_MIN = 60 # 1 minute
    LEAK_DETECT_TIMEFRAME_MAX = 1*60*60 # 60 minutes

    # Temperature
    INITIAL_TEMPERATURE = 73.0 # Fahrenheit
    TEMPERATURE_STANDARD_DEVIATION = 2 # +/- 2 degrees

    # Battery
    INITIAL_BATTERY_VOLTAGE = 3600 # millivolts

    def __init__(self, env=None, comm_tunnels=None, instance_name=None):
        super().__init__(env=env, comm_tunnels=comm_tunnels, codename='ahurani', instance_name=instance_name)

        ###############################
        ## Configure device settings ##
        ###############################

        # Heartbeat period
        self.save_setting(
            machine.Property(
                name='heartbeat_period',
                description='Device heartbeat period (in seconds)',
                data=machine.Property.Data(
                    type=machine.Property.Data.Type.UINT16,
                    value=Leak_Detector.HEARTBEAT_PERIOD
                )
            )
        )

        ######################
        ## Initialize state ##
        ######################

        # Firmware version
        self.save_state(
            machine.Property(
                name='firmware_version',
                description='Leak detector firmware version',
                data=machine.Property.Data(
                    type=machine.Property.Data.Type.STRING,
                    value='1.0.0'
                )
            )
        )

        # Temperature state
        self.save_state(
            machine.Property(
                name='temperature',
                description='Ambient air temperature near the device (in Fahrenheit)',
                data=machine.Property.Data(
                    type=machine.Property.Data.Type.FLOAT,
                    value=Leak_Detector.INITIAL_TEMPERATURE
                )
            )
        )

        # Battery state
        self.save_state(
            machine.Property(
                name='battery_voltage',
                description='Battery voltage (in millivolts)',
                data=machine.Property.Data(
                    type=machine.Property.Data.Type.UINT16,
                    value=Leak_Detector.INITIAL_BATTERY_VOLTAGE
                )
            )
        )

        # Top probe state
        self.save_state(
            machine.Property(
                name='top_probe',
                description='Top water probe state (true indicates wet)',
                data=machine.Property.Data(
                    type=machine.Property.Data.Type.BOOLEAN,
                    value=False
                )
            )
        )

        # Bottom probe state
        self.save_state(
            machine.Property(
                name='bottom_probe',
                description='Bottom water probe state (true indicates wet)',
                data=machine.Property.Data(
                    type=machine.Property.Data.Type.BOOLEAN,
                    value=False
                )
            )
        )

        # Spawn main process
        self._main_process = self._env.process(self.main_process())

    ###############
    ## Utilities ##
    ###############

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

    ######################
    ## Device processes ##
    ######################

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

                # Update states
                self.update_temperature()
                self.update_battery()

                logger.info('{}-{}: powered, creating in db...'.format(self._metadata.codename, self._metadata.serial_number))

                # Send operation
                self.send_operation(type=communicators.wan.OperationType.MACHINE_CREATE, data=self.to_dict())

                # Allow operation to finish
                # TODO: implement callback
                yield self._env.timeout(5)

                # Success
                logger.info('{}-{}: created!'.format(self._metadata.codename, self._metadata.serial_number))

                # Start heartbeat
                self._env.process(self.heartbeat_process())
            else:
                # Leak
                yield self._env.timeout(random.randint(Leak_Detector.LEAK_DETECT_TIMEFRAME_MIN, Leak_Detector.LEAK_DETECT_TIMEFRAME_MAX))

                logger.info('{}-{}: LEEEEEEEEEEEEEEEEEEEEEEEEEEEEAK!'.format(self._metadata.codename, self._metadata.serial_number))

                # Choose probe
                probe_state = random.choice([self.get_state('top_probe'), self.get_state('bottom_probe')])

                # Probe wet
                probe_state.data.value = True

                # Send sensor wet
                self.broadcast(message=communicators.rf.RadioPacket.Message.WET)
                self.send_event(type=communicators.wan.EventType.SENSOR_WET)

                # Wait a bit then dry up
                yield self._env.timeout(10)

                # Probe wet
                probe_state.data.value = False

                # Send sensor dry
                self.broadcast(message=communicators.rf.RadioPacket.Message.DRY)
                self.send_event(type=communicators.wan.EventType.SENSOR_DRY)

                logger.info('{}-{}: DRY!'.format(self._metadata.codename, self._metadata.serial_number))

                # Sync to db
                self.sync_to_db()

    def heartbeat_process(self):
        """Broadcasts a heartbeat message.

        Also updates internal states including temperature and battery voltage.
        """
        while True:
            # Update states
            self.update_temperature()
            self.update_battery()

            self.broadcast(message=communicators.rf.RadioPacket.Message.HEARTBEAT)
            self.send_event(type=communicators.wan.EventType.HEARTBEAT)

            # Use opportunity to sync latest setting/state changes
            self.sync_to_db()

            # Wait for next heartbeat
            yield self._env.timeout(self.get_setting('heartbeat_period').data.value)

    ####################
    ## Device actions ##
    ####################

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
        battery_state.data.value = new_voltage

    def update_temperature(self):
        """Generates normally distributed temperature around
        current temperature with stddev of `TEMPERATURE_STANDARD_DEVIATION`.
        """
        # Randomly generate new temperature
        new_temperature = random.gauss(self.get_state('temperature').data.value, Leak_Detector.TEMPERATURE_STANDARD_DEVIATION)

        # Grab current temperature and update
        temperature_state = self.get_state('temperature')
        temperature_state.data.value = new_temperature
