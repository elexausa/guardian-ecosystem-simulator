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

    Attributes:
        LEAK_DETECT_TIMEFRAME_MIN (int): Minimum amount of time (in simulation intervals) before a leak is detected.
        LEAK_DETECT_TIMEFRAME_MAX (int): Maximum amount of time (in simulation intervals) before a leak is detected.
        HEARTBEAT_PERIOD (int): Time (in simulation intervals) before a heartbeat packet is sent out.
        PRECENT_CHANCE_TO_STALL (int): The percent chance the valve controller will stall when closing.
        STALL_TIME (int): Amount of time (in simulation intervals) the valve controller is down if it stalls.
        MotorState (Enum): All applicable motor states.
        ValveState (Enum): All applicable valve states.
    """

    class MotorState(str, Enum):
        """Defines possible motor states.
        """
        OPENING = 'OPENING'
        CLOSING = 'CLOSING'
        RESTING = 'RESTING'

        def __repr__(self):
            return str(self.value)

    class ValveState(str, Enum):
        """Defines possible motor states.
        """
        OPENED = 'OPENED'
        CLOSED = 'CLOSED'
        STUCK = 'STUCK'

        def __repr__(self):
            return str(self.value)

    # Disable object `__dict__`
    __slots__ = ('_main_process', '_heartbeat_process', '_leak_process', '_rf_recv_pipe', 'leak_detectors', '_ip_recv_pipe')

    #########################
    ## Set class variables ##
    #########################

    # Startup
    STARTUP_TIME_MEAN = 5 # seconds
    STARTUP_TIME_STDDEV = 1 # seconds

    # Heartbeat
    # HEARTBEAT_PERIOD = 1*60*60*12 # 12 hours -> seconds
    # HEARTBEAT_PERIOD = 1*60*60 # 1 hour
    HEARTBEAT_PERIOD = 30 # 30 seconds

    # Internal detection
    LEAK_DETECTION_TIME_MEAN = 1*60*30 # 30 minutes
    LEAK_DETECTION_TIME_STDDEV = 1*60*5 # 5 minutes
    # LEAK_DETECTION_TIME_MEAN = 30 # 30 seconds
    # LEAK_DETECTION_TIME_STDDEV = 5 # 5 seconds

    # Motor open/close
    MOTOR_RUN_TIME_MEAN = 5 # seconds
    MOTOR_RUN_TIME_STDDEV = 1 # seconds

    # Stall
    CHANCE_TO_STALL = 5 # percent (1 - 100)
    STALL_TIME = 120 # Seconds

    def __init__(self, env=None, comm_tunnels=None, instance_name=None):
        super().__init__(env=env, comm_tunnels=comm_tunnels, codename='tiddymun', instance_name=instance_name)

        # Grab rf comm pipe
        self._rf_recv_pipe = self.get_communicator_recv_pipe(type=communicators.rf.RF)
        self._ip_recv_pipe = self.get_communicator_recv_pipe(type=communicators.WAN)

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

        # Time to wait before reacting to leak event
        self.save_setting(
            machine.Property(
                name='close_delay',
                description='Amount of time to wait (in seconds) before closing valve',
                data=machine.Property.Data(
                    type=machine.Property.Data.Type.UINT16,
                    value=5
                )
            )
        )

        # Latitudinal GPS coordinate
        self.save_setting(
            machine.Property(
                name='location_gps_lat',
                description='Latitudinal GPS coordinate',
                data=machine.Property.Data(
                    type=machine.Property.Data.Type.FLOAT,
                    value=5
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
                    value=5
                )
            )
        )

        ######################
        ## Initialize state ##
        ######################

        # Valve opened/closed
        self.save_state(
            machine.Property(
                name='valve',
                description='State of valve as OPENED/CLOSED/STUCK',
                data=machine.Property.Data(
                    type=machine.Property.Data.Type.STRING,
                    value=Valve_Controller.ValveState.OPENED
                )
            )
        )

        # Motor opening/closing/resting
        self.save_state(
            machine.Property(
                name='motor',
                description='State of motor as opening/closing/resting',
                data=machine.Property.Data(
                    type=machine.Property.Data.Type.STRING,
                    value=Valve_Controller.MotorState.RESTING
                )
            )
        )

        # Realtime motor current draw
        self.save_state(
            machine.Property(
                name='motor_current',
                description='Current draw of motor (in Amps)',
                data=machine.Property.Data(
                    type=machine.Property.Data.Type.FLOAT,
                    value=0.0
                )
            )
        )

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

        # Probe1 wet true/false
        self.save_state(
            machine.Property(
                name='probe1_wet',
                description='True if water detected at probe1',
                data=machine.Property.Data(
                    type=machine.Property.Data.Type.BOOLEAN,
                    value=False
                )
            )
        )

        # Leak detectors that are paired to the valve controller.
        self.leak_detectors = []

        # Spawn simulation processes
        self._main_process = self._env.process(self.main_process())
        self._leak_process = self._env.process(self.leak_process())

    ###############
    ## Utilities ##
    ###############

    def send_event(self, type: communicators.wan.EventType, origin: str = 'self', extra_data: dict = None):
        # Prep data
        data = {
            "target": 'machine-{}'.format(str(self._metadata.serial_number)),
            "type": type.name,
            "origin": origin,
            "timestamp": str(datetime.datetime.now()),
            "data": extra_data
        }

        # Send operation
        self.send_operation(communicators.wan.OperationType.EVENTS_CREATE, data=data)

    def send_operation(self, type: communicators.wan.OperationType, data: dict):
        # Prep packet
        packet = communicators.wan.OperationPacket(
            # Packet()
            sender=self._instance_name,
            simulation_time=self._env.now,
            realworld_time=str(datetime.datetime.now()),

            # EventPacket()
            type=type,
            data=data
        )

        # Send
        self.transmit(communicators.wan.WAN, packet)

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

                logger.info('machine-{}: PLUGGED IN'.format(self._metadata.serial_number))

                # Wait for startup to complete
                yield self._env.timeout(random.normalvariate(Valve_Controller.STARTUP_TIME_MEAN, Valve_Controller.STARTUP_TIME_STDDEV))

                # Success
                logger.info('machine-{}: RUNNING'.format(self._metadata.serial_number))

                # Send operation
                self.send_operation(type=communicators.wan.OperationType.MACHINE_CREATE, data=self.to_dict())

                # Allow operation to finish
                yield self._env.timeout(2)

                # Start heartbeat
                self._env.process(self.heartbeat_process())
            else:
                # Normal operation
                yield self._env.timeout(random.randint(60, 300))

                logger.info('machine-{}: beep'.format(self._metadata.serial_number))

    def heartbeat_process(self):
        """Sends a heartbeat to show the valve controller is still online
        and update cloud information.
        """
        while True:
            # Send event
            self.send_event(type=communicators.wan.EventType.HEARTBEAT)

            # Sync settings
            for setting in self._settings:
                data = {
                    'machine_id': self._metadata.serial_number,
                    'setting_name': setting.name,
                    'setting_data': dataclasses.asdict(setting.data)
                }
                self.send_operation(type=communicators.wan.OperationType.MACHINE_UPDATE_SETTING, data=data)

            # Sync states
            for state in self._states:
                data = {
                    'machine_id': self._metadata.serial_number,
                    'state_name': state.name,
                    'state_data': dataclasses.asdict(state.data)
                }
                self.send_operation(type=communicators.wan.OperationType.MACHINE_UPDATE_STATE, data=data)

            # Wait for next heartbeat
            yield self._env.timeout(self.get_setting('heartbeat_period').data.value)

    def leak_process(self):
        """Occasionally detects a leak.
        """
        while True:
            # Yield for define mean leak detection time +- the provided stddev
            yield self._env.timeout(random.normalvariate(Valve_Controller.LEAK_DETECTION_TIME_MEAN, Valve_Controller.LEAK_DETECTION_TIME_STDDEV))

            # Acknowledge leak
            self.wet_probe(self._env.now)

            # Start valve close process
            self._env.process(self.close())

            # Dry probe in 2-8 seconds
            yield self._env.timeout(random.randint(2, 8))

    ####################
    ## Device actions ##
    ####################

    def open(self):
        """Opens valve.

        Must be called via simpy process (simpy.Environment.process()).
        """
        # Send start of event
        logger.info('machine-{}: opening valve'.format(self._metadata.serial_number))
        self.send_event(type=communicators.wan.EventType.VALVE_OPENING)

        # Grab states
        motor_state = self.get_state('motor')
        valve_state = self.get_state('valve')

        # Ensure valve not already open
        if valve_state.data.value == Valve_Controller.ValveState.OPENED:
            logger.info('machine-{}: valve already opened'.format(self._metadata.serial_number))
            self.send_event(type=communicators.wan.EventType.VALVE_OPENED)
            return

        # Ensure motor starting from resting
        if motor_state.data.value != Valve_Controller.MotorState.RESTING:
            logger.info('machine-{}: motor busy, aborting'.format(self._metadata.serial_number))
            return

        # Update motor state
        motor_state.data.value = Valve_Controller.MotorState.CLOSING

        # Allow time to close (MOTOR_RUN_TIME_MEAN +- MOTOR_RUN_TIME_STDDEV)
        yield self._env.timeout(random.normalvariate(Valve_Controller.MOTOR_RUN_TIME_MEAN, Valve_Controller.MOTOR_RUN_TIME_STDDEV))

        # Occasionally force stall condition
        if random.randint(0, 100) <= Valve_Controller.CHANCE_TO_STALL:
            # Update state
            valve_state.data.value = Valve_Controller.ValveState.STUCK
            motor_state.data.value = Valve_Controller.MotorState.RESTING

            logger.info('machine-{}: valve stuck'.format(self._metadata.serial_number))
            self.send_event(type=communicators.wan.EventType.VALVE_STUCK)
            return

        # Update states
        motor_state.data.value = Valve_Controller.MotorState.RESTING
        valve_state.data.value = Valve_Controller.ValveState.OPENED

        # Done
        logger.info('machine-{}: valve opened'.format(self._metadata.serial_number))
        self.send_event(type=communicators.wan.EventType.VALVE_OPENED)

    def close(self):
        """Closes valve.

        Must be called via simpy process (simpy.Environment.process()).
        """
        # Send start of event
        logger.info('machine-{}: closing valve'.format(self._metadata.serial_number))
        self.send_event(type=communicators.wan.EventType.VALVE_CLOSING)

        # Grab states
        motor_state = self.get_state('motor')
        valve_state = self.get_state('valve')

        # Ensure valve not already closed
        if valve_state.data.value == Valve_Controller.ValveState.CLOSED:
            logger.info('machine-{}: valve already closed'.format(self._metadata.serial_number))
            self.send_event(type=communicators.wan.EventType.VALVE_CLOSED)
            return

        # Ensure motor starting from resting
        if motor_state.data.value != Valve_Controller.MotorState.RESTING:
            logger.info('machine-{}: motor busy, aborted'.format(self._metadata.serial_number))
            return

        # Update motor state
        motor_state.data.value = Valve_Controller.MotorState.CLOSING

        # Allow time to close (MOTOR_RUN_TIME_MEAN +- MOTOR_RUN_TIME_STDDEV)
        yield self._env.timeout(random.normalvariate(Valve_Controller.MOTOR_RUN_TIME_MEAN, Valve_Controller.MOTOR_RUN_TIME_STDDEV))

        # Occasionally force stall condition
        if random.randint(0, 100) <= Valve_Controller.CHANCE_TO_STALL:
            # Update states
            valve_state.data.value = Valve_Controller.ValveState.STUCK
            motor_state.data.value = Valve_Controller.MotorState.RESTING

            logger.info('machine-{}: valve stuck'.format(self._metadata.serial_number))
            self.send_event(type=communicators.wan.EventType.VALVE_STUCK)
            return

        # Update states
        motor_state.data.value = Valve_Controller.MotorState.RESTING
        valve_state.data.value = Valve_Controller.ValveState.CLOSED

        # Done
        logger.info('machine-{}: valve closed'.format(self._metadata.serial_number))
        self.send_event(type=communicators.wan.EventType.VALVE_CLOSED)

        # Start valve open process
        self._env.process(self.open())

    def wet_probe(self, time: int):
        logger.info('machine-{}: probe1 is wet!'.format(self._metadata.serial_number))

        # Set probe to wet
        self.get_state('probe1_wet').data.value = True

        # Send event
        self.send_event(type=communicators.wan.EventType.LEAK_DETECTED, extra_data={'where': 'probe1'})

    def dry_probe(self, time: int):
        logger.info('machine-{}: probe1 is dry!'.format(self._metadata.serial_number))

        # Set probe to wet
        self.get_state('probe1_wet').data.value = False

        # Send event
        self.send_event(type=communicators.wan.EventType.LEAK_CLEARED, extra_data={'where': 'probe1'})

