import json

from django.test import TestCase

import api.schema as s
from api.exceptions import ConfigurationError
from api.views import ApiView, Method


class ApiConfig(TestCase):
    def test_config_errors(self):
        with self.assertRaisesRegex(ConfigurationError, r'method'):
            class Test1(ApiView):
                pass

        with self.assertRaisesRegex(ConfigurationError, r'method'):
            class Test2(ApiView):
                method = 'GET'

        with self.assertRaisesRegex(ConfigurationError, r'in_contract'):
            class Test3(ApiView):
                method = Method.GET

        with self.assertRaisesRegex(ConfigurationError, r'in_contract'):
            class Test4(ApiView):
                method = Method.GET
                in_contract = 'spam'

        with self.assertRaisesRegex(ConfigurationError, r'out_contract'):
            class Test5(ApiView):
                method = Method.GET
                in_contract = None

        with self.assertRaisesRegex(ConfigurationError, r'out_contract'):
            class Test6(ApiView):
                method = Method.GET
                in_contract = None
                out_contract = 'spam'

        with self.assertRaisesRegex(ConfigurationError, r'handle'):
            class Test7(ApiView):
                method = Method.GET
                in_contract = None
                out_contract = None

        with self.assertRaisesRegex(ConfigurationError, r'handle'):
            class Test8(ApiView):
                method = Method.GET
                in_contract = None
                out_contract = None
                handle = 'eggs'

    def test_inheritance(self):
        class Base(ApiView):
            method = Method.GET
            in_contract = None
            out_contract = None

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
        response = self.client.get('/api/get_method/', {
            'q': 'spam'
        })
        self.assertEqual(response.status_code, 400)

        response = self.client.post('/api/post_method/', {
            'q': 'eggs'
        })
        self.assertEqual(response.status_code, 400)

    def test_in_contract(self):
        response = self.client.get('/api/get_method/', {
            'q': json.dumps({'foo': 'bar'})
        })
        self.assertEqual(response.status_code, 400)

        response = self.client.get('/api/in_contract_view/', {
            'q': json.dumps({'foo': 1})
        })
        self.assertEqual(response.status_code, 204)

        response = self.client.get('/api/in_contract_view/', {
            'q': json.dumps({'foo': '1'})
        })
        self.assertEqual(response.status_code, 204)

        response = self.client.get('/api/in_contract_view/', {
            'q': json.dumps({'foo': 'bar'})
        })
        self.assertEqual(response.status_code, 400)
        self.assertDictEqual(json.loads(response.content.decode('utf-8')),
                             {'foo': "value can't be converted to int"})

    def test_out_contract(self):
        response = self.client.get('/api/out_contract_view/', {
            'q': json.dumps({'foo': '1'})
        })
        self.assertEqual(response.status_code, 200)

        response = self.client.get('/api/out_contract_view/', {
            'q': json.dumps({'foo': 'bar'})
        })
        self.assertEqual(response.status_code, 500)

    def test_return_status(self):
        response = self.client.get('/api/return_status_view/', {
            'q': json.dumps({'result': 'int'})
        })
        self.assertEqual(response.status_code, 204)

        response = self.client.get('/api/return_status_view/', {
            'q': json.dumps({'result': 'dict'})
        })
        self.assertEqual(response.status_code, 500)

    def test_json_body(self):
        data = {'foo': 'bar'}
        response = self.client.post('/api/echo_view/', {
            'q': json.dumps(data)
        })
        self.assertEqual(response.status_code, 200)
        self.assertDictEqual(json.loads(response.content.decode('utf-8')), data)

        response = self.client.post('/api/echo_view/', json.dumps(data), 'application/json')
        self.assertEqual(response.status_code, 200)
        self.assertDictEqual(json.loads(response.content.decode('utf-8')), data)


class SchemaViewTest(TestCase):
    def test_in_schema(self):
        response = self.client.post('/api/schema_view/', json.dumps({
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

        response = self.client.post('/api/schema_view/', json.dumps({
            'foo': '',
            'bar': 1,
            'spam': {
                'eggs': ''
            }
        }), content_type='application/json')
        self.assertEqual(response.status_code, 204)


class SchemaTestCase(TestCase):
    def test_schema(self):
        child = s.Definition('TestChild', s.Object(
            str=s.String()
        ))
        schema = s.Object(
            str=s.String(),
            number=s.Optional(s.Number()),
            null=s.Null(),
            boolean=s.Boolean(),
            array=s.Array(s.String()),
            child=child
        )
        data = {
            'str': '',
            'number': 1,
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
