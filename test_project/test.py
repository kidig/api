import json
from io import StringIO

import yaml
from django.core.management import call_command
from django.http import QueryDict
from django.test import TestCase

import api.schema as s
from api.exceptions import ConfigurationError
from api.spec import Spec, Response
from api.swagger import validate
from api.views import ApiView, Method


class ApiConfig(TestCase):
    def test_config_errors(self):
        with self.assertRaisesRegex(ConfigurationError, r'spec'):
            class Test1(ApiView):
                pass

        with self.assertRaisesRegex(ConfigurationError, r'spec'):
            class Test2(ApiView):
                spec = 123

        with self.assertRaisesRegex(ConfigurationError, r'handle'):
            class Test3(ApiView):
                spec = Spec(Method.GET, s.Empty)

        with self.assertRaisesRegex(ConfigurationError, r'handle'):
            class Test4(ApiView):
                spec = Spec(Method.GET, s.Empty)
                handle = 123

    def test_inheritance(self):
        class Base(ApiView):
            spec = Spec(
                Method.GET,
                s.Empty(),
                Response(204)
            )

            def handle(self, data):
                pass  # pragma: no cover

        class Sub(Base):
            pass


class ApiBasics(TestCase):
    def test_method_not_allowed(self):
        response = self.client.post('/api/get_method/')
        self.assertEqual(response.status_code, 405)

        response = self.client.get('/api/get_method/')
        self.assertEqual(response.status_code, 204)

        response = self.client.get('/api/post_method/')
        self.assertEqual(response.status_code, 405)

        response = self.client.post('/api/post_method/')
        self.assertEqual(response.status_code, 204)

    def test_invalid_json(self):
        response = self.client.post('/api/post_method/', 'spam', content_type='application/json')
        self.assertEqual(response.status_code, 400)

    def test_get(self):
        response = self.client.get('/api/get_method/')
        self.assertEqual(response.status_code, 204)

    def test_in_contract(self):
        response = self.client.get('/api/in_contract/', {'foo': '1'})
        self.assertEqual(response.status_code, 204)

        response = self.client.get('/api/in_contract/', {'foo': 'bar'})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(json.loads(response.content.decode('utf-8')),
                         [{'path': ['foo'], 'error': "'bar' is not of type 'number'"}])

    def test_out_contract(self):
        response = self.client.get('/api/out_contract/', {'foo': '1'})
        self.assertEqual(response.status_code, 200)

        response = self.client.get('/api/failing_out_contract/', {'result': ''})
        self.assertEqual(response.status_code, 500)

        response = self.client.get('/api/failing_out_contract/', {'result': 'true'})
        self.assertEqual(response.status_code, 200)

    def test_return_status(self):
        response = self.client.get('/api/return_status/', {'result': 'int'})
        self.assertEqual(response.status_code, 204)

        response = self.client.get('/api/return_status/', {'result': 'dict'})
        self.assertEqual(response.status_code, 200)

        response = self.client.get('/api/return_status/', {'result': 'fail'})
        self.assertEqual(response.status_code, 500)

    def test_json_body(self):
        data = {'foo': 'bar'}
        response = self.client.post('/api/echo/', {
            'q': json.dumps(data)
        })
        self.assertEqual(response.status_code, 200)
        self.assertDictEqual(json.loads(response.content.decode('utf-8')), data)

        response = self.client.post('/api/echo/', json.dumps(data), 'application/json')
        self.assertEqual(response.status_code, 200)
        self.assertDictEqual(json.loads(response.content.decode('utf-8')), data)


class SchemaViewTest(TestCase):
    def test_in_schema(self):
        response = self.client.post('/api/schema/', json.dumps({
            'foo': '',
            'bar': '',
            'spam': {
                'eggs': 1
            }
        }), content_type='application/json')
        self.assertEqual(response.status_code, 400)
        self.assertEqual(json.loads(response.content.decode('utf-8')),
                         [{'path': ['bar'], 'error': "'' is not of type 'number'"},
                          {'path': ['spam', 'eggs'], 'error': "1 is not of type 'string'"}])

        response = self.client.post('/api/schema/', json.dumps({
            'foo': '',
            'bar': 1,
            'spam': {
                'eggs': ''
            }
        }), content_type='application/json')
        self.assertEqual(response.status_code, 200)

    def test_unknown_response(self):
        response = self.client.get('/api/unknown_response/', {'status': '200'})
        self.assertEqual(response.status_code, 500)

        response = self.client.get('/api/unknown_response/', {'status': '204'})
        self.assertEqual(response.status_code, 500)


class SchemaTestCase(TestCase):
    def test_schema(self):
        child = s.Definition('TestChild', s.Object(
            str=s.String()
        ))
        schema = s.Object(
            str=s.String(),
            number=s.Optional(s.Number()),
            integer=s.Integer(),
            null=s.Null(),
            boolean=s.Boolean(),
            array=s.Array(s.String()),
            child=child
        )
        data = {
            'str': '',
            'number': 1.2,
            'integer': 2,
            'null': None,
            'boolean': True,
            'array': [''],
            'child': {
                'str': ''
            }
        }
        self.assertEqual(data, schema.check_and_return(data))

        del data['number']
        self.assertEqual(data, schema.check_and_return(data))

        del data['boolean']
        data['str'] = 1
        with self.assertRaises(s.DataError) as ctx:
            self.assertEqual(data, schema.check_and_return(data))
        self.assertEqual(ctx.exception.as_dict(), [
            {'path': [], 'error': "'boolean' is a required property"},
            {'path': ['str'], 'error': "1 is not of type 'string'"}
        ])

    def test_duplicate(self):
        s.Definition('Duplicate', s.String())
        with self.assertRaises(ConfigurationError):
            s.Definition('Duplicate', s.String())

    def test_qs(self):
        schema = s.Query(
            string=s.String(),
            number=s.Number(),
            integer=s.Integer(),
            boolean=s.Boolean(),
            array=s.Array(s.String())
        )
        data = QueryDict('string=foo&number=1.2&integer=1&boolean=&array=foo&array=bar')
        self.assertEqual(schema.qs_check_and_return(data), {
            'string': 'foo',
            'number': 1.2,
            'integer': 1,
            'boolean': False,
            'array': ['foo', 'bar']
        })

        data = QueryDict('string=foo&number=1.2&boolean=&array=foo&array=bar')
        with self.assertRaises(s.DataError) as ctx:
            schema.qs_check_and_return(data)
        self.assertEqual(ctx.exception.as_dict(), [{
            'path': ['integer'],
            'error': "'None' is not of type 'integer'"
        }])


class SwaggerTestCase(TestCase):
    def test_spec(self):
        output = StringIO()
        call_command('swagger_spec', stdout=output)
        validate(yaml.load(output.getvalue()))
