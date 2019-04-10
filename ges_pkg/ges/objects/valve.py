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
import dataclasses
from enum import Enum

from ..core import communication
from ..core import communicators
from ..core.util import generate
from ..core.models import machine

# Define logger
logger = logging.getLogger(__name__)


class Valve_Controller(machine.Machine):
    """Simulates a valve controller.
    """

    class MotorState(str, Enum):
        """Defines possible motor states.
        """
        OPENING = 'OPENING'
        CLOSING = 'CLOSING'
        RESTING = 'RESTING'

        def __repr__(self):
            return str(self.value)

    class ValvePosition(str, Enum):
        """Defines possible valve positions.
        """
        OPENED = 'OPENED'
        CLOSED = 'CLOSED'
        STUCK = 'STUCK'

        def __repr__(self):
            return str(self.value)

    # Disable object `__dict__`
    __slots__ = ('_main_process', '_heartbeat_process', '_leak_process', '_rf_listener_process', '_rf_recv_pipe', 'leak_detectors', '_wan_recv_pipe')

    #########################
    ## Set class variables ##
    #########################

    # Heartbeat
    # HEARTBEAT_PERIOD = 1*60*60*12 # 12 hours -> seconds
    HEARTBEAT_PERIOD = 1*60*60 # 1 hour

    # Internal detection
    LEAK_DETECTION_TIME_MEAN = 1*60*30 # 30 minutes
    LEAK_DETECTION_TIME_STDDEV = 1*60*5 # 5 minutes

    # Motor open/close
    MOTOR_RUN_TIME_MEAN = 5 # seconds
    MOTOR_RUN_TIME_STDDEV = 1 # seconds

    # Stall
    CHANCE_TO_STALL = 5 # percent (1 - 100)
    STALL_TIME = 120 # Seconds

    # Temperature
    INITIAL_TEMPERATURE = 73.0 # Fahrenheit
    TEMPERATURE_STANDARD_DEVIATION = 2 # +/- 2 degrees

    def __init__(self, env=None, comm_tunnels=None, instance_name=None):
        super().__init__(env=env, comm_tunnels=comm_tunnels, codename='tiddymun', instance_name=instance_name)

        # Grab rf comm pipe
        self._rf_recv_pipe = self.get_communicator_recv_pipe(type=communicators.rf.RF)
        self._wan_recv_pipe = self.get_communicator_recv_pipe(type=communicators.WAN)

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
                    value=Valve_Controller.HEARTBEAT_PERIOD
                )
            )
        )

        # Choose location
        location = generate.location()

        # Latitudinal GPS coordinate
        self.save_setting(
            machine.Property(
                name='location_gps_lat',
                description='Latitudinal GPS coordinate',
                data=machine.Property.Data(
                    type=machine.Property.Data.Type.FLOAT,
                    value=location.lat
                )
            )
        )

        # Longitudinal GPS coordinate
        self.save_setting(
            machine.Property(
                name='location_gps_lon',
                description='Longitudinal GPS coordinate',
                data=machine.Property.Data(
                    type=machine.Property.Data.Type.FLOAT,
                    value=location.lon
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
                description='Valve controller firmware version',
                data=machine.Property.Data(
                    type=machine.Property.Data.Type.STRING,
                    value='4.0.0'
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
                    value=Valve_Controller.INITIAL_TEMPERATURE
                )
            )
        )

        # Valve opened/closed
        self.save_state(
            machine.Property(
                name='valve_position',
                description='Position of valve as OPENED/CLOSED/STUCK',
                data=machine.Property.Data(
                    type=machine.Property.Data.Type.STRING,
                    value=Valve_Controller.ValvePosition.OPENED
                )
            )
        )

        # Motor opening/closing/resting
        self.save_state(
            machine.Property(
                name='motor_state',
                description='State of motor as opening/closing/resting',
                data=machine.Property.Data(
                    type=machine.Property.Data.Type.STRING,
                    value=Valve_Controller.MotorState.RESTING
                )
            )
        )

        # Average motor current draw during operation
        self.save_state(
            machine.Property(
                name='motor_current_avg',
                description='Average current draw (in Amps) of motor during operation',
                data=machine.Property.Data(
                    type=machine.Property.Data.Type.FLOAT,
                    value=0.0
                )
            )
        )

        # Probe wet true/false
        self.save_state(
            machine.Property(
                name='probe',
                description='True if water detected at water probe',
                data=machine.Property.Data(
                    type=machine.Property.Data.Type.BOOLEAN,
                    value=False
                )
            )
        )

        # Leak detectors that are paired to the valve controller.
        self.leak_detectors = []

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
            model='GVC1',
            revision='01',
            week=str(datetime.datetime.now().isocalendar()[1]), # Week number
            year=str(datetime.datetime.now().isocalendar()[0]), # Year
            unit_number=str(random.randint(0,999999)).zfill(6) # Ensure padded to 6 chars
        )

    def generate_mac_addr(self):
        """Overrides super generator to force custom format.
        """
        return "30AEA402" + generate.string(size=4)

    ######################
    ## Device processes ##
    ######################

    def main_process(self):
        """Simulates device transient operation.

        During normal operation the device can be interrupted
        by other simulation events.
        """
        # On fresh call of `main_process()`, device must be turned on
        isPowered = False

        # Enter infinite loop for simulation
        while True:
            # Starting from unpowered
            if not isPowered:
                # Now powered
                isPowered = True

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

                # Start internal leak detection
                self._leak_process = self._env.process(self.leak_process())

                # Start listening for radio packets
                self._rf_listener_process = self._env.process(self.rf_listener_process())
            else:
                # Normal operation
                yield self._env.timeout(random.randint(60, 300))

                # Update states
                self.update_temperature()

                logger.info('{}-{}: beep'.format(self._metadata.codename, self._metadata.serial_number))

    def heartbeat_process(self):
        """Sends a heartbeat message over WAN.

        Valve Controllers sync also sync their settings with every heartbeat.
        """
        while True:
            # Update states
            self.update_temperature()

            # Send event
            self.send_event(type=communicators.wan.EventType.HEARTBEAT)

            # Use opportunity to sync latest setting/state changes
            self.sync_to_db()

            # Wait for next heartbeat
            yield self._env.timeout(self.get_setting('heartbeat_period').data.value)

    def leak_process(self):
        """Occasionally detects a leak.
        """
        while True:
            # Yield for define mean leak detection time +- the provided stddev
            yield self._env.timeout(random.normalvariate(Valve_Controller.LEAK_DETECTION_TIME_MEAN, Valve_Controller.LEAK_DETECTION_TIME_STDDEV))

            # Wet probe!
            self.wet_probe()

            # Start valve close process
            self._env.process(self.close())

            # Dry probe in 2-8 seconds
            yield self._env.timeout(random.randint(2, 8))

            # Dry probe!
            self.dry_probe()

            # Use opportunity to sync latest setting/state changes
            self.sync_to_db()

    def rf_listener_process(self):
        """Listens for leaks from "paired" leak detectors.
        """
        while True:
             # Wait for packet
            packet = yield self._rf_recv_pipe.get()

            # Get sender and serial number
            sender = packet.sender
            sender_serial_number = sender._metadata.serial_number

            logger.info('{}-{}: radio packet received from {}'.format(self._metadata.codename, self._metadata.serial_number, sender_serial_number))
            logger.debug('{}-{}: radio packet received from {}: {}'.format(self._metadata.codename, self._metadata.serial_number, sender_serial_number, packet))

            # Check is "paired"
            if sender not in self.leak_detectors:
                logger.info('{}-{}: not paired, radio packet dropped'.format(self._metadata.codename, self._metadata.serial_number))
                continue

            # Process message
            if packet.msg == communicators.rf.RadioPacket.Message.WET:
                # Send event
                self.send_event(type=communicators.wan.EventType.LEAK_DETECTED)

                # Start valve close process
                self._env.process(self.close())
            elif packet.msg == communicators.rf.RadioPacket.Message.DRY:
                # Send event
                self.send_event(type=communicators.wan.EventType.LEAK_CLEARED)

            # Use opportunity to sync latest setting/state changes
            self.sync_to_db()

    ####################
    ## Device actions ##
    ####################

    def open(self):
        """Opens valve.

        Must be called via simpy process (simpy.Environment.process()).
        """
        # Send start of event
        logger.info('{}-{}: opening valve'.format(self._metadata.codename, self._metadata.serial_number))
        self.send_event(type=communicators.wan.EventType.VALVE_OPENING)

        # Grab states
        motor_state = self.get_state('motor_state')
        valve_state = self.get_state('valve_position')

        # Ensure valve not already open
        if valve_state.data.value == Valve_Controller.ValvePosition.OPENED:
            logger.info('{}-{}: valve already opened'.format(self._metadata.codename, self._metadata.serial_number))
            self.send_event(type=communicators.wan.EventType.VALVE_OPENED)
            return

        # Ensure motor starting from resting
        if motor_state.data.value != Valve_Controller.MotorState.RESTING:
            logger.info('{}-{}: motor busy, aborting'.format(self._metadata.codename, self._metadata.serial_number))
            return

        # Update motor state
        motor_state.data.value = Valve_Controller.MotorState.CLOSING

        # Allow time to close (MOTOR_RUN_TIME_MEAN +- MOTOR_RUN_TIME_STDDEV)
        yield self._env.timeout(random.normalvariate(Valve_Controller.MOTOR_RUN_TIME_MEAN, Valve_Controller.MOTOR_RUN_TIME_STDDEV))

        # Occasionally force stall condition
        if random.randint(0, 100) <= Valve_Controller.CHANCE_TO_STALL:
            # Update state
            valve_state.data.value = Valve_Controller.ValvePosition.STUCK
            motor_state.data.value = Valve_Controller.MotorState.RESTING

            logger.info('{}-{}: valve stuck'.format(self._metadata.codename, self._metadata.serial_number))
            self.send_event(type=communicators.wan.EventType.VALVE_STUCK)
            return

        # Update states
        motor_state.data.value = Valve_Controller.MotorState.RESTING
        valve_state.data.value = Valve_Controller.ValvePosition.OPENED

        # Done
        logger.info('{}-{}: valve opened'.format(self._metadata.codename, self._metadata.serial_number))
        self.send_event(type=communicators.wan.EventType.VALVE_OPENED)

    def close(self):
        """Closes valve.

        Must be called via simpy process (simpy.Environment.process()).
        """
        # Send start of event
        logger.info('{}-{}: closing valve'.format(self._metadata.codename, self._metadata.serial_number))
        self.send_event(type=communicators.wan.EventType.VALVE_CLOSING)

        # Grab states
        motor_state = self.get_state('motor_state')
        valve_state = self.get_state('valve_position')

        # Ensure valve not already closed
        if valve_state.data.value == Valve_Controller.ValvePosition.CLOSED:
            logger.info('{}-{}: valve already closed'.format(self._metadata.codename, self._metadata.serial_number))
            self.send_event(type=communicators.wan.EventType.VALVE_CLOSED)
            return

        # Ensure motor starting from resting
        if motor_state.data.value != Valve_Controller.MotorState.RESTING:
            logger.info('{}-{}: motor busy, aborted'.format(self._metadata.codename, self._metadata.serial_number))
            return

        # Update motor state
        motor_state.data.value = Valve_Controller.MotorState.CLOSING

        # Allow time to close (MOTOR_RUN_TIME_MEAN +- MOTOR_RUN_TIME_STDDEV)
        yield self._env.timeout(random.normalvariate(Valve_Controller.MOTOR_RUN_TIME_MEAN, Valve_Controller.MOTOR_RUN_TIME_STDDEV))

        # Occasionally force stall condition
        if random.randint(0, 100) <= Valve_Controller.CHANCE_TO_STALL:
            # Update states
            valve_state.data.value = Valve_Controller.ValvePosition.STUCK
            motor_state.data.value = Valve_Controller.MotorState.RESTING

            logger.info('{}-{}: valve stuck'.format(self._metadata.codename, self._metadata.serial_number))
            self.send_event(type=communicators.wan.EventType.VALVE_STUCK)
            return

        # Update states
        motor_state.data.value = Valve_Controller.MotorState.RESTING
        valve_state.data.value = Valve_Controller.ValvePosition.CLOSED

        # Done
        logger.info('{}-{}: valve closed'.format(self._metadata.codename, self._metadata.serial_number))
        self.send_event(type=communicators.wan.EventType.VALVE_CLOSED)

        # Wait a lil bitty bit
        yield self._env.timeout(random.randint(5, 10))

        # Start valve open process
        self._env.process(self.open())

    def wet_probe(self):
        logger.info('{}-{}: probe1 is wet!'.format(self._metadata.codename, self._metadata.serial_number))

        # Set probe to wet
        self.get_state('probe1_wet').data.value = True

        # Send event
        self.send_event(type=communicators.wan.EventType.LEAK_DETECTED, extra_data={'from': 'probe1'})

    def dry_probe(self):
        logger.info('{}-{}: probe1 is dry!'.format(self._metadata.codename, self._metadata.serial_number))

        # Set probe to wet
        self.get_state('probe1_wet').data.value = False

        # Send event
        self.send_event(type=communicators.wan.EventType.LEAK_CLEARED, extra_data={'from': 'probe1'})

    def update_temperature(self):
        """Generates normally distributed temperature around
        current temperature with stddev of `TEMPERATURE_STANDARD_DEVIATION`.
        """
        # Randomly generate new temperature
        new_temperature = random.gauss(self.get_state('temperature').data.value, Valve_Controller.TEMPERATURE_STANDARD_DEVIATION)

        # Grab current temperature and update
        temperature_state = self.get_state('temperature')
        temperature_state.data.value = new_temperature