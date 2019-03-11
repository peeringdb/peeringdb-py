from functools import wraps
import inspect

import six

from peeringdb.resource import RESOURCES_BY_TAG

def reftag_to_cls(fn):
    """
    decorator that checks function arguments for `concrete` and `resource`
    and will properly set them to class references if a string (reftag) is
    passed as the value
    """
    names, _, _, values = inspect.getargspec(fn)
    @wraps(fn)
    def wrapped(*args, **kwargs):
        i = 0
        backend = args[0]
        for name in names[1:]:
            value = args[i]
            if name == "concrete" and isinstance(value, six.string_types):
                args[i] = backend.REFTAG_CONCRETE[value]
            elif name == "resource" and isinstance(value, six.string_types):
                args[i] = backend.REFTAG_RESOURCE[value]
            i += 1
        return fn(*args, **kwargs)
    return wrapped

class Field(object):
    """
    We use this to provide field instances to backends that
    don't use classes to describe their fields
    """

    def __init__(self, name):
        self.name = name
        self.column = column

class EmptyContext(object):

    """
    We use this to provide a dummy context wherever it's optional
    """

    def __enter__(self):
        pass
    def __exit__(self, *args):
        pass


class Base(object):

    """
    Backend base class.

    Do NOT extend this directly when implementing a new backend, instead
    extend Interface below.
    """

    # Handleref tag to resource class mapping
    REFTAG_RESOURCE = RESOURCES_BY_TAG

    @property
    def CONCRETE_MAP(self):
        if not hasattr(self, "_CONCRETE_MAP"):
            self._CONCRETE_MAP = {
                concrete: res for (res, concrete) in self.RESOURCE_MAP.items()}
        return self._CONCRETE_MAP

    def get_concrete(self, res):
        """
        returns the concrete class for the resource

        Returns:

            - concrete class
        """
        return self.RESOURCE_MAP[res]

    def is_concrete(self, cls):
        """
        check if concrete class exists in the resource -> concrete mapping

        Returns:

            - bool: True if class exists in the resource -> concrete mapping
        """
        return cls in self.CONCRETE_MAP

    def get_resource(self, cls):
        """
        returns the resource class for the concrete class

        Returns:

            - resource class
        """
        return self.CONCRETE_MAP[cls]


