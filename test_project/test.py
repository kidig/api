import json
import io

from django.test import TestCase

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
