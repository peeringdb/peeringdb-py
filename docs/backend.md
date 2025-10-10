# How to configure
The object-relational mapping backend can be configured with the `orm.backend` config parameter. For example, in YAML:

    orm:
      backend: django_peeringdb
      database:
        engine: sqlite3
        name: peeringdb.sqlite3

The only currently available backend module is for Django, `django_peeringdb`. Other backends may be supported in the future as needed.

To install the Django backend:

    pip install django_peeringdb

Make sure that the backend module is configured properly.

# Backend interface
A custom module can be defined by implementing the following methods and types, as well as pointing `peeringdb` to a module containing a `load_backend(**kwargs)` method which returns the implementation module as an object. For example:

    peeringdb.SUPPORTED_BACKENDS["new_backend"] = "my_app.peeringdb_adaptor_module"
    conf = peeringdb.config.load_config("~/new_orm_config/")
    client = peeringdb.PeeringDB(conf)

In your PeeringDB config file:

    orm:
        backend: new_backend
        database:
            ...

In `my_app/peeringdb_adaptor_module.py`:

    import impl_module as impl

    # or:
    # class Backend: ...
    # impl = Backend()

    def load_backend(**options):
        impl.configure(options)
        return impl

The requirements on a backend adaptor class are outlined below.

### Interface

```
Interface(peeringdb.backend.Base)
```

backend adapter interface

extend this when making a new backend

#### is_field_related

```
is_field_related(*args, **kwargs)
```

Should return a tuple containing bools on whether
a field signifies a relationship and if it's a single
relationship or a relationship to multiple objects

Arguments:

    - concrete: concrete class
    - field_name: query this field for a match

Returns:

    - tuple: (bool related, bool many)

#### get_field_names

```
get_field_names(*args, **kwargs)
```

Should return a list of field names for the concrete class

Arguments:

    - concrete: concrete class

Returns:

    - list: [<str>,...]

#### create_object

```
create_object(*args, **kwargs)
```

should create object from dict and return it

Arguments:

    - concrete: concrete class

Keyword Arguments:

    - object field names -> values

#### get_object

```
get_object(*args, **kwargs)
```

should return instance of object with matching id

Arguments:

    - concrete: concrete class
    - id: object primary key value

Returns:

    - concrete instance

#### convert_field

```
convert_field(*args, **kwargs)
```

Should take a value and a field definition and do a value
conversion if needed.

should return the new value.

Arguments:

    - concrete: concrete class
    - field_name
    - value

#### update

```
update(self, obj, field_name, value)
```

update field on a concrete instance to value

this does not have to commit to the database, which will be
handled separately via the `save` method.

Arguments:

    - obj: concrete object instance
    - field_name
    - value

#### get_field_concrete

```
get_field_concrete(*args, **kwargs)
```

Return concrete class for relationship by field name

Arguments:

    - concrete: concrete class
    - field_name

Returns:

    - concrete class

#### get_objects_by

```
get_objects_by(*args, **kwargs)
```

very simple search function that should return
collection of objects where field matches value

Arguments:

    - concrete: concrete class
    - field_name: query this field for a match
    - value: match this value (simple equal matching)

Returns:

    - collection of concrete instances

#### migrate_database

```
migrate_database(self, verbosity=0)
```

Do database migrations

Arguments:

    - verbosity <int>: arbitrary verbosity setting, 0 = be silent,
        1 = show some info about migrations.

#### get_object_by

```
get_object_by(*args, **kwargs)
```

very simply search function that should return
collection of objects where field matches value

Arguments:

    - concrete: concrete class
    - field_name: query this field for a match
    - value: match this value (simple equal matching)

Returns:

    - concrete instance

#### detect_uniqueness_error

```
detect_uniqueness_error(self, exc)
```

Should parse error message and collect any that describe violations
of a uniqueness constraint.

return the curresponding fields, else None

Arguments:

    - exc: exception instance

Returns:

    - list: list of fields
    - None: if no uniqueness errors

#### set_relation_many_to_many

```
set_relation_many_to_many(self, obj, field_name, objs)
```

Setup a many to many relationship

Arguments:

    - obj: concrete object instance
    - field_name: name of the field that holds the relationship
    - objs: collection of concrete objects to setup relationships with

#### get_fields

```
get_fields(*args, **kwargs)
```

Should return a collection of fields, if your backend does not
use classes to describe fields, leave this as is

Arguments:

    - concrete: concrete class

Returns:

    - collection of field instances

#### detect_missing_relations

```
detect_missing_relations(self, obj, exc)
```

Should parse error messages and collect the missing relationship
errors as a dict of Resource -> {id set} and return it

Arguments:

    - obj: concrete object instance
    - exc: exception instance

Returns:

    - dict: {Resource : [ids]}

#### get_objects

```
get_objects(*args, **kwargs)
```

should return collection of objects

Arguments:

    - concrete: concrete class
    - ids: if specified should be a list of primary
        key values and only objects matching those
        values should be returned

Returns:

    - collection of concrete instances

#### clean

```
clean(self, obj)
```

Should take an object instance and validate / clean it

Arguments:

    - obj: concrete object instance

#### delete_all

```
delete_all(self)
```

Delete all objects, essentially empty the database

#### get_field

```
get_field(*args, **kwargs)
```

Should retrun a field instance, if your backend does not use
classes to describe fields, leave this as is

Arguments:

    - concrete: concrete class
    - field_name

Returns:

    - field instance

#### save

```
save(self, obj)
```

Save the object instance

Arguments:

    - obj: concrete object instance

#### last_change

```
last_change(*args, **kwargs)
```

should return unix epoch timestamp of the `updated` field
of the most recently updated object

Arguments:

    - concrete: concrete class

Returns:

    - int

#### is_database_migrated

```
is_database_migrated(self, **kwargs)
```

Should return whether the database is fully migrated

Returns:

    - bool
