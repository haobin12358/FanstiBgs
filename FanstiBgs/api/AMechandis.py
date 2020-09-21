from ..control.CMechandis import CMechandis
from ..extensions.base_resource import Resource


class AMechandis(Resource):
    def __init__(self):
        self.cmechandis = CMechandis()

    def get(self, mechandis):
        apis = {
            'get_mechandis_list': self.cmechandis.get_mechandis_list,
            'get_mechandis_remark': self.cmechandis.get_mechandis_remark,
            'get_mechandis_history_list': self.cmechandis.get_mechandis_history_list,
            'get_mechandis_history': self.cmechandis.get_mechandis_history
        }
        return apis

    def post(self, mechandis):
        apis = {
            'make_mechandis_remark': self.cmechandis.make_mechandis_remark,
            'make_mechandis_history': self.cmechandis.make_mechandis_history
        }

        return apis