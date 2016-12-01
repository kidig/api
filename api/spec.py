import enum
import typing

from .schema import Schema


class Method(enum.Enum):
    GET = 'GET'
    POST = 'POST'


class Response:
    def __init__(self, code: int, schema: typing.Optional[Schema] = None):
        self.code = code
        self.schema = schema


class Spec:
    def __init__(self, method: Method, payload: typing.Optional[Schema], *responses: typing.List[Response]):
        self.method = method
        self.payload = payload
        self.responses = responses
