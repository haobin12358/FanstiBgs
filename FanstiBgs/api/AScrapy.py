from ..control.CScrapy import CScrapy
from ..extensions.base_resource import Resource


class AScrapy(Resource):
    def __init__(self):
        self.cscrapy = CScrapy()

    def get(self, scrapy):
        apis = {
            'get_cas': self.cscrapy.get_cas,
            'get_flyno': self.cscrapy.get_flyno,
            'get_dgr': self.cscrapy.get_dgr,
            'add_checklist': self.cscrapy.add_checklist,
            'get_jd': self.cscrapy.get_jd,
            'get_jd_names': self.cscrapy.get_jd_names
        }
        return apis