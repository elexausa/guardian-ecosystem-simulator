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
from enum import Enum

from ..core import communication
from ..core import model
from ..core.util import generate
from ..core import communicators

logger = logging.getLogger(__name__)


class Valve(model.Device):
    """ Simulates a valve controller.
    
    Attributes:
        LEAK_DETECT_TIMEFRAME_MIN (int): Minimum amount of time (in simulation seconds) before a leak is detected.
        LEAK_DETECT_TIMEFRAME_MAX (int): Maximum amount of time (in simulation seconds) before a leak is detected.
        HEARTBEAT_PERIOD (int): Time (in simulation seconds) before a heartbeat packet is sent out.
        PRECENT_CHANCE_TO_STALL (int): The percent chance the valve controller will stall when closing.
        STALL_TIME (int): Amount of time (in simulation seconds) the valve controller is down if it stalls.
        MotorState (Enum): All applicable motor states.
        ValveState (Enum): All applicable valve states.
    """

    # Disable object `__dict__`
    __slots__ = ('_main_process', '_rf_recv_pipe', '_heartbeat_process', 'leak_detectors')

    LEAK_DETECT_TIMEFRAME_MIN = 1
    LEAK_DETECT_TIMEFRAME_MAX = 1*60*60*24*30 # 30 days

    HEARTBEAT_PERIOD = 1*60*60*12 # 12 hours -> seconds

    PERCENT_CHANCE_TO_STALL = 5

    STALL_TIME = 120

    MotorState = Enum("MotorState", "opening closing resting")
    ValveStatus = Enum("ValveStatus", "opened closed stuck")

    def __init__(self, env=None, comm_tunnels=None, instance_name=None):
        super().__init__(env=env, comm_tunnels=comm_tunnels, codename='tiddymun', instance_name=instance_name)

        # Grab rf comm pipe
        self._rf_recv_pipe = self.get_communicator_recv_pipe(type=communicators.rf.RF)

        ###############################
        ## Configure device settings ##
        ###############################

        # Heartbeat period
        self.save_setting(
           model.Device.Data(
                name='heartbeat_period',
                type=model.Device.Data.Type.UINT16,
                value=Valve.HEARTBEAT_PERIOD,
                description='Device heartbeat period (in seconds)'
            )
        )

        # Time to wait before reacting to leak event
        self.save_setting(
           model.Device.Data(
                name='close_delay',
                type=model.Device.Data.Type.UINT16,
                value=5,
                description='Amount of time to wait (in seconds) before closing valve'
            )
        )

        # Latitudinal GPS coordinate
        self.save_setting(
           model.Device.Data(
                name='location_gps_lat',
                type=model.Device.Data.Type.FLOAT,
                value=5,
                description='Latitudinal GPS coordinate'
            )
        )

        # Longitudinal GPS coordinate
        self.save_setting(
           model.Device.Data(
                name='location_gps_lon',
                type=model.Device.Data.Type.FLOAT,
                value=5,
                description='Longitudinal GPS coordinate'
            )
        )

        ######################
        ## Initialize state ##
        ######################

        # Valve opened/closed
        self.save_state(
           model.Device.Data(
                name='valve',
                type=model.Device.Data.Type.STRING,
                value='opened',
                description='State of valve as opened/closed/stuck'
            )
        )

        # Motor opening/closing/resting
        self.save_state(
           model.Device.Data(
                name='motor',
                type=model.Device.Data.Type.STRING,
                value='resting',
                description='State of motor as opening/closing/resting'
            )
        )

        # Realtime motor current draw
        self.save_state(
           model.Device.Data(
                name='motor_current',
                type=model.Device.Data.Type.FLOAT,
                value=0.0,
                description='Current draw of motor (in Amps)'
            )
        )

        # Firmware version
        self.save_state(
           model.Device.Data(
                name='firmware_version',
                type=model.Device.Data.Type.STRING,
                value='4.0.0',
                description='Valve controller firmware version'
            )
        )

        # Probe1 wet true/false
        self.save_state(
           model.Device.Data(
                name='probe1_wet',
                type=model.Device.Data.Type.BOOLEAN,
                value=False,
                description='True if water detected at probe1'
            )
        )

        # Leak detectors that are paired to the valve controller.
        self.leak_detectors = []

        # Spawn simulation processes
        self._main_process = self._env.process(self.run())
        self._env.process(self.detect_leak())
        self._heartbeat_process = self.send_hearbeat()

    def generate_mac_addr(self):
        return "30AEA402" + generate.string(size=4)

    def run(self):
        """Simulates device transient operation.

        During normal operation the device can be interrupted
        by other simulation events.
        """

        while True:
            # Get event for message pipe
            packet = yield self._rf_recv_pipe.get()

            if packet.sent_at < self._env.now:
                # if message was already put into pipe, then
                # message_consumer was late getting to it. Depending on what
                # is being modeled this, may, or may not have some
                # significance
                logger.info('%s - received packet LATE - current time %d' % (self._instance_name, self._env.now))
                # logger.info(json.dumps(json.loads(packet[1])))
            else:
                # message_consumer is synchronized with message_generator
                logger.info('%s - received packet ON TIME - current time %d - data (after NL)\n%s' % (self._instance_name, self._env.now, packet.data))

            # Check if the sender is paired to the valve controller.
            if "sent_by" in packet.data:
                sent_by = packet.data["sent_by"]
                for ld in self.leak_detectors:
                    if ld._instance_name == sent_by:
                        # Check for event.
                        if "event" in packet.data:
                            event = packet.data["event"]
                            if event == "leak_detected":
                                logger.info("{valve} RECEIVED LEAK FROM {leak_detector}".format(valve=self._instance_name,
                                                                                                leak_detector=sent_by))
                        break

            continue
            # Turn off the valve, 5-10 seconds
            yield self._env.timeout(random.randint(5, 10))

    def add_leak_detector(self, leak_detector):
        """ Pairs a leak detector.
        
        Args:
            leak_detector (Leak_Detector) -- The new leak detector to be paired.
        """

        self.leak_detectors.append(leak_detector)

    def list_leak_detectors(self):
        """ Lists all leak detectors paired to a valve controller.
        """

        logger.log("Leak detectors paired to {valve}:".format(valve=self._instance_name))
        for ld in self.leak_detectors:
            logger.log("\t{leak_detector}".format(leak_detector=ld._instance_name))

    def send_hearbeat(self):
        """ Sends a heartbeat to show the valve controller is still online.
        """

        yield self._env.timeout(Valve.HEARTBEAT_PERIOD)

        packet = communication.Communicator.Packet(
            sent_at=self._env.now,
            created_at=str(datetime.datetime.now()),
            sent_by=self._metadata.mac_address,
            sent_to=self._metadata.mac_address,
            data='ping'
        )

        # Send
        self.transmit(communicators.rf.RF, packet)

    def set_heartbeat(self, new_heartbeat):
        """ Sets all valve controllers' heartbeat period.
        
        Args:
            new_heartbeat (UINT16) -- New heartbeat period in seconds.
        """
        
        Valve.HEARTBEAT_PERIOD = new_heartbeat
        logger.info("Set all valve controllers' heartbeat period to {new_value} seconds.".format(new_value=new_heartbeat))

    def update_probe(self, is_wet):
        """ Updates the probe's status.
        
        Args:
            is_wet (boolean) --
                True if the probe is wet.
                False if the probe is dry.
        
        Raises:
            TypeError -- is_wet is not a boolean.
        """

        if is_wet in [True, False]:
            value = self.get_state('probe1_wet')
            value = is_wet
        else:
            raise TypeError("A valve's probe status must either be True or False, not {received_value}".format(received_value=is_wet))

    def update_motor_action(self, new_state):
        """ Updates the motor's action status.
        
        Args:
            new_state (Valve.MotorState) -- The new motor action status.
        
        Raises:
            TypeError -- new_state is not a type of allowed motor state.
        """

        if new_state.lower() in [Valve.MotorState.opening.name, Valve.MotorState.closing.name, Valve.MotorState.resting.name]:
            value = self.get_state('motor').value
            value = new_state
        else:
            raise TypeError("Motor state must be {opening}, {closing}, {resting}, not {received_value}.".format(opening=Valve.MotorState.opening.name,
                                                                                                                closing=Valve.MotorState.closing.name,
                                                                                                                resting=Valve.MotorState.resting.name,
                                                                                                                received_value=new_state))

    def update_valve_status(self, new_status):
        """ Updates the valve's status.
        
        Args:
            new_status (Valve.ValveStatus) -- The new valve status.
        
        Raises:
            TypeError -- new_status is not a type of allowed valve status.
        """

        if new_status.lower() in [Valve.ValveStatus.opened.name, Valve.ValveStatus.closed.name, Valve.ValveStatus.stuck.name]:
            value = self.get_state('valve').value
            value = new_status
        else:
            raise TypeError("Valve status must be {opened}, {closed}, {stuck}, not {received_value}.".format(opened=Valve.ValveStatus.opened.name,
                                                                                                            closed=Valve.ValveStatus.closed.name,
                                                                                                            stuck=Valve.ValveStatus.stuck.name,
                                                                                                            received_value=new_status))

    def detect_leak(self):
        """ Occasionally triggers a leak.
        """

        while True:
            # yield self._env.timeout(random.expovariate(self.MEAN_LEAK_DETECTION_TIME))
            yield self._env.timeout(random.randint(1, 60))

            self.update_probe(is_wet=True)

            logger.warning(self._instance_name + ' LEAK DETECTED! CLOSING VALVE!')

            logger.info("{valve} MOTOR IS CLOSING!".format(valve=self._instance_name))
            self.update_motor_action(new_state=Valve.MotorState.closing.name)        
            # Wait 5 seconds for motor to close.
            yield self._env.timeout(5)

            total_percent_chance_to_stall = 100
            if random.randint(0, total_percent_chance_to_stall + 1) <= Valve.PERCENT_CHANCE_TO_STALL:
                self.stall()
                # Wait 2 minutes for a "person" to come fix the valve.
                yield self._env.timeout(Valve.STALL_TIME)
            else:
                self.close()

            self.update_motor_action(Valve.MotorState.opening.name)
            logger.info("{valve} MOTOR IS OPENING!".format(valve=self._instance_name))
            # Wait 5 seconds for motor to open.
            yield self._env.timeout(5)

            self.open()

    def stall(self):
        """ Stalls the valve controller.
        """

        self.update_valve_status(new_status=Valve.ValveStatus.stuck.name)
        logger.warning("{valve} STALLED!".format(valve=self._instance_name))

    def open(self):
        """ Opens the valve.
        """

        self.update_probe(is_wet=False)

        self.update_valve_status(Valve.ValveStatus.opened.name)
        logger.info("{valve} IS OPENED!".format(valve=self._instance_name))

    def close(self):
        """ Closes the valve.
        """

        self.update_valve_status(new_status=Valve.ValveStatus.closed.name)
        logger.info("{valve} CLOSED!".format(valve=self._instance_name))
