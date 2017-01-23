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
Test suite for module topology_openswitch.openswitch
"""

from __future__ import unicode_literals, absolute_import
from __future__ import print_function, division

from abc import ABCMeta, abstractmethod

from pytest import raises, warns
from six import add_metaclass

from topology.platforms.node import CommonNode
from topology_openswitch.openswitch import (
    OpenSwitchBase, WrongAttributeError, DeletedAttributeError
)


def test_wrong_attribute():
    """
    Test that the wrong attribute is found in the right classes.
    """

    @add_metaclass(ABCMeta)
    class Mixer(CommonNode, OpenSwitchBase):
        @abstractmethod
        def __init__(self, *args, **kwargs):
            super(Mixer, self).__init__(*args, **kwargs)

    class Child0(Mixer):
        _class_openswitch_attributes = {
            'child_0_0': 'child_0_0 doc',
            'child_0_1': 'child_0_1 doc'
        }

        def __init__(self, identifier, child_0_1):
            self._child_0_0 = 'child_0_0'
            self._child_0_1 = child_0_1
            super(Child0, self).__init__(identifier)

        def _get_services_address(self):
            pass

    class Child1(Mixer):
        def __init__(self, identifier):
            super(Child1, self).__init__(identifier)

        def _get_services_address(self):
            pass

    class Child2(Child1):
        _class_openswitch_attributes = {
            'child_2_0': 'child_2_0 doc',
        }

        def __init__(self, identifier):
            super(Child2, self).__init__(identifier)
            self._child_2_0 = 'child_2_0'

    class Child3(Child1):
        _class_openswitch_attributes = {
            'child_3_0': 'child_3_0 doc',
        }

        def __init__(self, identifier):
            super(Child3, self).__init__(identifier)
            self._child_3_0 = 'child_3_0'

    class Child4(Child2):
        _class_openswitch_attributes = {
            'child_4_0': 'child_4_0 doc',
        }

        def __init__(self, identifier):
            super(Child4, self).__init__(identifier)
            self._child_4_0 = 'child_4_0'

    @add_metaclass(ABCMeta)
    class Child5(Child4):
        _class_openswitch_attributes = {
            'child_5_0': 'child_5_0 doc',
        }

        @abstractmethod
        def __init__(self, identifier):
            super(Child5, self).__init__(identifier)
            self._child_5_0 = 'child_5_0'

    class Child6(Child5):
        _class_openswitch_attributes = {
            'child_6_0': 'child_6_0 doc',
        }

        def __init__(self, identifier):
            super(Child6, self).__init__(identifier)
            self._child_6_0 = 'child_6_0'

    child_0_0 = Child0('child_0_0', 'child_0_0_1')
    child_0_1 = Child0('child_0_1', 'child_0_1_1')
    child_1_0 = Child1('child_1_0')
    child_2_0 = Child2('child_2_0')
    child_2_1 = Child2('child_2_1')
    child_3_0 = Child3('child_3_0')
    child_4_0 = Child4('child_4_0')
    child_6_0 = Child6('child_6_0')

    assert child_6_0.child_5_0 == 'child_5_0'

    assert child_0_0.child_0_0 == 'child_0_0'
    assert child_0_1.child_0_0 == 'child_0_0'

    assert child_2_1.identifier == 'child_2_1'

    assert hasattr(child_3_0, 'child_3_0')

    assert hasattr(child_4_0, 'child_4_0')
    assert hasattr(child_4_0, 'child_2_0')

    assert child_4_0.child_2_0 == 'child_2_0'

    child_4_0.child_2_0 = 'child_2_0_4'

    assert child_2_0.child_2_0 == 'child_2_0'

    assert child_0_1.child_0_1 == 'child_0_1_1'

    child_0_1.child_0_0 = 'child_0_0_1'

    assert child_0_1.child_0_0 == 'child_0_0_1'

    assert child_0_0.child_0_0 == 'child_0_0'

    assert child_0_0.child_0_1 == 'child_0_0_1'

    with raises(WrongAttributeError) as error:
        child_1_0.child_0_0

    assert (
        'Attribute child_0_0 was not found in class '
        'test_topology_openswitch.Child1, this attribute is available in'
        ' test_topology_openswitch.Child0.'
    ) == str(error.value)

    with raises(WrongAttributeError):
        child_2_0.child_0_0

    with raises(AttributeError):
        child_1_0.child_0_2

    assert Child0.child_0_0.__doc__ == (
        Child0._class_openswitch_attributes[
            'child_0_0'
        ]
    )

    assert hasattr(child_3_0, 'child_3_0')

    del child_0_0.child_0_0

    with raises(DeletedAttributeError):
        child_0_0.child_0_0

    with warns(UserWarning):
        child_2_1.__del__()