class Interface(Base):

    """
    backend adapter interface

    extend this when making a new backend
    """

    # Resource class to concrete class mapping
    # should go in here
    RESOURCE_MAP = {}

    # Handleref tag to concrete class mapping
    # should go in here
    REFTAG_CONCRETE = {}


    @classmethod
    def validation_error(cls, concrete=None):
        """
        should return the exception class that will
        be raised when an object fails validation

        Arguments:

            - concrete: if your backend has class specific validation
                errors and this is set, return the exception class that would be
                raised for this concrete class.

        Returns:

            - Exception class
        """
        return Exception


    @classmethod
    def object_missing_error(cls, concrete=None):
        """
        should return the exception class that will
        be raised when an object cannot be found

        Arguments:

            - concrete: if your backend has class specific object missing
                errors and this is set, return the exception class that would be
                raised for this concrete class.

        Returns:

            - Exception class
        """
        return Exception


    @classmethod
    def atomic_transaction(cls):
        """
        Allows you to return an atomic transaction context
        if your backend supports it, if it does not, leave as is

        This should never return None

        Returns:

            - python context instance
        """
        return EmptyContext()

    @classmethod
    def setup(cls):
        """
        operations that need to be done ONCE during runtime
        to prepare usage for the backend
        """
        pass


    # INTERFACE (REQUIRED)
    # The following methods are required to be overwritten in
    # your backend and will raise a NotImplementedError if
    # they are not.
    #
    # when overriding make sure you also apply the `reftag_to_cls`
    # decorator on the methods that need it

    @reftag_to_cls
    def create_object(self, concrete, **data):
        """
        should create object from dict and return it

        Arguments:

            - concrete: concrete class

        Keyword Arguments:

            - object field names -> values
        """
        raise NotImplementedError()


    #TODO:
    def delete_all(self):
        """
        Delete all objects, essentially empty the database
        """
        raise NotImplementedError()


    def detect_missing_relations(self, obj, exc):
        """
        Should parse error messages and collect the missing relationship
        errors as a dict of Resource -> {id set} and return it

        Arguments:

            - obj: concrete object instance
            - exc: exception instance

        Returns:

            - dict: {Resource : [ids]}
        """
        raise NotImplementedError()


    def detect_uniqueness_error(self, exc):
        """
        Should parse error message and collect any that describe violations
        of a uniqueness constraint.

        return the curresponding fields, else None

        Arguments:

            - exc: exception instance

        Returns:

            - list: list of fields
            - None: if no uniqueness errors
        """
        raise NotImplementedError()


    @reftag_to_cls
    def get_field_names(self, concrete):
        """
        Should return a list of field names for the concrete class

        Arguments:

            - concrete: concrete class

        Returns:

            - list: [<str>,...]
        """
        raise NotImplementedError()


    @reftag_to_cls
    def get_field_concrete(self, concrete, field_name):
        """
        Return concrete class for relationship by field name

        Arguments:

            - concrete: concrete class
            - field_name

        Returns:

            - concrete class
        """
        raise NotImplementedError()


    @reftag_to_cls
    def get_object(self, concrete, id):
        """
        should return instance of object with matching id

        Arguments:

            - concrete: concrete class
            - id: object primary key value

        Returns:

            - concrete instance
        """
        raise NotImplementedError()

    @reftag_to_cls
    def get_object_by(self, concrete, field_name, value):
        """
        very simply search function that should return
        collection of objects where field matches value

        Arguments:

            - concrete: concrete class
            - field_name: query this field for a match
            - value: match this value (simple equal matching)

        Returns:

            - concrete instance
        """
        raise NotImplementedError()

    @reftag_to_cls
    def get_objects(self, concrete, ids=None):
        """
        should return collection of objects

        Arguments:

            - concrete: concrete class
            - ids: if specified should be a list of primary
                key values and only objects matching those
                values should be returned

        Returns:

            - collection of concrete instances
        """
        raise NotImplementedError()

    @reftag_to_cls
    def get_objects_by(self, concrete, field, value):
        """
        very simple search function that should return
        collection of objects where field matches value

        Arguments:

            - concrete: concrete class
            - field_name: query this field for a match
            - value: match this value (simple equal matching)

        Returns:

            - collection of concrete instances
        """
        raise NotImplementedError()

    @reftag_to_cls
    def is_field_related(self, concrete, field_name):
        """
        Should return a tuple containing bools on whether
        a field signifies a relationship and if it's a single
        relationship or a relationship to multiple objects

        Arguments:

            - concrete: concrete class
            - field_name: query this field for a match

        Returns:

            - tuple: (bool related, bool many)
        """
        raise NotImplementedError()


    @reftag_to_cls
    def last_change(self, concrete):
        """
        should return unix epoch timestamp of the `updated` field
        of the most recently updated object

        Arguments:

            - concrete: concrete class

        Returns:

            - int
        """
        raise NotImplementedError()

    def save(self, obj):
        """
        Save the object instance

        Arguments:

            - obj: concrete object instance
        """
        raise NotImplementedError()

    def set_relation_many_to_many(self, obj, field_name, objs):
        """
        Setup a many to many relationship

        Arguments:

            - obj: concrete object instance
            - field_name: name of the field that holds the relationship
            - objs: collection of concrete objects to setup relationships with
        """
        raise NotImplementedError()

    def update(self, obj, field_name, value):
        """
        update field on a concrete instance to value

        this does not have to commit to the database, which will be
        handled separately via the `save` method.

        Arguments:

            - obj: concrete object instance
            - field_name
            - value
        """
        setattr(obj, field_name, value)

    ## INTERFACE (OPTIONAL / SITUATIONAL)

    @reftag_to_cls
    def get_field(self, concrete, field_name):
        """
        Should retrun a field instance, if your backend does not use
        classes to describe fields, leave this as is

        Arguments:

            - concrete: concrete class
            - field_name

        Returns:

            - field instance
        """
        return Field(field_name)

    @reftag_to_cls
    def get_fields(self, concrete):
        """
        Should return a collection of fields, if your backend does not
        use classes to describe fields, leave this as is

        Arguments:

            - concrete: concrete class

        Returns:

            - collection of field instances
        """
        return [Field(name) for name in self.field_names(concrete)]


    def clean(self, obj):
        """
        Should take an object instance and validate / clean it

        Arguments:

            - obj: concrete object instance
        """
        pass

    @reftag_to_cls
    def convert_field(self, concrete, field_name, value):
        """
        Should take a value and a field definition and do a value
        conversion if needed.

        should return the new value.

        Arguments:

            - concrete: concrete class
            - field_name
            - value
        """
        pass

    def migrate_database(self, verbosity=0):
        """
        Do database migrations

        Arguments:

            - verbosity <int>: arbitrary verbosity setting, 0 = be silent,
                1 = show some info about migrations.
        """
        pass

    def is_database_migrated(self, **kwargs):
        """
        Should return whether the database is fully migrated

        Returns:

            - bool
        """
        return True


