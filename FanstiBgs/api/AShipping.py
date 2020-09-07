from ..control.CShipping import CShipping
from ..extensions.base_resource import Resource


class AShipping(Resource):
    def __init__(self):
        self.cshipping = CShipping()

    def get(self, shipping):
        apis = {
            'list': self.cshipping.list,
            "get": self.cshipping.get
        }
        return apis

    def post(self, shipping):
        apis = {

        }

        return apis