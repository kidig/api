from django.http import HttpResponseBadRequest, HttpResponseNotAllowed, HttpResponseServerError


class ConfigurationError(Exception):
    pass


class MethodNotAllowed(HttpResponseNotAllowed):
    pass


class RequestContractError(HttpResponseBadRequest):
    pass


class RequestParseError(HttpResponseBadRequest):
    pass


class ResponseContractError(HttpResponseServerError):
    pass
