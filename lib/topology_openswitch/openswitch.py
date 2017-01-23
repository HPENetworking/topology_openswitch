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
from warnings import warn

from six import add_metaclass


class WrongAttributeError(Exception):
    """
    Custom exception to be raised when a wrong attribute is requested.

    This exception will be raised when an attempt is done to access an
    attribute that is not present in the object but is present in other class
    that is child of OpenSwitch.

    :param str attribute: Attribute that was not found
    :param class lacking_class: Class that was missing the attribute
    :param list having_classes: List of concrete classes names that have the
     attribute
    """

    def __init__(self, attribute, lacking_class, having_classes):
        self._attribute = attribute
        self._lacking_class = lacking_class
        self._having_classes = having_classes
        super(WrongAttributeError, self).__init__()

    def __str__(self):

        def module_name(class_):
            return '{}.{}'.format(class_.__module__, class_.__name__)

        having_classes = ''

        for having_class in self._having_classes[:-1]:
            having_classes = '{}{}'.format(
                having_classes, module_name(having_class)
            )

        last_having_class = self._having_classes[-1]
        having_classes = '{}{}'.format(
            having_classes,
            module_name(last_having_class)
        )

        return (
            'Attribute {} was not found in class {}, this attribute is'
            ' available in {}.'
        ).format(
            self._attribute, module_name(self._lacking_class), having_classes
        )


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
        super(DeletedAttributeError, self).__init__()

    def __str__(self):
        return (
            'Attribute {} was not present in the instance but is present in'
            ' the class. Has it been deleted?'
        )


class _MetaOpenSwitch(type):

    def __init__(self, *args, **kwargs):

        def getattribute(attr):
            def internal(salf):
                if attr not in salf._attribute_record:
                    salf._attribute_record.add(attr)

                return getattr(salf, '_{}'.format(attr))
            return internal

        for attr, docstring in self._class_openswitch_attributes.items():
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


class _ABCMetaMetaOpenSwitch(ABCMeta, _MetaOpenSwitch):
    pass


@add_metaclass(_ABCMetaMetaOpenSwitch)
class OpenSwitchBase(object):
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
    _class_openswitch_attributes = {}

    @abstractmethod
    def __init__(self, *args, **kwargs):
        self._attribute_record = set()

        super(OpenSwitchBase, self).__init__(*args, **kwargs)

    @classmethod
    def _find_attribute(cls, name, lacking_class):
        """
        Recursively find an attribute in the subclasses of OpenSwitch.

        This method raises an WrongAttribtueError exception if the attribute is
        not present in the object but belongs to other class.

        :param str name: The name of the attribute to look for
        :param class lacking_class: The class where the attribute was not found
        """
        if cls == OpenSwitchBase:
            subclasses = [
                subclass for subclass in cls._get_all_subclasses() if not (
                    subclass.__dict__.get('__abstractmethods__', False)
                )
            ]

            subclasses_with_attribute = []

            for subclass in subclasses:
                if name in subclass.__dict__.keys():
                    subclasses_with_attribute.append(subclass)

            if subclasses_with_attribute:
                raise WrongAttributeError(
                    name, lacking_class, subclasses_with_attribute
                )

        else:
            for base in cls.__bases__:
                if issubclass(base, OpenSwitchBase):
                    base._find_attribute(name, lacking_class)

    def __getattr__(self, name):
        """
        Attempt to find the missing attribute in another class.

        This method is called when the attribute is not found, and it triggers
        a search for a class that actually has this attribute.
        """
        if name in self.__class__.__dict__.keys():
            raise DeletedAttributeError(name)
        self.__class__._find_attribute(name, self.__class__)

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

    @classmethod
    def _find_class(cls, attributes):
        """
        Raise a warning if parent class has all attributes used in the test.

        This is done to inform the user that an unnecessarily specific node is
        being used in the test case.

        :param: set attributes: Node attributes used in the test
        :rtype: class
        :return: The highest class that has all the attributes in the test
        """

        for parent in cls.__bases__:
            if (
                not issubclass(parent, OpenSwitchBase)
            ) or parent.__dict__.get('__abstractmethods__', False):
                continue
            if parent == OpenSwitchBase:
                return cls
            if attributes.issubset(set(parent.__dict__.keys())):
                return parent._find_class(attributes)
        else:
            return cls

    def __del__(self):
        higher_class = self.__class__._find_class(self._attribute_record)

        if higher_class != self.__class__:
            warn(
                '{} should be instantiated using class {}.{}'.format(
                    self.identifier,
                    higher_class.__module__,
                    higher_class.__name__
                ),
                UserWarning
            )


__all__ = ['OpenSwitchBase', 'WrongAttributeError']
__author__ = 'Hewlett Packard Enterprise Development LP'
__email__ = 'hpe-networking@lists.hp.com'
__version__ = '0.1.0'
