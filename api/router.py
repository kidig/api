import re

from django.conf.urls import url

from . import schema as s
from .views import ApiView


def snake_case(name):
    s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
    return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()


class Router:
    def views(self):
        for view in ApiView.__subclasses__():
            if view.router == self and not view.abstract:
                yield view

    @property
    def urls(self):
        patterns = []
        for view in self.views():
            patterns.append(
                url('^{}/$'.format(snake_case(view.swagger_spec.name)), view.as_view()),
            )
        return patterns, None, None

    def swagger(self):
        data = {
            'swagger': '2.0',
            'basePath': '/api',
            'schemes': ['http'],
            'consumes': ['application/json'],
            'produces': ['application/json'],
            'info': {
                'title': '',
                'version': ''
            },
            'paths': {
                '/{}/'.format(snake_case(view.__name__)): view.swagger_spec.spec for view in self.views()
                }
        }
        if s.Definition.registered:
            data[s.DEFINITIONS_PATH] = {d.name: d.schema.to_json() for d in s.Definition.registered.values()}
        return data
