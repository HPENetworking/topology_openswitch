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
from re import search, match

from pexpect import EOF

from topology.platforms.shell import PExpectBashShell

# Regular expression template that matches a vtysh prompt along with its
# context
_VTYSH_PROMPT_TPL = r'(\r\n)?{}(\([-\w\s]+\))?[#>] '

# Prompt value that is set with set prompt
_VTYSH_FORCED = 'X@~~==::VTYSH_PROMPT::==~~@X'

# Regular expression that matches with values that may be found in unset vtysh
# prompts
_VTYSH_STANDARD = 'switch'

# A bash prompt may be found in an unset value too, this regular expression
# matches that kind of prompts:
BASH_STANDARD_PROMPT = r'(\r\n)?root@[-\w]+:~# '
# Prompt value that is set in the bash prompt
BASH_FORCED_PROMPT = PExpectBashShell.FORCED_PROMPT

VTYSH_FORCED_PROMPT = _VTYSH_PROMPT_TPL.format(_VTYSH_FORCED)
VTYSH_STANDARD_PROMPT = _VTYSH_PROMPT_TPL.format(_VTYSH_STANDARD)


class _VtyshError(Exception):
    """
    Pass.
    """
    _crash_message = None

    def __init__(self, command):
        self._command = command

    def __str__(self):
        return '{} received when executing "{}"'.format(
            self._crash_message,
            self._command
        )


class SegmentationFaultError(_VtyshError):
    """
    Pass
    """
    _crash_message = 'Segmentation fault'


class IllegalInstructionErrorError(_VtyshError):
    """
    Pass
    """
    _crash_message = 'Illegal instruction error'


class AbortedError(_VtyshError):
    """
    Pass
    """
    _crash_message = 'Aborted'


class FloatingPointExceptionErrorError(_VtyshError):
    """
    Pass
    """
    _crash_message = 'Floating point exception error'


class QuitError(_VtyshError):
    """
    Pass
    """
    _crash_message = 'Quit'


class VtyshShellMixin(object):
    """
    Mixin for the ``vtysh`` shell
    """

    def _handle_crash(self, connection=None):
        """
        Handle all known vtysh crashes with a proper exception.

        :param str connection: The connection in which to handle a crash
        """

        spawn = self._get_connection(connection)

        errors = [
            SegmentationFaultError,
            IllegalInstructionErrorError,
            AbortedError,
            FloatingPointExceptionErrorError,
            QuitError
        ]

        crash_messages = [getattr(error, '_crash_message') for error in errors]

        # To find out if a segmentation fault error was produced, a search for
        # the "Segmentation fault" string in the output of the command is done.
        crash = search(
            '|'.join(crash_messages), self.get_response(silent=True)
        )

        # The other necessary condition to detect a segmentation fault error is
        # to detect a forced bash prompt being matched.
        forced_bash_prompt = match(
            BASH_FORCED_PROMPT, spawn.after.decode(
                encoding=self._encoding, errors=self._errors
            )
        )

        # This exception is raised to provide a meaningful error to the user.
        if crash and forced_bash_prompt is not None:
            raise errors[crash](self._last_command)

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
        spawn.sendline('stdbuf -oL vtysh')
        spawn.expect(VTYSH_STANDARD_PROMPT)

        # The newer images of OpenSwitch include this command that changes
        # the prompt of the shell to an unique value. This is done to
        # perform a safe matching that will match only with this value in
        # each expect.
        spawn.sendline('set prompt {}'.format(_VTYSH_FORCED))
        index = spawn.expect([VTYSH_STANDARD_PROMPT, VTYSH_FORCED_PROMPT])

        # Since it is not possible to know beforehand if the image loaded
        # in the node includes the "set prompt" command, an attempt to
        # match any of the following prompts is done. If the command does
        # not exist, the shell will return an standard prompt after showing
        # an error message.
        return bool(index)

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
    'SegmentationFaultError',
    'IllegalInstructionErrorError',
    'AbortedError',
    'FloatingPointExceptionErrorError',
    'QuitError',
]
