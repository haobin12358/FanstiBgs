"""
本文件用于处理收运管理
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
            filter_args.append(t_bgs_main_single_number.destination_port == request.args.get("destination_port"))
        return

    def get(self):
        """
        获取检查单详情
        """
        args = parameter_required(("token", "master_number"))
        main_port = t_bgs_main_single_number.query\
            .filter(t_bgs_main_single_number.master_number == args.get("master_number"))\
            .first_("未找到该单据")
        un_list = t_bgs_un.query.filter(t_bgs_un.master_number == args.get("master_number")).all()
        main_port.append(un_list)
        return Success("获取成功", data=main_port)

