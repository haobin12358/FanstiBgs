from datetime import datetime

from FanstiBgs.config.enums import TestEnum
from FanstiBgs.extensions.success_response import Success


class CHello(object):
    def hello(self):
        return Success()
