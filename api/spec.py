import enum
import typing

from . import schema as s
from .exceptions import ConfigurationError


class Method(enum.Enum):
    GET = 'GET'
    POST = 'POST'


class Response:
    def __init__(self, code: int, description: typing.Optional[str] = None, schema: typing.Optional[s.Schema] = None):
        self.code = code
        self.schema = schema
        if description is None:
            if 200 <= code < 300:
                description = 'success'
            else:
                description = 'failure'
        self.description = description

        if self.schema and not isinstance(self.schema, s.Schema):
            raise ConfigurationError('response schema must be api.schema.Schema instance, got {}'
                                     .format(type(self.schema)))

    def swagger(self):
        data = {'description': self.description}
        if self.schema:
            data['schema'] = self.schema.to_json()
        return {
            str(self.code): data
        }


class Spec:
    def __init__(self, method: Method, payload: typing.Optional[s.Schema], *responses: typing.List[Response]):
        self.method = method
        self.payload = payload
        self.responses = responses

        if self.method is Method.GET:
            if payload:
                if not isinstance(payload, s.Query) and payload is not s.Empty:
                    raise ConfigurationError('GET spec must be api.schema.Query or api.schema.Empty instance, got {}'
                                             .format(type(payload)))
