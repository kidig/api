import abc
import typing

import jsonschema
from django.utils.datastructures import MultiValueDict
from django.utils.functional import cached_property

from .exceptions import ConfigurationError

REF_KEY = '$ref'
DEFINITIONS_PATH = 'definitions'


class ConvertError(Exception):
    def __init__(self, message, path=None):
        super(ConvertError, self).__init__(message)
        self.message = message
        self.path = path or []


class DataError(Exception):
    def __init__(self, errors: typing.List[jsonschema.ValidationError]):
        self.errors = errors

    def as_dict(self):
        res = []
        for error in self.errors:
            res.append({
                'path': list(error.path),
                'error': error.message
            })
        return res


class Schema(metaclass=abc.ABCMeta):
    @abc.abstractmethod
    def to_json(self):
        return NotImplemented  # pragma: no cover

    @cached_property
    def _validator(self):
        return jsonschema.Draft4Validator(embed_definitions(self.to_json()))

    def check_and_return(self, instance):
        errors = list(sorted(self._validator.iter_errors(instance), key=str))
        if errors:
            raise DataError(errors)
        return instance


class Empty(Schema):
    def to_json(self):
        raise RuntimeError('Empty is a special case and doesn\'t reflect to real jsonschema')  # pragma: no cover

    def __call__(self, *args, **kwargs):
        pass


Empty = Empty()


class Optional:
    def __init__(self, schema: Schema):
        self.schema = schema


class Definition(Schema):
    registered = {}

    def __init__(self, name: str, schema: Schema):
        self.name = name
        self.reg_name = '#/{}/{}'.format(DEFINITIONS_PATH, name)
        if self.reg_name in self.registered:
            raise ConfigurationError('duplicate definition {}'.format(self.reg_name))
        self.schema = schema
        self.registered[self.reg_name] = self

    def to_json(self):
        return {REF_KEY: self.reg_name}


class Null(Schema):
    def to_json(self):
        return {'type': 'null'}

    def qs_check_and_return(self, instance):
        if instance:
            raise ConvertError("'{}' is not of type 'null'")
        return None


class Boolean(Schema):
    def to_json(self):
        return {'type': 'boolean'}

    def qs_check_and_return(self, instance):
        if instance == 'true':
            return True
        if instance:
            raise ConvertError("'{}' is not of type 'boolean'")
        return False


class Object(Schema):
    def __init__(self, **properties: typing.Mapping[str, typing.Union[Schema, Optional]]):
        self.properties = properties

    def to_json(self):
        properties = {}
        required = []
        for key in sorted(self.properties):
            value = self.properties[key]
            if isinstance(value, Optional):
                value = value.schema
            else:
                required.append(key)
            properties[key] = value.to_json()
        data = {
            'type': 'object'
        }
        if properties:
            data['properties'] = properties
        if required:
            data['required'] = required
        return data


class Array(Schema):
    def __init__(self, schema: Schema):
        self.schema = schema

    def to_json(self):
        return {
            'type': 'array',
            'items': self.schema.to_json()
        }

    def qs_check_and_return(self, instance):
        res = []
        for idx, item in enumerate(instance):
            try:
                res.append(self.schema.qs_check_and_return(item))
            except ConvertError as err:
                raise ConvertError(err.message, [idx] + err.path)
        return res


class Number(Schema):
    def to_json(self):
        return {'type': 'number'}

    def qs_check_and_return(self, instance):
        try:
            return float(instance)
        except (ValueError, TypeError):
            raise ConvertError("'{}' is not of type 'number'".format(instance))


class Integer(Schema):
    def to_json(self):
        return {'type': 'integer'}

    def qs_check_and_return(self, instance):
        try:
            return int(instance)
        except (ValueError, TypeError):
            raise ConvertError("'{}' is not of type 'integer'".format(instance))


class String(Schema):
    def to_json(self):
        return {'type': 'string'}

    def qs_check_and_return(self, instance):
        return instance


class Query(Object):
    def __init__(self, **properties: typing.Mapping[str, typing.Union[String, Integer, Number, Array, Boolean]]):
        super(Query, self).__init__(**properties)

    def qs_check_and_return(self, instance: MultiValueDict):
        try:
            res = {}
            for key, value in self.properties.items():
                try:
                    required = True
                    if isinstance(value, Optional):
                        required = False
                        value = value.schema

                    if not required and key not in instance:
                        continue

                    if isinstance(value, Array):
                        res[key] = value.qs_check_and_return(instance.getlist(key))
                    else:
                        res[key] = value.qs_check_and_return(instance.get(key))

                except ConvertError as err:
                    raise jsonschema.ValidationError(message=err.message, path=[key] + err.path)
            return res
        except jsonschema.ValidationError as err:
            raise DataError([err])

def _collect_definitions(data):
    if isinstance(data, dict):
        res = []
        for key, value in data.items():
            if key == REF_KEY:
                res.append(Definition.registered[value])
            else:
                res += _collect_definitions(value)
        return res
    elif isinstance(data, list):
        return sum(map(_collect_definitions, data), [])
    return []


def embed_definitions(data):
    definitions = _collect_definitions(data)
    if definitions:
        data = dict(data)
        data[DEFINITIONS_PATH] = {d.name: d.schema.to_json() for d in definitions}
    return data
