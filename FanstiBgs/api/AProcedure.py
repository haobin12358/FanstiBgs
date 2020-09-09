from ..control.CProcedure import CProcedure
from ..extensions.base_resource import Resource


class AProcedure(Resource):
    def __init__(self):
        self.cprocedure = CProcedure()

    def get(self, procedure):
        apis = {
            'get_area': self.cprocedure.get_area,
            "get_storing_location": self.cprocedure.get_storing_location,
            "get_preservation_type": self.cprocedure.get_preservation_type
        }
        return apis

    def post(self, procedure):
        apis = {

        }

        return apis