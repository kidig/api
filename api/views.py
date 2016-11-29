import json
from copy import copy
from enum import Enum

import trafaret as t
from django.conf import settings
from django.http import JsonResponse, HttpResponse
from django.utils.module_loading import import_string
from django.views import View

from .exceptions import ConfigurationError, MethodNotAllowed, RequestParseError, RequestContractError, \
    ResponseContractError

__all__ = ('Method', 'ApiView',)


class StaticProperty(object):
    def __init__(self, getter):
        self.getter = getter

    def __get__(self, instance, owner):
        return self.getter()


class Method(Enum):
    GET = 'GET'
    POST = 'POST'


class ApiViewMeta(type):
    def __new__(mcs, name, bases_, attrs):

        bases = []
        for base in bases_:
            if base is not ApiConfig:
                bases.append(base)
        bases = tuple(bases)

        if '__no_check__' not in attrs:
            for base in bases:
                if hasattr(base, 'method'):
                    break
            else:
                if 'method' not in attrs:
                    raise ConfigurationError('{} must declare method'.format(name))
                elif not isinstance(attrs['method'], Method):
                    raise ConfigurationError('{} method isn\'t api.views.Method enum'.format(name))

            for base in bases:
                if hasattr(base, 'in_contract'):
                    break
            else:
                if 'in_contract' not in attrs:
                    raise ConfigurationError('{} must declare in_contract'.format(name))
                elif attrs['in_contract'] is None:
                    pass
                elif not isinstance(attrs['in_contract'], t.Trafaret):
                    raise ConfigurationError('{} in_contract isn\'t trafaret.Trafaret instance')

            for base in bases:
                if hasattr(base, 'out_contract'):
                    break
            else:
                if 'out_contract' not in attrs:
                    raise ConfigurationError('{} must declare out_contract'.format(name))
                elif attrs['out_contract'] is None:
                    pass
                elif not isinstance(attrs['out_contract'], t.Trafaret):
                    raise ConfigurationError('{} out_contract isn\'t trafaret.Trafaret instance')

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
    method = None
    in_contract = None
    out_contract = None

    def handle(self, data):
        pass  # pragma: no cover


class ApiView(View, ApiConfig, metaclass=ApiViewMeta):
    __no_check__ = True

    def _handle(self, data: str):
        try:
            data = json.loads(data)
        except json.JSONDecodeError:
            return RequestParseError()

        if self.in_contract is None:
            if data:
                return RequestContractError()
        else:
            try:
                data = self.in_contract.check_and_return(data)
            except t.DataError:
                return RequestContractError()

        response_data = self.handle(data)

        if self.out_contract is None:
            if isinstance(response_data, int):
                return HttpResponse(status=response_data)
            else:
                return ResponseContractError()
        else:
            try:
                response_data = self.out_contract.check_and_return(response_data)
            except t.DataError:
                return ResponseContractError()

            return JsonResponse(response_data, safe=False)

    def get(self, request):
        if self.method != Method.GET:
            return MethodNotAllowed(['GET'])
        return self._handle(request.GET.get('q', '{}'))

    def post(self, request):
        if self.method != Method.POST:
            return MethodNotAllowed(['POST'])
        return self._handle(request.POST.get('q', '{}'))
