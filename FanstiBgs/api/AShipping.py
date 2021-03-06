from ..control.CShipping import CShipping
from ..extensions.base_resource import Resource


class AShipping(Resource):
    def __init__(self):
        self.cshipping = CShipping()

    def get(self, shipping):
        apis = {
            'list': self.cshipping.list,
            "get": self.cshipping.get,
            "get_photos": self.cshipping.get_photos,
            "get_checklist_type": self.cshipping.get_checklist_type,
            "get_checklist_item": self.cshipping.get_checklist_item,
            "get_checklist_message": self.cshipping.get_checklist_message
        }
        return apis

    def post(self, shipping):
        apis = {
            "upload_photos": self.cshipping.upload_photos,
            "make_checklist_history": self.cshipping.make_checklist_history
        }

        return apis