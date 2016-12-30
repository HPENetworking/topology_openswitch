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

from abc import ABCMeta, abstractmethod

from six import add_metaclass


class WrongAttributeError(Exception):
    """
    Custom exception to be raised when a wrong attribute is requested.

    This exception will be raised when an attempt is done to access an
    attribute that is not present in the object but is present in other class
    that is child of OpenSwitch.

    :param str attribute: Attribute that was not found
    :param str class_name: Class that was missing the attribute
    :param list subclasses: List of class names that have the attribute
    """

    def __init__(self, attribute, class_name, subclasses):
        self._attribute = attribute
        self._class_name = class_name
        self._subclasses = subclasses

    def __str__(self):
        subclasses = ''

        for subclass in self._subclasses[:-1]:
            subclasses = '{}{}'.format(
                subclasses, '{}, '.format(subclass)
            )

        subclasses = '{}{}'.format(
            subclasses, self._subclasses[-1]
        )

        return (
            'Attribute {} was not found in class {}, this attribute is'
            ' available in {}.'
        ).format(self._attribute, self._class_name, subclasses)


class DeletedAttributeError(Exception):
    """
    Custom exception to be raised when a requested attribute is not present in
    the instance but is present in the class.

    It is assumed here that these situations happen when the attribute has been
    deleted with ``del instance.attribute``.

    :param str attribute: Attribute that was not found
    """

    def __init__(self, attribute):
        self._attribute = attribute

    def __str__(self):
        return (
            'Attribute {} was not present in the instance but is present in'
            ' the class. Has it been deleted?'
        )


class _MetaOpenSwitch(type):

    def __call__(self, *args, **kwargs):

        def getattribute(attr):
            def internal(salf):
                if attr not in salf._attribute_record:
                    salf._attribute_record.append(attr)

                return getattr(salf, '_{}'.format(attr))
            return internal

        for attr, docstring in self._openswitch_attributes.items():
            setattr(
                self, attr, property(
                    getattribute(attr),
                    (
                        lambda attr: lambda salf, value: setattr(
                            salf, '_{}'.format(attr), value
                        )
                    )(attr),
                    (
                        lambda attr: lambda salf: delattr(
                            salf, '_{}'.format(attr)
                        )
                    )(attr),
                    docstring
                )
            )

        return super(_MetaOpenSwitch, self).__call__(*args, **kwargs)


class _ABCMetaMetaOpenSwitch(ABCMeta, _MetaOpenSwitch):
    _openswitch_attributes = {}


@add_metaclass(_ABCMetaMetaOpenSwitch)
class OpenSwitch(object):
    """
    topology_openswitch abstract node.

    This node is not to be instantiated nor it is intended to work with any
    platform engine as it is. It is only a place where common code for the
    different implementations of the different OpenSwitch nodes may be.

    This class makes it possible to detect if an attribute of a subclass does
    not belong to it but to another one. If that happens, a WrongAttributeError
    exception will be raised to let the use know of this situation.
    All the attributes of the subclasses of this class should be properties.

    See :class:`topology.base.CommonNode` for more information.
    """

    _openswitch_attrs = {}

    @abstractmethod
    def __init__(self):
        self._attribute_record = []

        super(OpenSwitch, self).__init__()

    @classmethod
    def _find_attribute(cls, name, class_name):
        """
        Recursively find an attribute in the subclasses of OpenSwitch.

        This method raises an WrongAttribtueError exception if the attribute is
        not present in the object but belongs to other class.

        :param str name: The attribute to look for
        :param str class_name: The name of the class where the attribute was
         not found
        """
        if cls == OpenSwitch:
            subclasses = cls._get_all_subclasses()

            subclasses_with_attribute = []

            for subclass in subclasses:
                if name in subclass.__dict__.keys():
                    subclasses_with_attribute.append(subclass.__name__)

            if subclasses_with_attribute:
                raise WrongAttributeError(
                    name, class_name, subclasses_with_attribute
                )

        else:
            cls.__bases__[0]._find_attribute(name, class_name)

    def __getattr__(self, name):
        """
        Attempt to find the missing attribute in another class.

        This method is called when the attribute is not found, and it triggers
        a search for a class that actually has this attribute.
        """
        if name in self.__class__.__dict__.keys():
            raise DeletedAttributeError(name)
        self.__class__._find_attribute(name, self.__class__.__name__)

        return self.__getattribute__(name)

    @classmethod
    def _get_all_subclasses(cls):
        """
        Recursively finds all the subclasses of this class.

        :param type cls: A class to search for subclasses
        :rtype: list
        :return: A list of the name of all the subclasses of this class
        """
        subclasses = cls.__subclasses__()
        subsubclasses = []

        for subclass in subclasses:
            subsubclasses.extend(subclass._get_all_subclasses())

        subclasses.extend(subsubclasses)

        return subclasses

    def __del__(self):
        pass
        # FIXME: Implement search for parent attributes here.


__all__ = ['OpenSwitch', 'WrongAttributeError']
__author__ = 'Hewlett Packard Enterprise Development LP'
__email__ = 'hpe-networking@lists.hp.com'
__version__ = '0.1.0'