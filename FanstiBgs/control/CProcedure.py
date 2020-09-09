"""
本文件用于处理进出港出入库及盘库
create user: haobin12358
last update time: 2020-09-09
"""

import hashlib, datetime, requests
from flask import request, current_app

from FanstiBgs.extensions.params_validates import parameter_required
from FanstiBgs.extensions.error_response import ParamsError, AuthorityError
from FanstiBgs.extensions.request_handler import token_to_user_
from FanstiBgs.extensions.token_handler import usid_to_token
from FanstiBgs.extensions.register_ext import db
from FanstiBgs.extensions.success_response import Success
from FanstiBgs.models.bgs_android import an_user
from FanstiBgs.models.bgs_cloud import t_bgs_main_single_number, t_bgs_un

class CProcedure:

    def get_area(self):
        """
        获取区域
        """
        return

    def get_storing_location(self):
        """
        获取仓位
        """
        return

    def get_preservation_type(self):
        """
        获取类别
        """
        return 