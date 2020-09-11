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
from FanstiBgs.models.bgs_android import an_procedure
from FanstiBgs.models.bgs_cloud import t_bgs_main_single_number, t_bgs_un, t_bgs_shipper_consignee_info

class CShipping:

    def list(self):
        """
        获取检查单列表
        """
        token = token_to_user_(request.args.get("token"))
        filter_args = []
        if request.args.get("master_number"):
            filter_args.append(t_bgs_main_single_number.master_number.like("%{0}%".format(request.args.get("master_number"))))
        if request.args.get("destination_port"):
            filter_args.append(t_bgs_main_single_number.destination_port == request.args.get("destination_port"))
        main_port = t_bgs_main_single_number.query.filter(*filter_args).all_with_page()
        page_num = request.args.get("page_num") or 1
        page_size = request.args.get("page_size") or 15
        i = 1
        for port in main_port:
            un_list = t_bgs_un.query.filter(t_bgs_un.master_number == port.id).all()
            port.fill("un_count", len(un_list))
            # TODO 判断已检查
            port_status = ""
            if True:
                port_status = "已检查"
            else:
                port_status = "未检查"
            procedure = an_procedure.query.filter(an_procedure.master_number == port.id).all()
            if procedure:
                procedure_status = ""
                for procedure_dict in procedure:
                    preservation = procedure_dict.preservation
                    if preservation == "in":
                        if not procedure_status:
                            procedure_status = preservation
                    elif preservation == "out":
                        if not procedure_status or procedure_status in ["in"]:
                            procedure_status = preservation
                    elif preservation == "repeat":
                        procedure_status = preservation
                if procedure_status == "in":
                    port_status = "已入库"
                elif procedure_status == "out":
                    port_status = "已出库"
                elif procedure_status == "repeat":
                    port_status = "重新入库"
            port.fill("port_status", port_status)
            port.fill("port_no", page_size * (page_num - 1) + i)
            i = i + 1
        return Success(data=main_port)

    def get(self):
        """
        获取检查单详情
        """
        args = parameter_required(("token", "id"))
        main_port = t_bgs_main_single_number.query.filter(t_bgs_main_single_number.id == args.get("id"))\
            .first_("未找到该单据")
        # TODO 签名图片需要改为url
        un_list = t_bgs_un.query.filter(t_bgs_un.master_number == args.get("id")).all()
        odd_number_list = []
        for un in un_list:
            if un.odd_number and un.odd_number not in odd_number_list:
                odd_number_list.append(un.odd_number)
        part_port = []
        for odd_number in odd_number_list:
            odd_dict = {}
            odd_dict["odd_number"] = odd_number
            un_list_by_odd_master = t_bgs_un.query.filter(t_bgs_un.master_number == args.get("id"),
                                                          t_bgs_un.odd_number == odd_number).all()
            odd_dict["un_list"] = un_list_by_odd_master
            odd_dict["length"] = len(un_list_by_odd_master)
            part_port.append(odd_dict)
        main_port.fill("un_list", part_port)
        receiver_dict = t_bgs_shipper_consignee_info.query.filter(
            t_bgs_shipper_consignee_info.master_number == args.get("id"),
            t_bgs_shipper_consignee_info.info_state == "2")\
            .first()
        sender_dict = t_bgs_shipper_consignee_info.query.filter(
            t_bgs_shipper_consignee_info.master_number == args.get("id"),
            t_bgs_shipper_consignee_info.info_state == "1")\
            .first()

        receiver = ""
        if receiver_dict.country:
            receiver += "国家：{0}".format(receiver_dict.country)
        if receiver_dict.city:
            receiver += "<br/>城市：{0}".format(receiver_dict.city)
        if receiver_dict.company_name:
            receiver += "<br/>公司名称：{0}".format(receiver_dict.company_name)
        if receiver_dict.company_address:
            receiver += "<br/>公司地址：{0}".format(receiver_dict.company_address)
        if receiver_dict.name:
            receiver += "<br/>姓名：{0}".format(receiver_dict.name)
        if receiver_dict.mailbox:
            receiver += "<br/>邮箱：{0}".format(receiver_dict.mailbox)
        if receiver_dict.fax:
            receiver += "<br/>传真：{0}".format(receiver_dict.fax)
        if receiver_dict.phone:
            receiver += "<br/>电话：{0}".format(receiver_dict.phone)
        sender = ""
        if sender_dict.country:
            sender += "国家：{0}".format(sender_dict.country)
        if sender_dict.city:
            sender += "<br/>城市：{0}".format(sender_dict.city)
        if sender_dict.company_name:
            sender += "<br/>公司名称：{0}".format(sender_dict.company_name)
        if sender_dict.company_address:
            sender += "<br/>公司地址：{0}".format(sender_dict.company_address)
        if sender_dict.name:
            sender += "<br/>姓名：{0}".format(sender_dict.name)
        if sender_dict.mailbox:
            sender += "<br/>邮箱：{0}".format(sender_dict.mailbox)
        if sender_dict.fax:
            sender += "<br/>传真：{0}".format(sender_dict.fax)
        if sender_dict.phone:
            sender += "<br/>电话：{0}".format(sender_dict.phone)

        main_port.fill("receiver", receiver)
        main_port.fill("sender", sender)
        return Success(data=main_port)

