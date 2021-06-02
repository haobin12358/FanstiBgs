"""
盘库相关api
create user: haobin12358
last update time: 2020-09-16
"""

import hashlib, datetime, requests, uuid, os
from flask import request, current_app

from FanstiBgs.extensions.params_validates import parameter_required
from FanstiBgs.extensions.error_response import ParamsError, AuthorityError, NoPreservationError
from FanstiBgs.extensions.request_handler import token_to_user_
from FanstiBgs.extensions.token_handler import usid_to_token
from FanstiBgs.extensions.register_ext import db
from FanstiBgs.extensions.success_response import Success
from FanstiBgs.models.bgs_android import an_mechandise_inventory_part, an_user, an_mechandis_inventory_time, \
    an_procedure, an_preservation_type, an_storing_location, an_area, an_master_number_remark, \
    an_merchandise_inventory_main
from FanstiBgs.models.bgs_cloud import t_bgs_main_single_number, t_bgs_un

class CMechandis:

    def _get_time_zones(self):
        """
        获取当前盘库时间段
        """
        time_zones_dict = {
            "time_start": "",
            "time_end": ""
        }
        now = datetime.datetime.now()
        mechandis_inventory_dict = an_mechandis_inventory_time.query.filter(
            now.hour > an_mechandis_inventory_time.start_time_hour,
            now.minute > an_mechandis_inventory_time.start_time_minute,
            now.second > an_mechandis_inventory_time.start_time_second,
            now.hour < an_mechandis_inventory_time.end_time_hour,
            now.minute < an_mechandis_inventory_time.end_time_minute,
            now.second < an_mechandis_inventory_time.end_time_second
        ).first_("不在盘库时间段内")
        time_zones_dict["time_start"] = datetime.datetime(now.year, now.month, now.day,
                                                          int(mechandis_inventory_dict.start_time_hour),
                                                          int(mechandis_inventory_dict.start_time_minute),
                                                          int(mechandis_inventory_dict.start_time_second))
        time_zones_dict["time_end"] = datetime.datetime(now.year, now.month, now.day,
                                                          int(mechandis_inventory_dict.end_time_hour),
                                                          int(mechandis_inventory_dict.end_time_minute),
                                                          int(mechandis_inventory_dict.end_time_second))

        return time_zones_dict

    def get_mechandis_list(self):
        """
        获取可盘库的列表
        """
        args = parameter_required(("token", ))
        page_size = int(args.get("page_size")) or 15
        page_num = int(args.get("page_num")) or 1
        time_zones_dict = self._get_time_zones()
        mechandise_inventory_part = an_mechandise_inventory_part.query.filter(
            an_mechandise_inventory_part.createtime > time_zones_dict["time_start"],
            an_mechandise_inventory_part.createtime < time_zones_dict["time_end"]).all()

        master_list = []
        for row in mechandise_inventory_part:
            master_list.append(row.master_id)

        filter_args = [an_procedure.id.notin_(master_list), an_procedure.preservation.in_(["repeat", "in"])]

        if args.get("preservation_id"):
            preservation = an_preservation_type.query.filter(an_preservation_type.id == args.get("preservation_id"))\
                .first_("未找到该类别")
            storing_id = preservation.storing_id
            if args.get("storing_id"):
                if storing_id != args.get("storing_id"):
                    return ParamsError("仓位中无此类别，请先选择仓位再选择类别")
            storing = an_storing_location.query.filter(an_storing_location.id == storing_id).first_("未找到该仓位")
            area_id = storing.area_id
            if args.get("area_id"):
                if area_id != args.get("area_id"):
                    return ParamsError("该区域中无此仓位，请先选择区域再选择仓位")
            filter_args.append(an_procedure.preservation_type == preservation.preservation_type_name)
        if args.get("storing_id"):
            storing = an_storing_location.query.filter(an_storing_location.id == args.get("storing_id"))\
                .first_("未找到该仓位")
            area_id = storing.area_id
            if args.get("area_id"):
                if area_id != args.get("area_id"):
                    return ParamsError("该区域中无此仓位，请先选择区域再选择仓位")
            filter_args.append(an_procedure.storing_location == storing.storing_location_name)
        if args.get("area_id"):
            area = an_area.query.filter(an_area.id == args.get("area_id")).first_("未找到该区域")
            filter_args.append(an_procedure.preservation_area == area.area_name)
        if args.get("board_no"):
            if args.get("storing_id"):
                storing = an_storing_location.query.filter(an_storing_location.id == args.get("storing_id"))\
                    .first_("未找到该仓位")
                if storing.storing_location_name not in ["大货区", "锂电池暂存区", "ETV区", "Stacker区"]:
                    return ParamsError("需要选择特殊仓位")
                area_id = storing.area_id
                if args.get("area_id"):
                    if area_id != args.get("area_id"):
                        return ParamsError("该区域中无此仓位，请先选择区域再选择仓位")
                filter_args.append(an_procedure.board_no == args.get("board_no"))
            else:
                return ParamsError("需要选择特殊仓位")
        if args.get("master_number"):
            filter_args.append(an_procedure.master_number.like("%{0}%".format(args.get("master_number"))))

        # 20210518需求变更，根据危险品类别排序，再根据单号后四位排序
        master_list = an_procedure.query.filter(*filter_args)\
            .order_by(an_procedure.create_time.desc(),
                      an_procedure.master_number_cut.asc())\
            .all_with_page()
        port_no = 1 + page_size * (page_num - 1)
        for master_dict in master_list:
            master_dict.fill("port_no", port_no)
            port_no += 1

        return Success(data=master_list)


    def get_mechandis_history_list(self):
        """
        获取盘库历史列表
        """
        args = parameter_required(("token",))
        page_size = int(args.get("page_size")) or 15
        page_num = int(args.get("page_num")) or 1
        time_zones_dict = self._get_time_zones()

        filter_args = []

        if args.get("preservation_id"):
            preservation = an_preservation_type.query.filter(an_preservation_type.id == args.get("preservation_id"))\
                .first_("未找到该类别")
            storing_id = preservation.storing_id
            if args.get("storing_id"):
                if storing_id != args.get("storing_id"):
                    return ParamsError("仓位中无此类别，请先选择仓位再选择类别")
            storing = an_storing_location.query.filter(an_storing_location.id == storing_id).first_("未找到该仓位")
            area_id = storing.area_id
            if args.get("area_id"):
                if area_id != args.get("area_id"):
                    return ParamsError("该区域中无此仓位，请先选择区域再选择仓位")
            filter_args.append(an_mechandise_inventory_part.preservation_type == preservation.preservation_type_name)
        if args.get("storing_id"):
            storing = an_storing_location.query.filter(an_storing_location.id == args.get("storing_id"))\
                .first_("未找到该仓位")
            area_id = storing.area_id
            if args.get("area_id"):
                if area_id != args.get("area_id"):
                    return ParamsError("该区域中无此仓位，请先选择区域再选择仓位")
            filter_args.append(an_mechandise_inventory_part.storing_location == storing.storing_location_name)
        if args.get("area_id"):
            area = an_area.query.filter(an_area.id == args.get("area_id")).first_("未找到该区域")
            filter_args.append(an_mechandise_inventory_part.preservation_area == area.area_name)
        if args.get("board_no"):
            if args.get("storing_id"):
                storing = an_storing_location.query.filter(an_storing_location.id == args.get("storing_id"))\
                    .first_("未找到该仓位")
                if storing.storing_location_name not in ["大货区", "锂电池暂存区", "ETV区", "Stacker区"]:
                    return ParamsError("需要选择特殊仓位")
                area_id = storing.area_id
                if args.get("area_id"):
                    if area_id != args.get("area_id"):
                        return ParamsError("该区域中无此仓位，请先选择区域再选择仓位")
                filter_args.append(an_mechandise_inventory_part.board_no == args.get("board_no"))
            else:
                return ParamsError("需要选择特殊仓位")
        if args.get("master_number"):
            filter_args.append(an_mechandise_inventory_part.master_number.like("%{0}%".format(args.get("master_number"))))

        if args.get("start_time"):
            filter_args.append(an_mechandise_inventory_part.createtime > args.get("start_time"))

        if args.get("end_time"):
            filter_args.append(an_mechandise_inventory_part.createtime < args.get("end_time"))

        master_id_list = []
        mechandise_inventory_part = an_mechandise_inventory_part.query.filter(*filter_args)\
            .order_by(an_mechandise_inventory_part.createtime.desc()).all()
        for mechandise in mechandise_inventory_part:
            if mechandise["main_id"] not in master_id_list:
                master_id_list.append(mechandise["main_id"])

        master_id_page = master_id_list[(page_num-1) * page_size: page_num * page_size]

        total_count = len(master_id_page)
        if total_count % page_size == 0:
            total_page = int(total_count / page_size)
        else:
            total_page = int(total_count / page_size) + 1

        port_no = 1 + page_size * (page_num - 1)
        merchandise_inventory_main = []
        for master_id in master_id_page:
            merchandise_inventory_main_dict = an_merchandise_inventory_main.query.filter(
                an_merchandise_inventory_main.id == master_id).first()
            if merchandise_inventory_main_dict:
                merchandise_inventory_main_dict.fill("port_no", port_no)
                merchandise_inventory_main.append(merchandise_inventory_main_dict)
                port_no += 1

        return {
            "status": 200,
            "message": "获取成功",
            "data": merchandise_inventory_main,
            "total_page": total_page,
            "total_count": total_count
        }


    def get_mechandis_history(self):
        """
        获取盘库历史详情
        """
        args = parameter_required(('main_id', 'token'))

        # 排序
        part_inventory = an_mechandise_inventory_part.query.filter(
            an_mechandise_inventory_part.main_id == args.get("main_id"))\
            .order_by(an_mechandise_inventory_part.master_number_cut.desc()).all_with_page()

        for row in part_inventory:
            procedure = an_procedure.query.filter(an_procedure.id == row.master_id).first()
            row.fill("inputer_name", procedure.inputer_name)
            row.fill("create_time", procedure.create_time)

        return Success(data=part_inventory)

    def make_mechandis_remark(self):
        """
        提交盘库备注
        """
        data = parameter_required(("message", "master_id"))
        user_id = getattr(request, "user").id
        user = an_user.query.filter(an_user.user_id == user_id).first_("未找到该用户")
        with db.auto_commit():
            an_remark_instance = an_master_number_remark.create({
                "id": str(uuid.uuid1()),
                "master_number_id": data.get("master_id"),
                "message": data.get("message"),
                "createtime": datetime.datetime.now(),
                "user_id": user_id
            })
            db.session.add(an_remark_instance)

        return Success(message="备注成功")

    def get_mechandis_remark(self):
        """
        获取盘库备注
        """
        args = parameter_required(("token", "master_id"))
        time_zones_dict = self._get_time_zones()
        filter_args = [an_master_number_remark.createtime > time_zones_dict["time_start"],
                       an_master_number_remark.createtime < time_zones_dict["time_end"],
                       an_master_number_remark.master_number_id == args.get("master_id")
                       ]
        mechandis_remark = an_master_number_remark.query.filter(*filter_args)\
            .order_by(an_master_number_remark.createtime.desc()).first()
        if not mechandis_remark:
            mechandis_remark = {
                "message": ""
            }

        return Success(data=mechandis_remark)



    def make_mechandis_history(self):
        """
        提交盘库
        """
        data = request.json
        user_id = getattr(request, "user").id
        user = an_user.query.filter(an_user.user_id == user_id).first_("未找到该用户")
        main_id = str(uuid.uuid1())
        with db.auto_commit():
            for mechandise in data:
                if "board_no" in mechandise.keys():
                    board_no = mechandise["board_no"]
                else:
                    board_no = None
                if mechandise["master_number"]:
                    master_number_cut = str(mechandise["master_number"])[-4:] or ""
                else:
                    master_number_cut = ""
                mechandise_dict = {
                    "id": str(uuid.uuid1()),
                    "main_id": main_id,
                    "master_id": mechandise["id"],
                    "createtime": datetime.datetime.now(),
                    "master_number": mechandise["master_number"],
                    "master_number_cut": master_number_cut,
                    "preservation_area": mechandise["preservation_area"],
                    "storing_location": mechandise["storing_location"],
                    "preservation_type": mechandise["preservation_type"],
                    "board_no": board_no
                }
                mechandise_inventory_part_instance = an_mechandise_inventory_part.create(mechandise_dict)
                db.session.add(mechandise_inventory_part_instance)
            merchandise_main_dict = {
                "id": main_id,
                "stork_user_id": user_id,
                "stork_user_name": user.user_truename,
                "createtime": datetime.datetime.now()
            }
            merchandise_main_instance = an_merchandise_inventory_main.create(merchandise_main_dict)
            db.session.add(merchandise_main_instance)

        return Success(message="盘库成功")