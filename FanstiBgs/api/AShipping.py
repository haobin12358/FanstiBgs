from ..control.CShipping import CShipping
from ..extensions.base_resource import Resource


class AShipping(Resource):
    def __init__(self):
        self.cshipping = CShipping()

    def get(self, shipping):
        apis = {
            'list': self.cshipping.list,
            "get": self.cshipping.get,
            "get_photos": self.cshipping.get_photos
        }
        return apis

    def post(self, shipping):
        apis = {
            "upload_photos": self.cshipping.upload_photos
        }

        return apis