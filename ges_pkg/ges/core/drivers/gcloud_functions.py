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

import requests
import json
import logging

# Define logger
logger = logging.getLogger(__name__)

# TODO: Remove from VCS
ENDPOINT = "https://us-central1-guardian-ecoystem-simulator.cloudfunctions.net/{function_name}"

def call_function(name: str, data: dict):
    try:
        logger.info('Calling cloud function %s with data: %s' % (name, data))
        r = requests.post(url=ENDPOINT.format(function_name=name), data=json.dumps(data))
    except Exception as e: # TODO: Handle specific exceptions
        logger.warn('Could not call cloud function (error: %s)' % str(e))
    else:
        logger.warn('Cloud function called, result: %s' % str(r.content))

def process(raw_msg: str):
    """Parse raw message and call relevant cloud function.
    """
    logger.info("received raw packet: %s" % raw_msg)
    call_function('test_function', {"message": "hello!"})
