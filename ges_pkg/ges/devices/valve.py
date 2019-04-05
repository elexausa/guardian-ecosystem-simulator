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
from ..core import model
from ..core.util import generate
from ..core import communicators

logger = logging.getLogger(__name__)


class ValveController(model.Device):
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
    HEARTBEAT_PERIOD = 30 # 30 seconds minutes

    # Internal detection
    LEAK_DETECTION_TIME_MEAN = 1*60*60 # 1 hour
    LEAK_DETECTION_TIME_STDDEV = 1*60*15 # 15 minutes

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
        self._ip_recv_pipe = self.get_communicator_recv_pipe(type=communicators.IP_Network)

        ###############################
        ## Configure device settings ##
        ###############################

        # Heartbeat period
        self.save_setting(
            model.Property(
                name='heartbeat_period',
                description='Device heartbeat period (in seconds)',
                data=model.Property.Data(
                    type=model.Property.Data.Type.UINT16,
                    value=ValveController.HEARTBEAT_PERIOD
                )
            )
        )

        # Time to wait before reacting to leak event
        self.save_setting(
            model.Property(
                name='close_delay',
                description='Amount of time to wait (in seconds) before closing valve',
                data=model.Property.Data(
                    type=model.Property.Data.Type.UINT16,
                    value=5
                )
            )
        )

        # Latitudinal GPS coordinate
        self.save_setting(
            model.Property(
                name='location_gps_lat',
                description='Latitudinal GPS coordinate',
                data=model.Property.Data(
                    type=model.Property.Data.Type.FLOAT,
                    value=5
                )
            )
        )

        # Longitudinal GPS coordinate
        self.save_setting(
            model.Property(
                name='location_gps_lon',
                description='Longitudinal GPS coordinate',
                data=model.Property.Data(
                    type=model.Property.Data.Type.FLOAT,
                    value=5
                )
            )
        )

        ######################
        ## Initialize state ##
        ######################

        # Valve opened/closed
        self.save_state(
            model.Property(
                name='valve',
                description='State of valve as OPENED/CLOSED/STUCK',
                data=model.Property.Data(
                    type=model.Property.Data.Type.STRING,
                    value=ValveController.ValveState.OPENED
                )
            )
        )

        # Motor opening/closing/resting
        self.save_state(
            model.Property(
                name='motor',
                description='State of motor as opening/closing/resting',
                data=model.Property.Data(
                    type=model.Property.Data.Type.STRING,
                    value=ValveController.MotorState.RESTING
                )
            )
        )

        # Realtime motor current draw
        self.save_state(
            model.Property(
                name='motor_current',
                description='Current draw of motor (in Amps)',
                data=model.Property.Data(
                    type=model.Property.Data.Type.FLOAT,
                    value=0.0
                )
            )
        )

        # Firmware version
        self.save_state(
            model.Property(
                name='firmware_version',
                description='Valve controller firmware version',
                data=model.Property.Data(
                    type=model.Property.Data.Type.STRING,
                    value='4.0.0'
                )
            )
        )

        # Probe1 wet true/false
        self.save_state(
            model.Property(
                name='probe1_wet',
                description='True if water detected at probe1',
                data=model.Property.Data(
                    type=model.Property.Data.Type.BOOLEAN,
                    value=False
                )
            )
        )

        # Leak detectors that are paired to the valve controller.
        self.leak_detectors = []

        # Spawn simulation processes
        self._main_process = self._env.process(self.main_process())
        self._leak_process = self._env.process(self.leak_process())
        self._heartbeat_process = None

    def generate_serial(self):
        """
        Should be overridden by implementation and be made
        to generate realistic serial numbers.
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

        # On fresh call of `run()`, device must be turned on
        isPowered = False

        # Enter infinite loop for simulation
        while True:
            # Starting from unpowered
            if not isPowered:
                # Set to powered
                isPowered = True

                logger.info('%s: PLUGGED IN', self._instance_name)

                # Wait for startup
                yield self._env.timeout(random.normalvariate(ValveController.STARTUP_TIME_MEAN, ValveController.STARTUP_TIME_STDDEV))

                # Success
                logger.info('%s: RUNNING', self._instance_name)

                # Prep packet
                packet = communication.Communicator.OperationPacket(
                    # Packet()
                    sender=self._instance_name,
                    simulation_time=self._env.now,
                    realworld_time=str(datetime.datetime.now()),

                    # OperationPacket()
                    type=communication.Communicator.OperationPacket.Type.MACHINE_CREATE,

                    data=self.to_dict()
                )

                # Send
                self.transmit(communicators.ip_network.IP_Network, packet)

                # Start heartbeat
                self._env.process(self.heartbeat_process())
            else:
                # Normal operation
                yield self._env.timeout(random.randint(60, 300))
                logger.info('%s: beep', self._instance_name)

    def heartbeat_process(self):
        """Sends a heartbeat to show the valve controller is still online
        and update cloud information.
        """
        while True:
            yield self._env.timeout(self.get_setting('heartbeat_period').data.value)

            # Prep packet
            packet = communication.Communicator.EventPacket(
                # Packet()
                sender=self._instance_name,
                simulation_time=self._env.now,
                realworld_time=str(datetime.datetime.now()),

                # EventPacket()
                type=communication.Communicator.EventPacket.Type.HEARTBEAT,

                data={
                    "target": 'machine-{}'.format(str(self._metadata.serial_number)),
                    "trigger": "self",
                    "type": "HEARTBEAT",
                    "timestamp": str(datetime.datetime.now())
                }
            )

            # Send
            self.transmit(communicators.ip_network.IP_Network, packet)

    def leak_process(self):
        """Occasionally detects a leak.
        """
        while True:
            # Yield for define mean leak detection time +- the provided stddev
            yield self._env.timeout(random.normalvariate(ValveController.LEAK_DETECTION_TIME_MEAN, ValveController.LEAK_DETECTION_TIME_STDDEV))

            # Acknowledge leak
            self.acknowledge_leak(self._env.now)

            # Start valve close process
            self._env.process(self.close())

    ####################
    ## Device actions ##
    ####################

    def open(self):
        # TODO
        pass

    def close(self):
        """Closes valve.

        Must be called via simpy process (simpy.Environment.process()).
        """

        logger.info(self._instance_name + ': CLOSING VALVE')

        # Grab required info
        motor_state = self.get_state('motor')
        # motor_amperage_state = self.get_state('motor_current')
        valve_state = self.get_state('valve')

        # Ensure valve starting as opened
        if valve_state.data.value in [ValveController.ValveState.OPENED.value, ValveController.ValveState.STUCK.value]:
            logging.warning(self._instance_name + ': VALVE ALREADY CLOSED, ABORTING')
            return

        # Ensure motor starting from resting
        if motor_state.data.value != ValveController.MotorState.RESTING.value:
            logging.warning(self._instance_name + ': MOTOR BUSY, ABORTING')
            return

        # Set to closing
        motor_state.data.value = ValveController.MotorState.CLOSING.value

        # Allow time to close (MOTOR_RUN_TIME_MEAN +- MOTOR_RUN_TIME_STDDEV)
        yield self._env.timeout(random.normalvariate(ValveController.MOTOR_RUN_TIME_MEAN, ValveController.MOTOR_RUN_TIME_STDDEV))

        # Occasionally force stall condition
        if random.randint(0, 100) <= ValveController.CHANCE_TO_STALL:
            # Valve is stuck
            valve_state.data.value = ValveController.ValveState.STUCK.value
            logging.info(self._instance_name + ': VALVE STALLED')
            return

        # Stop motor
        motor_state.data.value = ValveController.MotorState.RESTING

        # Done
        logging.info(self._instance_name + ': VALVE CLOSED')

    def acknowledge_leak(self, time: int):
        logger.info(self._instance_name + ': LEAK DETECTED')

        # Set probe to wet
        self.get_state('probe1_wet').data.value = True

        # Prep packet
        packet = communication.Communicator.EventPacket(
            # Packet()
            sender=self._instance_name,
            simulation_time=self._env.now,
            realworld_time=str(datetime.datetime.now()),

            # OperationPacket()
            type=communication.Communicator.EventPacket.Type.LEAK_DETECTED,
            data=json.dumps({
                'cause': 'internal_probe'
            })
        )

        # Send
        self.transmit(communicators.ip_network.IP_Network, packet)
