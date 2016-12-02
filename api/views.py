import json
import logging
import typing

from django.conf import settings
from django.http import HttpResponse, JsonResponse
from django.utils.module_loading import import_string
from django.views import View

from . import schema as s
from .exceptions import ConfigurationError, MethodNotAllowed, RequestParseError, RequestContractError, \
    ResponseContractError
from .spec import Spec, Method

__all__ = ('Method', 'ApiView',)

logger = logging.getLogger(__name__)


class StaticProperty:
    def __init__(self, getter):
        self.getter = getter

    def __get__(self, instance, owner):
        return self.getter()


class ClassProperty:
    def __init__(self, getter):
        self.getter = getter

    def __get__(self, instance, owner):
        return self.getter(owner)


class ApiViewMeta(type):
    def __new__(mcs, name, bases_, attrs):

        bases = []
        for base in bases_:
            if base is not ApiConfig:
                bases.append(base)
        bases = tuple(bases)

        if 'abstract' not in attrs:
            attrs['abstract'] = False

        if not attrs['abstract']:
            for base in bases:
                if hasattr(base, 'spec'):
                    break
            else:
                if 'spec' not in attrs:
                    raise ConfigurationError('{} must declare spec'.format(name))
                elif not isinstance(attrs['spec'], Spec):
                    raise ConfigurationError('{} spec isn\'t api.spec.Spec instance')

            for base in bases:
                if hasattr(base, 'handle'):
                    break
            else:
                if 'handle' not in attrs:
                    raise ConfigurationError('{} must declare handle'.format(name))
                elif not callable(attrs['handle']):
                    raise ConfigurationError('{} handle isn\'t callable'.format(name))

        for base in bases:
            if hasattr(base, 'router'):
                break
        else:
            attrs['router'] = StaticProperty(lambda: import_string(settings.API_DEFAULT_ROUTER))

        cls = type.__new__(mcs, name, bases, attrs)
        if not cls.abstract:
            cls.swagger_spec = SwaggerSpec(name, cls.spec, cls.__doc__)
        return cls


class ApiConfig:
    abstract = False
    router = None
    spec = None

    def handle(self, data):
        pass  # pragma: no cover


class SwaggerSpec:
    def __init__(self, name: str, spec: Spec, description: str = None):
        self.name = name
        self.description = description or ''
        if self.name.lower().endswith('view'):
            self.name = self.name[:-4]
        self._spec = spec

    @property
    def spec(self):
        data = {
            'operationId': self.name,
            'responses': {},
            'description': self.description
        }

        if self._spec.payload and self._spec.payload is not s.Empty:
            if self._spec.method is Method.POST:
                data['parameters'] = [{
                    'in': 'body',
                    'name': 'body',
                    'required': True,
                    'schema': self._spec.payload.to_json()
                }]
            elif self._spec.method is Method.GET:
                data['parameters'] = []
                for name, schema in self._spec.payload.properties.items():
                    required = True
                    if isinstance(schema, s.Optional):
                        required = False
                        schema = schema.schema
                    data['parameters'].append(dict(schema.to_json(), **{
                        'in': 'query',
                        'name': name,
                        'required': required
                    }))

        for response in self._spec.responses:
            data['responses'].update(response.swagger())

        return {self._spec.method.value.lower(): data}


class ApiView(View, ApiConfig, metaclass=ApiViewMeta):
    abstract = True

    def _handle(self, data: typing.Optional[str]):
        if not data:
            data = None

        if isinstance(data, str):
            try:
                data = json.loads(data)
            except json.JSONDecodeError:
                return RequestParseError()

        if not self.spec.payload or self.spec.payload is s.Empty:
            if data:
                return RequestContractError()
        else:
            try:
                if self.spec.method is Method.GET:
                    data = self.spec.payload.qs_check_and_return(data)
                else:
                    data = self.spec.payload.check_and_return(data)
            except s.DataError as err:
                return RequestContractError(json.dumps(err.as_dict()), content_type='application/json')

        status_code = 200
        response_data = self.handle(data)
        if isinstance(response_data, int):
            status_code = response_data
            response_data = None
        elif isinstance(response_data, tuple):
            status_code, response_data = response_data

        for response in self.spec.responses:
            if response.code == status_code:
                if response.schema and not response_data:
                    logger.error('{} response with status {} requires data'.format(
                        self.__class__.__name__, status_code))
                    return ResponseContractError()
                elif not response.schema and response_data:
                    logger.error('{} response with status {} defines no data'.format(
                        self.__class__.__name__, status_code))
                    return ResponseContractError()
                elif not response.schema and not response_data:
                    return HttpResponse(status=status_code)

                try:
                    response_data = response.schema.check_and_return(response_data)
                except s.DataError as err:
                    logger.error('{} failed schema validation for response {}: {}'.format(
                        self.__class__.__name__, status_code, err
                    ))
                    return ResponseContractError()

                return JsonResponse(response_data, status=status_code, safe=False)

        logger.error('{} defines no response with status {}'.format(self.__class__.__name__, status_code))
        return ResponseContractError()

    def get(self, request):
        if self.spec.method != Method.GET:
            return MethodNotAllowed(['GET'])
        return self._handle(request.GET)

    def post(self, request):
        if self.spec.method != Method.POST:
            return MethodNotAllowed(['POST'])
        if 'json' in request.content_type:
            return self._handle(request.body.decode('utf-8'))
        return self._handle(request.POST.get('q', '{}'))
