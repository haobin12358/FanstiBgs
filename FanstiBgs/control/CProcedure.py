"""
本文件用于处理进出港出入库及盘库
create user: haobin12358
last update time: 2020-09-09
"""

import hashlib, datetime, requests
from flask import request, current_app

from FanstiBgs.extensions.params_validates import parameter_required
from FanstiBgs.extensions.error_response import ParamsError, AuthorityError, NoPreservationError
from FanstiBgs.extensions.request_handler import token_to_user_
from FanstiBgs.extensions.token_handler import usid_to_token
from FanstiBgs.extensions.register_ext import db
from FanstiBgs.extensions.success_response import Success
from FanstiBgs.models.bgs_android import an_user, an_area, an_storing_location, an_preservation_type
from FanstiBgs.models.bgs_cloud import t_bgs_main_single_number, t_bgs_un

class CProcedure:

    def get_area(self):
        """
        获取区域
        """
        area = an_area.query.filter(an_area.isdelete == 0).all()
        return Success(data=area)

    def get_storing_location(self):
        """
        获取仓位
        """
        filter_args = [an_storing_location.isdelete == 0]
        if request.args.get("area_id"):
            filter_args.append(an_storing_location.area_id == request.args.get("area_id"))
        storing_location = an_storing_location.query.filter(*filter_args).all()
        return Success(data=storing_location)

    def get_preservation_type(self):
        """
        获取类别
        """
        filter_args = [an_preservation_type.isdelete == 0]
        if request.args.get("storing_id"):
            storing_location = an_storing_location.query.filter(
                an_storing_location.id == request.args.get("storing_id"))\
                .first_("未找到该仓位")
            if storing_location.storing_location_name in ["大货区", "锂电池暂存区", "ETV区", "Stacker区"]:
                return NoPreservationError()
            filter_args.append(an_preservation_type.storing_id == request.args.get("storing_id"))
        preservation_type = an_preservation_type.query.filter(*filter_args).all()
        return Success(data=preservation_type)

    def get(self):
        """
        获取详情
        1.基于id（获取详情）
        2.基于master_number（创建一条数据后，返回详情）
        """
        args = parameter_required(("procedure_type", ))
        if args.get("id"):

            pass
        elif args.get("master_number"):
            pass

        return

    def list(self):
        """
        获取列表
        """

        return

    def stork_in(self):
        """
        入库
        """

        return

    def stork_out(self):
        """
        出库
        """

        return

    def stork_repeat(self):
        """
        重新入库
        """

        return