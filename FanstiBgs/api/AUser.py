from ..control.CUser import CUser
from ..extensions.base_resource import Resource


class AUser(Resource):
    def __init__(self):
        self.cuser = CUser()

    def get(self, user):
        apis = {
            #'get': self.cuser.hello
        }
        return apis

    def post(self, user):
        apis = {
            "user_login": self.cuser.user_login,
            "user_password_repeat": self.cuser.user_password_repeat
        }

        return apis