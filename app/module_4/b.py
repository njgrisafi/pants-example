import requests
from module_2 import *
from module_common import *
from module_common.utils import json

c.example_c()
b.example_b()


def example_json() -> str:
    return json.dumps({"test": "test"})
