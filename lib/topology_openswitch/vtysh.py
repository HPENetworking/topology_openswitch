# -*- coding: utf-8 -*-
#
# Copyright (C) 2015-2016 Hewlett Packard Enterprise Development LP
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.

"""
topology_openswitch node module
"""

from __future__ import unicode_literals, absolute_import
from __future__ import print_function, division

from logging import warning
from re import match
from time import sleep
from logging import getLogger

from pexpect import EOF

from topology.platforms.shell import PExpectBashShell

log = getLogger(__name__)

# Regular expression template that matches a vtysh prompt along with its
# context
_VTYSH_PROMPT_TPL = r'(\r\n)?{}(\([-\w\s]+\))?[#>] '

# Prompt value that is set with set prompt
_VTYSH_FORCED = 'X@~~==::VTYSH_PROMPT::==~~@X'

# Regular expression that matches with values that may be found in unset vtysh
# prompts
_VTYSH_STANDARD = '[-\w]+'

# A bash prompt may be found in an unset value too, this regular expression
# matches that kind of prompts:
BASH_STANDARD_PROMPT = r'(\r\n)?root@[-\w]+:~# '
# The prompt can change on rbac enabled images
BASH_NONROOT_PROMPT = r'(\r\n)?[-\w]+:~\$ '
# Prompt value that is set in the bash prompt
BASH_FORCED_PROMPT = PExpectBashShell.FORCED_PROMPT

VTYSH_FORCED_PROMPT = _VTYSH_PROMPT_TPL.format(_VTYSH_FORCED)
VTYSH_STANDARD_PROMPT = _VTYSH_PROMPT_TPL.format(_VTYSH_STANDARD)


class VtyshError(Exception):
    """
    Generic class for all vtysh crash errors
    """

    _error_message = None

    def __init__(self, command):
        self._command = command

    def __str__(self):
        return '{} received when executing "{}"'.format(
            self._error_message,
            self._command
        )


class UnknownError(VtyshError):
    """
    Represents an unknown error

    This exception is to be raised when there is a vtysh crash that returns
    an unknown error message
    """

    def __init__(self, command, error_message):
        super(UnknownError, self).__init__(command)

        self._error_message = error_message


# This allows the user to only have to worry of adding the error messages here,
# the classes and the insertion of their symbols in this module will be done in
# a completely automatic way.
_ERROR_MESSAGES = [
    'Segmentation fault',
    'Illegal instruction error',
    'Aborted',
    'Floating point exception error',
    'Quit'
]

_ERROR_CLASSES = {
    error_message: type(
        ''.join([error_message.title().replace(' ', ''), 'Error']),
        (VtyshError, ),
        {'_error_message': error_message}
    ) for error_message in _ERROR_MESSAGES
}


