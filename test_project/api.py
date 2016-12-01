import trafaret as t

import api.schema as s
from api.router import Router
from api.views import ApiView, Method

router = Router()


class GetMethod(ApiView):
    method = Method.GET
    in_contract = None
    out_contract = None

    def handle(self, data):
        return 204


class PostMethod(ApiView):
    method = Method.POST
    in_contract = None
    out_contract = None

    def handle(self, data):
        return 204


class InContractView(ApiView):
    method = Method.GET
    in_contract = t.Dict({
        t.Key('foo'): t.Int()
    })
    out_contract = None

    def handle(self, data):
        return 204


class OutContractView(ApiView):
    method = Method.GET
    in_contract = t.Dict({
        t.Key('foo'): t.String()
    })
    out_contract = t.Dict({
        t.Key('foo'): t.Int()
    })

    def handle(self, data):
        return data


class ReturnStatusView(ApiView):
    method = Method.GET
    in_contract = t.Dict({
        t.Key('result'): t.Enum('int', 'dict')
    })
    out_contract = None

    def handle(self, data):
        if data['result'] == 'int':
            return 204
        return data


class EchoView(ApiView):
    method = Method.POST
    in_contract = out_contract = t.Dict().allow_extra('*')

    def handle(self, data):
        return data


nested = s.Definition('Nested', s.Object(
    eggs=s.String()
))


class SchemaView(ApiView):
    method = Method.POST
    in_contract = s.Object(
        foo=s.String(),
        bar=s.Number(),
        spam=nested
    )
    out_contract = None

    def handle(self, data):
        return 204
