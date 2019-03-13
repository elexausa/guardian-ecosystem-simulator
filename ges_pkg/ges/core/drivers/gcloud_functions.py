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

# TODO: Remove from VCS
ENDPOINT = "https://us-central1-guardian-ecoystem-simulator.cloudfunctions.net/{function_name}"

def call_function(name: str, data: dict):
    try:
        logging.info('Calling cloud function %s with data: %s' % (name, data))
        r = requests.post(url=ENDPOINT.format(function_name=name), data=json.dumps(data))
    except Exception as e: # TODO: Handle specific exceptions
        logging.warn('Could not call cloud function (error: %s)' % str(e))
    else:
        logging.warn('Cloud function called, result: %s' % str(r))

def process(raw_msg: str):
    """Parse raw message and call relevant cloud function.
    """
    pass