class VtyshShellMixin(object):
    """
    Mixin for the ``vtysh`` shell
    """

    def _handle_crash(self, connection=None):
        """
        Handle all known vtysh crashes with a proper exception.

        This method will raise a proper exception if a vtysh crash is detected.
        If no crash is detected, it will do nothing. Because of this, the call
        of send_command of the nodes that use this method should be done inside
        a try/except block and this method called in the latter part. A call to
        raise should follow the call of this method to raise the original
        exception if a vtysh crash cannot be detected.

        :param str connection: The connection in which to handle a crash
        """

        spawn = self._get_connection(connection)

        # One necessary condition to detect a segmentation fault error is
        # to detect a forced bash prompt being matched.
        before = spawn.before.decode(
            encoding=self._encoding, errors=self._errors
        )

        error_bash_prompt_re = r'.*\n(?P<error>{})\n{}'

        error_bash_prompt_match = match(
            error_bash_prompt_re.format(
                '|'.join(_ERROR_MESSAGES), BASH_FORCED_PROMPT
            ), before
        )

        if error_bash_prompt_match is not None:
            raise _ERROR_CLASSES[error_bash_prompt_match.group('error')](
                self._last_command
            )

        bash_prompt_match = match(
            error_bash_prompt_re.format(r'.*', BASH_FORCED_PROMPT)
        )

        if bash_prompt_match is not None:
            raise UnknownError(
                self._last_command, bash_prompt_match.group('error')
            )

    def _determine_set_prompt(self, connection=None):
        """
        This method determines if the vtysh command ``set prompt`` exists.

        This method starts wit a call to sendline and finishes with a call
        to expect.

        :rtype: bool
        :return: True if vtysh supports the ``set prompt`` command, False
         otherwise.
        """
        spawn = self._get_connection(connection)

        # When a segmentation fault error happens, the message
        # "Segmentation fault" shows up in the terminal and then and EOF
        # follows, making the vtysh shell to close ending up in the bash
        # shell that opened it.

        # This starts the vtysh shell in a mode that forces the shell to
        # always return the produced output, even if an EOF exception
        # follows after it. This is done to handle the segmentation fault
        # errors.

        attempts = 10

        for i in range(attempts):
            try:
                spawn.sendline('stdbuf -oL vtysh')
                index = spawn.expect(
                    [VTYSH_STANDARD_PROMPT, BASH_FORCED_PROMPT], timeout=30
                )
                if index == 0:
                    break
                elif index == 1:
                    log.warning(
                        'Unable to start vtysh, received output: {}'.format(
                            spawn.before.decode('utf-8', errors='ignore')
                        )
                    )
                    continue
                else:
                    raise Exception(
                        'Unexpected match received: {}'.format(index)
                    )
            except Exception as error:
                raise Exception(
                    'Unable to connect to vytsh after {} attempts, '
                    'last output received: {}'.format(
                        attempts,
                        spawn.before.decode('utf-8', errors='ignore')
                    )
                ) from error

        # The newer images of OpenSwitch include this command that changes
        # the prompt of the shell to an unique value. This is done to
        # perform a safe matching that will match only with this value in
        # each expect.
        for attempt in range(0, 10):
            spawn.sendline('set prompt {}'.format(_VTYSH_FORCED))
            index = spawn.expect([VTYSH_STANDARD_PROMPT, VTYSH_FORCED_PROMPT])

            # If the image does not set the prompt immediately, wait and retry
            if index == 0:
                sleep(1)

            else:
                # Since it is not possible to know beforehand if the image
                # loaded in the node includes the "set prompt" command, an
                # attempt to match any of the following prompts is done. If the
                # command does not exist, the shell will return an standard
                # prompt after showing an error message.
                return bool(index)

        return False

    def _exit(self):
        """
        Attempt a clean exit from the shell

        This is necessary to enable the gathering of coverage information in
        the vtysh module.
        """
        for connection in self._connections.keys():
            try:
                # This is done to handle calls to the hostname command that
                # change this prompt
                self.send_command(
                    'end', silent=True, connection=connection, matches=[
                        _VTYSH_PROMPT_TPL.format('[-\w]+')
                    ]
                )

                self.send_command(
                    'exit', silent=True, connection=connection, matches=[
                        EOF, BASH_FORCED_PROMPT
                    ]
                )

            except Exception as error:
                warning(
                    'Exiting the vtysh self connection {} failed with this'
                    ' error: {}'.format(connection, str(error))
                )


__all__ = [
    'VTYSH_FORCED_PROMPT',
    'VTYSH_STANDARD_PROMPT',
    'BASH_FORCED_PROMPT',
    'BASH_STANDARD_PROMPT',
    'VtyshShellMixin',
    'VtyshError',
    'UnknownError'
]


# Here the names of the vtysh error classes are inserted in the globals
# dictionary to make them importable from this module directly.
for error_class in _ERROR_CLASSES.values():
    globals()[error_class.__name__] = error_class
    __all__.append(error_class.__name__)
