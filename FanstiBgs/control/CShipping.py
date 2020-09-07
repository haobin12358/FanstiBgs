"""
本文件用于处理收运管理
create user: haobin12358
last update time: 2020-09-07
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
from FanstiBgs.models.bgs_cloud import t_bgs_main_single_number

class CShipping:

    def list(self):
        """
        获取检查单列表
        """
        token = token_to_user_(request.args.get("token"))
        filter_args = []
        if request.args.get("master_number"):
            filter_args.append(t_bgs_main_single_number.master_number == request.args.get("master_number"))
        if request.args.get("destination_port"):
            filter_args.append()
        return

    def get(self):
        return