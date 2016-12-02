import json
import os

import jsonschema


def validate(spec):
    schema_path = os.path.join(os.path.dirname(__file__), 'swagger.json')
    with open(schema_path) as fp:
        schema = json.load(fp)
    jsonschema.validate(spec, schema)
