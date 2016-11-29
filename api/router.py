import re

from django.conf.urls import url

from .views import ApiView


def snake_case(name):
    s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
    return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()


class Router:
    def views(self):
        for view in ApiView.__subclasses__():
            if view.router == self:
                yield view

    @property
    def urls(self):
        patterns = []
        for view in self.views():
            patterns.append(
                url('^{}/$'.format(snake_case(view.__name__)), view.as_view()),
            )
        return patterns, None, None
