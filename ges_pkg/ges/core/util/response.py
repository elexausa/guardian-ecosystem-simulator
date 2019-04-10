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

import typing
from enum import Enum

class Error(str, Enum):
    GENERIC = "Generic error"
    SIMULATION_RUNNING = "Simulation running"
    DOES_NOT_EXIST = "Specified object does not exist"

def construct_response(data: dict = None, error_codes: typing.List = None):
    """Constructs full JSON response packet from provided information.

    .. highlight:: json

        {
            "status": "ok/error",
            "errors": [
                {
                    "code": "Error (enum)"
                    "detail": "Detail about error code"
                }
            ],
            "data": data
        }

    :param status: Status code of
    :param error_codes: Error codes to attach to the response, if none, the "error" key is not
                        appended to the packet.

    :type data: dict
    :type error_codes: list(:class:`Error`) or list(tuple(:class:`Error`, "error code message override"))

    :return: Response
    :rtype: dict
    """
    # Create packet
    response = {}

    # Add data if it exists
    if data is not None:
        response["data"] = data

    # Handle error codes
    if type(error_codes) is list and len(error_codes) > 0:
        # Status ERROR
        response["status"] = "error"

        # Create errors list
        errors = []

        # Handle errors
        if type(error_codes[0]) is Error:
            # If true, assume list is full of Errors and append all
            for error_code in error_codes:
                errors.append(construct_error(code=error_code))
        elif type(error_codes[0]) is tuple:
            # If true, assume list is full of tuples in (Error, message override) form
            for error_code in error_codes:
                errors.append(construct_error(code=error_code[0], msg_override=error_code[1]))

        # Add to object
        response["errors"] = errors
    else:
        # Status OK
        response["status"] = "ok"

    # Return object
    return response

def construct_error(code: Error = Error.GENERIC, msg_override: str = None):
    """Constructs an error object with detailed information from the provided response code.

    .. highlight:: json

        {
            code: code,
            message: "Detail about the error code"
        }

    :param code: The code to construct the error from
    :param msg_override: If defined, overrides the default error detail message.

    :type code: :class:`Error`
    :type msg_override: str

    :returns: Wrapped error and detail
    :rtype: dict
    """
    # Create initial error object
    error = {}
    error["code"] = code.name

    # Apply override message if set
    if type(msg_override) is str:
        error["detail"] = msg_override
    else:
        error["detail"] = code.value

    # Return error object
    return error
