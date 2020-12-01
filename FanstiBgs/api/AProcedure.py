from ..control.CProcedure import CProcedure
from ..extensions.base_resource import Resource


class AProcedure(Resource):
    def __init__(self):
        self.cprocedure = CProcedure()

    def get(self, procedure):
        apis = {
            'get_area': self.cprocedure.get_area,
            "get_storing_location": self.cprocedure.get_storing_location,
            "get_preservation_type": self.cprocedure.get_preservation_type,
            "get": self.cprocedure.get,
            "list": self.cprocedure.list,
            "get_master_number": self.cprocedure.get_master_number
        }
        return apis

    def post(self, procedure):
        apis = {
            "stork_in": self.cprocedure.stork_in,
            "stork_out": self.cprocedure.stork_out,
            "stork_repeat": self.cprocedure.stork_repeat,
            "update_procedure": self.cprocedure.update_procedure
        }

        return apis