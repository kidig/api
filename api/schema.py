import abc
import typing

import jsonschema
from django.utils.functional import cached_property

from .exceptions import ConfigurationError

REF_KEY = '$ref'
DEFINITIONS_PATH = 'definitions'


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


class Boolean(Schema):
    def to_json(self):
        return {'type': 'boolean'}


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
        return {
            'type': 'object',
            'properties': properties,
            'required': required
        }


class Array(Schema):
    def __init__(self, schema: Schema):
        self.schema = schema

    def to_json(self):
        return {
            'type': 'array',
            'items': self.schema.to_json()
        }


class Number(Schema):
    def to_json(self):
        return {'type': 'number'}


class String(Schema):
    def to_json(self):
        return {'type': 'string'}


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
