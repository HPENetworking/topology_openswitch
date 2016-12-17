# -*- coding: utf-8 -*-
#
# Copyright (C) 2016 Hewlett Packard Enterprise Development LP
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
Test suite for module topology_openswitch.
"""

from __future__ import unicode_literals, absolute_import
from __future__ import print_function, division

from pytest import raises

from topology_openswitch.openswitch import OpenSwitch, WrongAttributeError


def test_wrong_attribute():
    """
    Test that the wrong attribute is found in the right classes.
    """

    class Child0(OpenSwitch):
        def __init__(self, child_0_only_1):
            self._child_0_only_0 = 9
            self._child_0_only_1 = child_0_only_1

        @property
        def child_0_only_0(self):
            return self._child_0_only_0

        @child_0_only_0.setter
        def child_0_only_0(self, child_0_only_0):
            self._child_0_only_0 = child_0_only_0

        @property
        def child_0_only_1(self):
            return self._child_0_only_1

        @child_0_only_1.setter
        def child_0_only_1(self, child_0_only_1):
            self._child_0_only_1 = child_0_only_1

        def _get_services_address(self):
            pass

    class Child1(OpenSwitch):
        def __init__(self):
            pass

        def _get_services_address(self):
            pass

    class Child2(Child1):
        pass

    child_0 = Child0('child_0_only_1')
    child_1 = Child1()
    child_2 = Child2()

    assert child_0.child_0_only_0 == 9
    assert child_0.child_0_only_1 == 'child_0_only_1'

    with raises(WrongAttributeError):
        child_1.child_0_only_0

    with raises(WrongAttributeError):
        child_2.child_0_only_0

    with raises(AttributeError):
        child_1.child_0_only_2
