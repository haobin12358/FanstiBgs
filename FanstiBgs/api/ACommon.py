from ..control.CCommon import CCommon
from ..extensions.base_resource import Resource


class ACommon(Resource):
    def __init__(self):
        self.ccommon = CCommon()

    def post(self, common):
        apis = {
            'upload_file': self.ccommon.upload_file
        }
        return apis