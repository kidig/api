import api.schema as s
from api.router import Router
from api.spec import Spec, Response
from api.views import ApiView, Method

router = Router()


class GetMethod(ApiView):
    """sample view doc"""

    spec = Spec(
        Method.GET,
        s.Empty,
        Response(204, description='okay')
    )

    def handle(self, data):
        return 204


class PostMethod(ApiView):
    spec = Spec(
        Method.POST,
        s.Empty,
        Response(204)
    )

    def handle(self, data):
        return 204


class InContractView(ApiView):
    spec = Spec(
        Method.GET,
        s.Query(
            foo=s.Number()
        ),
        Response(204)
    )

    def handle(self, data):
        return 204


class OutContractView(ApiView):
    spec = Spec(
        Method.GET,
        s.Query(
            foo=s.String()
        ),
        Response(200, schema=s.Object(
            foo=s.String()
        ))
    )

    def handle(self, data):
        return data


class FailingOutContractView(ApiView):
    spec = Spec(
        Method.GET,
        s.Query(
            result=s.Boolean()
        ),
        Response(200, schema=s.Object(
            foo=s.String()
        ))
    )

    def handle(self, data):
        if data['result']:
            return {'foo': '1'}


class ReturnStatusView(ApiView):
    spec = Spec(
        Method.GET,
        s.Query(
            result=s.String()
        ),
        Response(204),
        Response(200, schema=s.Object(
            result=s.String()
        ))
    )

    def handle(self, data):
        if data['result'] == 'int':
            return 204
        elif data['result'] == 'fail':
            return 201
        return data


class EchoView(ApiView):
    spec = Spec(
        Method.POST,
        s.Object(),
        Response(200, schema=s.Object())
    )

    def handle(self, data):
        return data


nested = s.Definition('Nested', s.Object(
    eggs=s.String()
))


class SchemaView(ApiView):
    model = s.Object(
        foo=s.String(),
        bar=s.Number(),
        spam=nested
    )

    spec = Spec(
        Method.POST,
        model,
        Response(200, schema=s.Array(model))
    )

    def handle(self, data):
        return [data]


class UnknownResponseView(ApiView):
    spec = Spec(
        Method.GET,
        s.Query(
            status=s.Number()
        ),
        Response(204)
    )

    def handle(self, data):
        return data['status'], data


class ForbiddenView(ApiView):
    spec = Spec(
        Method.GET,
        s.Empty,
        Response(403)
    )

    def handle(self, data):
        return 403
