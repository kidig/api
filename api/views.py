import json
import logging
from copy import copy

from django.conf import settings
from django.http import JsonResponse, HttpResponse
from django.utils.module_loading import import_string
from django.views import View

from . import schema as s
from .exceptions import ConfigurationError, MethodNotAllowed, RequestParseError, RequestContractError, \
    ResponseContractError
from .spec import Spec, Method

__all__ = ('Method', 'ApiView',)

logger = logging.getLogger(__name__)


class StaticProperty(object):
    def __init__(self, getter):
        self.getter = getter

    def __get__(self, instance, owner):
        return self.getter()


class ApiViewMeta(type):
    def __new__(mcs, name, bases_, attrs):

        bases = []
        for base in bases_:
            if base is not ApiConfig:
                bases.append(base)
        bases = tuple(bases)

        if '__no_check__' not in attrs:
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

        else:
            attrs = copy(attrs)
            del attrs['__no_check__']

        for base in bases:
            if hasattr(base, 'router'):
                break
        else:
            attrs['router'] = StaticProperty(lambda: import_string(settings.API_DEFAULT_ROUTER))

        return type.__new__(mcs, name, bases, attrs)


class ApiConfig:
    router = None
    spec = None

    def handle(self, data):
        pass  # pragma: no cover


class ApiView(View, ApiConfig, metaclass=ApiViewMeta):
    __no_check__ = True

    def _handle(self, data: str):
        try:
            data = json.loads(data)
        except json.JSONDecodeError:
            return RequestParseError()

        if self.spec.payload is s.Empty:
            if data:
                return RequestContractError()
        else:
            try:
                data = self.spec.payload.check_and_return(data)
            except s.DataError as err:
                return RequestContractError(json.dumps(err.as_dict()), content_type='application/json')

        response_data = self.handle(data)

        if isinstance(response_data, int):
            for response in self.spec.responses:
                if response.code == response_data and not response.schema:
                    return HttpResponse(status=response_data)
            else:
                logger.error('{} response is not declared for {}'.format(response_data, self.__class__.__name__))
                return ResponseContractError()
        else:
            for response in self.spec.responses:
                if response.code == 200:
                    try:
                        response_data = response.schema.check_and_return(response_data)
                    except s.DataError as err:
                        logger.error('{} failed out contract validation {}'.format(self.__class__.__name__, err))
                        return ResponseContractError()

        return JsonResponse(response_data, safe=False)

    def get(self, request):
        if self.spec.method != Method.GET:
            return MethodNotAllowed(['GET'])
        return self._handle(request.GET.get('q', '{}'))

    def post(self, request):
        if self.spec.method != Method.POST:
            return MethodNotAllowed(['POST'])
        if 'json' in request.content_type:
            return self._handle(request.body.decode('utf-8'))
        return self._handle(request.POST.get('q', '{}'))
