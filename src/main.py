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

import datetime
import random
import time
import json
import simpy
import os
import logging

from gds import core
from gds.devices.Valve import Valve, DyingCow

RANDOM_SEED = time.time()

# def message_generator():
#     """A process which randomly generates messages."""
#     while True:
#         # wait for next transmission
#         yield core.ENV.timeout(random.randint(6, 10))
#         msg = (core.ENV.now, "{'sent_at':'%d','content':'%s'}" % (core.ENV.now, 'my content here'))
#         logging.warning("message_generator(): " + str(msg))

if __name__ == "__main__":
    # Configure logger
    logging.basicConfig(
        level=logging.INFO,
        format='PID-%(process)d,%(levelname)s,%(asctime)s: %(message)s'
    )

    # Seed random
    random.seed(RANDOM_SEED)

    # Record start time
    starttime = datetime.datetime.now()

    try:
        # Create valves
        valves = {}

        for i in range(10):
            v = Valve()
            valves[v._instance_name] = v
            print(v.dump_json())

        # for valve_id, valve in valves.items():
        #     logging.info('%s:\n%s' % (valve_id, valve.dump_json()))

        # Throw in some dying cows
        dying_cows = [('cow_%d' % i, DyingCow.spawn("Moo-er #%d" % i)) for i in range(10000)]

        # for cow_id, cow in dying_cows:
        #     logging.info('%s:\n%s' % (cow_id, cow.dump_json()))

        # Start simulation
        logging.info("Starting simulation...")
        core.ENV.run()

    except (KeyboardInterrupt, SystemExit):
        logging.warning("Simulation shutting down!")

        # Calculate duration
        duration = round((datetime.datetime.now() - starttime).total_seconds())

        # Clean exit
        print("\n")
        logging.info("Simulation exited. Total duration: " + str(duration) + " seconds")