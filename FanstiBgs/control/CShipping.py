"""
本文件用于处理收运管理
create user: haobin12358
last update time: 2020-09-09
"""

import hashlib, datetime, requests, uuid, json
from flask import request, current_app
from ast import literal_eval

from FanstiBgs.extensions.params_validates import parameter_required
from FanstiBgs.extensions.request_handler import token_to_user_
from FanstiBgs.extensions.register_ext import db
from FanstiBgs.extensions.success_response import Success
from FanstiBgs.models.bgs_android import an_procedure, an_procedure_picture, an_checklist, an_check_history, \
    an_check_history_item
from FanstiBgs.models.bgs_cloud import t_bgs_main_single_number, t_bgs_un, t_bgs_shipper_consignee_info, t_bgs_file, \
    t_bgs_odd_number, t_bgs_un_pack

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

        # 获取三天以内数据， 精确到天就好 2020/9/14中午增加需求
        three_days_ago = datetime.datetime.now() + datetime.timedelta(days=-3)
        order_time = datetime.datetime(three_days_ago.year, three_days_ago.month, three_days_ago.day, 0, 0, 0)
        filter_args.append(t_bgs_main_single_number.order_time > order_time)

        main_port = t_bgs_main_single_number.query.filter(*filter_args).all_with_page()
        page_num = int(request.args.get("page_num")) or 1
        page_size = int(request.args.get("page_size")) or 15
        i = 1
        for port in main_port:
            un_list = t_bgs_un.query.filter(t_bgs_un.master_number == port.id).all()
            port.fill("un_count", len(un_list))
            # 判断已检查
            hisory = an_check_history.query.filter(an_check_history.master_id == port.id).all()
            if hisory:
                port_status = "已检查{0}次".format(len(hisory))
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

        # 签名图片改为url-2020/10/9逻辑
        name_picture_id = main_port.name_image_file
        bgs_file = t_bgs_file.query.filter(t_bgs_file.f_id == name_picture_id, t_bgs_file.file_class == "signature").first()
        if bgs_file:
            main_port.fill("statement_url", bgs_file.file_src)
        else:
            main_port.fill("statement_url", "")

        # 包装性能单改url-2020/10/10逻辑
        bgs_file2 = t_bgs_file.query.filter(t_bgs_file.f_id == name_picture_id,
                                           t_bgs_file.file_class == "performanceSheet").first()
        if bgs_file2:
            main_port.fill("packaging_url", bgs_file.file_src)
        else:
            main_port.fill("packaging_url", "")

        un_list = t_bgs_un.query.filter(t_bgs_un.master_number == args.get("id")).all()
        odd_number_list = []
        for un in un_list:
            if un.odd_number and un.odd_number not in odd_number_list:
                odd_number_list.append(un.odd_number)
        part_port = []
        if odd_number_list:
            for odd_number in odd_number_list:
                odd_dict = {}
                odd_name_dict = t_bgs_odd_number.query.filter(t_bgs_odd_number.id == odd_number).first_("分单号信息未找到")
                odd_dict["odd_number"] = odd_name_dict.odd_number
                un_list_by_odd_master = t_bgs_un.query.filter(t_bgs_un.master_number == args.get("id"),
                                                              t_bgs_un.odd_number == odd_number).all()
                for un_dict in un_list_by_odd_master:
                    un_pack_list = t_bgs_un_pack.query.filter(t_bgs_un_pack.oddNumberId == odd_number,
                                                              t_bgs_un_pack.unNumberId == un_dict.id).all()
                    un_pack = ""
                    for un_pack_dict in un_pack_list:
                        if un_pack_dict.status == "Overpack":
                            un_pack += "<strong>Proper Shipping Name</strong><br/>{0} {1} {2} {3}"\
                                .format(un_pack_dict.product_name or " ", un_pack_dict.TechnicalName or " ",
                                        un_pack_dict.productNameSelect or " ", un_pack_dict.difference or " ")
                            if un_dict.MAIN_DANGEROUS_ID:
                                if un_pack:
                                    un_pack += "<br/>"
                                un_pack += "<strong>Class or Division(Subsidiary Risk)</strong><br/>{0}".format(un_dict.MAIN_DANGEROUS_ID)
                                if un_dict.SECOND_DANGEROUS_IDA:
                                    un_pack += "({0})".format(un_dict.SECOND_DANGEROUS_IDA)
                            if un_dict.packaging_grade:
                                if un_pack:
                                    un_pack += "<br/>"
                                un_pack += "<strong>Packing Group</strong><br/>{0}".format(un_dict.packaging_grade)
                            if un_pack:
                                un_pack += "<br/>"
                            un_pack += "<strong>Quantity and type of packing</strong><br/>"
                            if un_pack_dict.packNumber and un_pack_dict.unit:
                                un_pack += un_pack_dict.packNumber
                                if un_pack_dict.material:
                                    un_pack += " "
                                    un_pack += literal_eval(un_pack_dict.material)[1]
                                if un_pack_dict.weight:
                                    un_pack += " "
                                    un_pack += un_pack_dict.weight
                                if un_pack_dict.unit:
                                    un_pack += " "
                                    un_pack += un_pack_dict.unit
                                if un_pack_dict.packInfo:
                                    un_pack += "({0})".format(un_pack_dict.packInfo)
                            elif un_pack_dict.packInfo:
                                un_pack += un_pack_dict.packInfo
                            if un_dict.packaging_instruction:
                                if un_pack:
                                    un_pack += "<br/>"
                                un_pack += "<strong>Packing Inst.</strong><br/>{0}".format(un_dict.packaging_instruction)
                        elif un_pack_dict.status == "All Packed In One1":
                            un_pack += "<strong>Proper Shipping Name</strong><br/>{0} {1} {2} {3}" \
                                .format(un_pack_dict.product_name or " ", un_pack_dict.TechnicalName or " ",
                                        un_pack_dict.productNameSelect or " ", un_pack_dict.difference or " ")
                            if un_dict.MAIN_DANGEROUS_ID:
                                if un_pack:
                                    un_pack += "<br/>"
                                un_pack += "<strong>Class or Division(Subsidiary Risk)</strong><br/>{0}".format(un_dict.MAIN_DANGEROUS_ID)
                                if un_dict.SECOND_DANGEROUS_IDA:
                                    un_pack += "({0})".format(un_dict.SECOND_DANGEROUS_IDA)
                            if un_dict.packaging_grade:
                                if un_pack:
                                    un_pack += "<br/>"
                                un_pack += "<strong>Packing Group</strong><br/>{0}".format(un_dict.packaging_grade)
                            if un_pack:
                                un_pack += "<br/>"
                            un_pack += "<strong>Quantity and type of packing</strong><br/>"
                            if un_pack_dict.packNumber and un_pack_dict.unit:
                                un_pack += un_pack_dict.packNumber
                                if un_pack_dict.material:
                                    un_pack += " "
                                    un_pack += literal_eval(un_pack_dict.material)[1]
                                if un_pack_dict.weight:
                                    un_pack += " "
                                    un_pack += un_pack_dict.weight
                                if un_pack_dict.unit:
                                    un_pack += " "
                                    un_pack += un_pack_dict.unit
                                if un_pack_dict.packInfo:
                                    un_pack += "({0})".format(un_pack_dict.packInfo)
                            elif un_pack_dict.packInfo:
                                un_pack += un_pack_dict.packInfo
                            if un_dict.packaging_instruction:
                                if un_pack:
                                    un_pack += "<br/>"
                                un_pack += "<strong>Packing Inst.</strong><br/>{0}".format(un_dict.packaging_instruction)
                        elif un_pack_dict.status == "Not Operated":
                            un_pack += "<strong>Proper Shipping Name</strong><br/>{0} {1} {2} {3}" \
                                .format(un_pack_dict.product_name or " ", un_pack_dict.TechnicalName or " ",
                                        un_pack_dict.productNameSelect or " ", un_pack_dict.difference or " ")
                            if un_dict.MAIN_DANGEROUS_ID:
                                if un_pack:
                                    un_pack += "<br/>"
                                un_pack += "<strong>Class or Division(Subsidiary Risk)</strong><br/>{0}".format(un_dict.MAIN_DANGEROUS_ID)
                                if un_dict.SECOND_DANGEROUS_IDA:
                                    un_pack += "({0})".format(un_dict.SECOND_DANGEROUS_IDA)
                            if un_dict.packaging_grade:
                                if un_pack:
                                    un_pack += "<br/>"
                                un_pack += "<strong>Packing Group</strong><br/>{0}".format(un_dict.packaging_grade)
                            if un_pack:
                                un_pack += "<br/>"
                            un_pack += "<strong>Quantity and type of packing</strong><br/>"
                            if un_dict.packNumber and un_dict.unit:
                                un_pack += un_dict.packNumber
                                if un_dict.material:
                                    un_pack += " "
                                    un_pack += literal_eval(un_dict.material)[1]
                                if un_dict.weight:
                                    un_pack += " "
                                    un_pack += un_dict.weight
                                if un_dict.unit:
                                    un_pack += " "
                                    un_pack += un_dict.unit
                            if un_dict.packaging_instruction:
                                if un_pack:
                                    un_pack += "<br/>"
                                un_pack += "Packing Inst.</strong><br/>{0}".format(un_dict.packaging_instruction)

                    if not un_pack:
                        shipping_name = un_dict.product_Name
                        if un_dict.TechnicalName:
                            shipping_name += " "
                            shipping_name += un_dict.TechnicalName
                        if un_dict.productNameSelect:
                            shipping_name += " "
                            shipping_name += un_dict.productNameSelect
                        if un_dict.difference:
                            shipping_name += " "
                            shipping_name += un_dict.difference
                        division = un_dict.MAIN_DANGEROUS_ID
                        if un_dict.SECOND_DANGEROUS_IDA:
                            division += "({0})".format(un_dict.SECOND_DANGEROUS_IDA)
                        packing_group = un_dict.packaging_grade
                        quantity = un_dict.packNumber
                        if un_dict.material:
                            quantity += " "
                            quantity += literal_eval(un_dict.material)[1]
                        if un_dict.weight:
                            quantity += " "
                            quantity += un_dict.weight
                        if un_dict.unit:
                            quantity += " "
                            quantity += un_dict.unit
                        packing_inst = un_dict.packaging_instruction
                        if shipping_name:
                            un_pack += "<strong>Proper Shipping Name</strong><br/>{0}<br/>".format(shipping_name)
                        else:
                            un_pack += "<strong>Proper Shipping Name</strong><br/>{0}<br/>".format("None")
                        if division:
                            un_pack += "<strong>Class or Division(Subsidiary Risk)</strong><br/>{0}<br/>".format(
                                division)
                        else:
                            un_pack += "<strong>Class or Division(Subsidiary Risk)</strong><br/>{0}<br/>".format("None")
                        if packing_group:
                            un_pack += "<strong>Packing Group</strong><br/>{0}<br/>".format(packing_group)
                        else:
                            un_pack += "<strong>Packing Group</strong><br/>{0}<br/>".format("None")
                        if quantity:
                            un_pack += "<strong>Quantity and type of packing</strong><br/>{0}<br/>".format(quantity)
                        else:
                            un_pack += "<strong>Quantity and type of packing</strong><br/>{0}<br/>".format("None")
                        if packing_inst:
                            un_pack += "<strong>Packing Inst.</strong><br/>{0}".format(packing_inst)
                        else:
                            un_pack += "<strong>Packing Inst.</strong><br/>{0}".format("None")
                    un_dict.fill("un_pack", un_pack)

                odd_dict["un_list"] = un_list_by_odd_master
                odd_dict["length"] = len(un_list_by_odd_master)
                part_port.append(odd_dict)
        else:
            odd_dict = {}
            odd_dict["odd_number"] = "No separate order"
            un_list_by_odd_master = t_bgs_un.query.filter(t_bgs_un.master_number == args.get("id")).all()
            for un_dict in un_list_by_odd_master:
                un_pack_list = t_bgs_un_pack.query.filter(t_bgs_un_pack.unNumberId == un_dict.id).all()
                un_pack = ""
                for un_pack_dict in un_pack_list:
                    if un_pack:
                        un_pack += "<br/>"
                    if un_pack_dict.status == "Overpack":
                        un_pack += "<strong>Proper Shipping Name</strong><br/>{0} {1} {2} {3}" \
                            .format(un_pack_dict.product_name or " ", un_pack_dict.TechnicalName or " ",
                                    un_pack_dict.productNameSelect or " ", un_pack_dict.difference or " ")
                        if un_dict.MAIN_DANGEROUS_ID:
                            if un_pack:
                                un_pack += "<br/>"
                            un_pack += "<strong>Class or Division(Subsidiary Risk)</strong><br/>{0}".format(un_dict.MAIN_DANGEROUS_ID)
                            if un_dict.SECOND_DANGEROUS_IDA:
                                un_pack += "({0})".format(un_dict.SECOND_DANGEROUS_IDA)
                        if un_dict.packaging_grade:
                            if un_pack:
                                un_pack += "<br/>"
                            un_pack += "<strong>Packing Group</strong><br/>{0}".format(un_dict.packaging_grade)

                        if un_pack:
                            un_pack += "<br/>"
                        un_pack += "<strong>Quantity and type of packing</strong><br/>"
                        if un_pack_dict.packNumber and un_pack_dict.unit:
                            un_pack += un_pack_dict.packNumber
                            if un_pack_dict.material:
                                un_pack += " "
                                un_pack += literal_eval(un_pack_dict.material)[1]
                            if un_pack_dict.weight:
                                un_pack += " "
                                un_pack += un_pack_dict.weight
                            if un_pack_dict.unit:
                                un_pack += " "
                                un_pack += un_pack_dict.unit
                            if un_pack_dict.packInfo:
                                un_pack += "({0})".format(un_pack_dict.packInfo)
                        elif un_pack_dict.packInfo:
                            un_pack += un_pack_dict.packInfo
                        if un_dict.packaging_instruction:
                            if un_pack:
                                un_pack += "<br/>"
                            un_pack += "<strong>Packing Inst.</strong><br/>{0}".format(un_dict.packaging_instruction)
                    elif un_pack_dict.status == "All Packed In One1":
                        un_pack += "<strong>Proper Shipping Name</strong><br/>{0} {1} {2} {3}" \
                            .format(un_pack_dict.product_name or " ", un_pack_dict.TechnicalName or " ",
                                    un_pack_dict.productNameSelect or " ", un_pack_dict.difference or " ")
                        if un_dict.MAIN_DANGEROUS_ID:
                            if un_pack:
                                un_pack += "<br/>"
                            un_pack += "<strong>Class or Division(Subsidiary Risk)</strong><br/>{0}".format(un_dict.MAIN_DANGEROUS_ID)
                            if un_dict.SECOND_DANGEROUS_IDA:
                                un_pack += "({0})".format(un_dict.SECOND_DANGEROUS_IDA)
                        if un_dict.packaging_grade:
                            if un_pack:
                                un_pack += "<br/>"
                            un_pack += "<strong>Packing Group</strong><br/>{0}".format(un_dict.packaging_grade)
                        if un_pack:
                            un_pack += "<br/>"
                        un_pack += "<strong>Quantity and type of packing</strong><br/>"
                        if un_pack_dict.packNumber and un_pack_dict.unit:
                            un_pack += un_pack_dict.packNumber
                            if un_pack_dict.material:
                                un_pack += " "
                                un_pack += literal_eval(un_pack_dict.material)[1]
                            if un_pack_dict.weight:
                                un_pack += " "
                                un_pack += un_pack_dict.weight
                            if un_pack_dict.unit:
                                un_pack += " "
                                un_pack += un_pack_dict.unit
                            if un_pack_dict.packInfo:
                                un_pack += "({0})".format(un_pack_dict.packInfo)
                        elif un_pack_dict.packInfo:
                            un_pack += un_pack_dict.packInfo
                        if un_dict.packaging_instruction:
                            if un_pack:
                                un_pack += "<br/>"
                            un_pack += "<strong>Packing Inst.</strong><br/>{0}".format(un_dict.packaging_instruction)
                    elif un_pack_dict.status == "Not Operated":
                        un_pack += "<strong>Proper Shipping Name</strong><br/>{0} {1} {2} {3}" \
                            .format(un_pack_dict.product_name or " ", un_pack_dict.TechnicalName or " ",
                                    un_pack_dict.productNameSelect or " ", un_pack_dict.difference or " ")
                        if un_dict.MAIN_DANGEROUS_ID:
                            if un_pack:
                                un_pack += "<br/>"
                            un_pack += "<strong>Class or Division(Subsidiary Risk)</strong><br/>{0}".format(un_dict.MAIN_DANGEROUS_ID)
                            if un_dict.SECOND_DANGEROUS_IDA:
                                un_pack += "({0})".format(un_dict.SECOND_DANGEROUS_IDA)
                        if un_dict.packaging_grade:
                            if un_pack:
                                un_pack += "<br/>"
                            un_pack += "<strong>Packing Group</strong><br/>{0}".format(un_dict.packaging_grade)
                        if un_pack:
                            un_pack += "<br/>"
                        un_pack += "<strong>Quantity and type of packing</strong><br/>"
                        if un_dict.packNumber and un_dict.unit:
                            un_pack += un_dict.packNumber
                            if un_dict.material:
                                un_pack += " "
                                un_pack += literal_eval(un_dict.material)[1]
                            if un_dict.weight:
                                un_pack += " "
                                un_pack += un_dict.weight
                            if un_dict.unit:
                                un_pack += " "
                                un_pack += un_dict.unit
                        if un_dict.packaging_instruction:
                            if un_pack:
                                un_pack += "<br/>"
                            un_pack += "<strong>Packing Inst.</strong><br/>{0}".format(un_dict.packaging_instruction)
                if not un_pack:
                    shipping_name = un_dict.product_Name
                    if un_dict.TechnicalName:
                        shipping_name += " "
                        shipping_name += un_dict.TechnicalName
                    if un_dict.productNameSelect:
                        shipping_name += " "
                        shipping_name += un_dict.productNameSelect
                    if un_dict.difference:
                        shipping_name += " "
                        shipping_name += un_dict.difference
                    division = un_dict.MAIN_DANGEROUS_ID
                    if un_dict.SECOND_DANGEROUS_IDA:
                        division += "({0})".format(un_dict.SECOND_DANGEROUS_IDA)
                    packing_group = un_dict.packaging_grade
                    quantity = un_dict.packNumber
                    if un_dict.material:
                        quantity += " "
                        quantity += literal_eval(un_dict.material)[1]
                    if un_dict.weight:
                        quantity += " "
                        quantity += un_dict.weight
                    if un_dict.unit:
                        quantity += " "
                        quantity += un_dict.unit
                    packing_inst = un_dict.packaging_instruction
                    if shipping_name:
                        un_pack += "<strong>Proper Shipping Name</strong><br/>{0}<br/>".format(shipping_name)
                    else:
                        un_pack += "<strong>Proper Shipping Name</strong><br/>{0}<br/>".format("None")
                    if division:
                        un_pack += "<strong>Class or Division(Subsidiary Risk)</strong><br/>{0}<br/>".format(division)
                    else:
                        un_pack += "<strong>Class or Division(Subsidiary Risk)</strong><br/>{0}<br/>".format("None")
                    if packing_group:
                        un_pack += "<strong>Packing Group</strong><br/>{0}<br/>".format(packing_group)
                    else:
                        un_pack += "<strong>Packing Group</strong><br/>{0}<br/>".format("None")
                    if quantity:
                        un_pack += "<strong>Quantity and type of packing</strong><br/>{0}<br/>".format(quantity)
                    else:
                        un_pack += "<strong>Quantity and type of packing</strong><br/>{0}<br/>".format("None")
                    if packing_inst:
                        un_pack += "<strong>Packing Inst.</strong><br/>{0}".format(packing_inst)
                    else:
                        un_pack += "<strong>Packing Inst.</strong><br/>{0}".format("None")
                un_dict.fill("un_pack", un_pack)

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
            receiver += "<strong>Country：</strong>{0}".format(receiver_dict.country)
        if receiver_dict.city:
            receiver += "<br/><strong>City：</strong>{0}".format(receiver_dict.city)
        if receiver_dict.company_name:
            receiver += "<br/><strong>Company Name：</strong>{0}".format(receiver_dict.company_name)
        if receiver_dict.company_address:
            receiver += "<br/><strong>Company Address：</strong>{0}".format(receiver_dict.company_address)
        if receiver_dict.name:
            receiver += "<br/><strong>Name：</strong>{0}".format(receiver_dict.name)
        if receiver_dict.mailbox:
            receiver += "<br/><strong>Email：</strong>{0}".format(receiver_dict.mailbox)
        if receiver_dict.fax:
            receiver += "<br/><strong>Fox：</strong>{0}".format(receiver_dict.fax)
        if receiver_dict.phone:
            receiver += "<br/><strong>Tel.：</strong>{0}".format(receiver_dict.phone)
        sender = ""
        if sender_dict.country:
            sender += "<strong>Country：</strong>{0}".format(sender_dict.country)
        if sender_dict.city:
            sender += "<br/><strong>City：</strong>{0}".format(sender_dict.city)
        if sender_dict.company_name:
            sender += "<br/><strong>Company Name：</strong>{0}".format(sender_dict.company_name)
        if sender_dict.company_address:
            sender += "<br/><strong>Company Address：</strong>{0}".format(sender_dict.company_address)
        if sender_dict.name:
            sender += "<br/><strong>Name：</strong>{0}".format(sender_dict.name)
        if sender_dict.mailbox:
            sender += "<br/><strong>Email：</strong>{0}".format(sender_dict.mailbox)
        if sender_dict.fax:
            sender += "<br/><strong>Fox：</strong>{0}".format(sender_dict.fax)
        if sender_dict.phone:
            sender += "<br/><strong>Tel.：</strong>{0}".format(sender_dict.phone)

        main_port.fill("receiver", receiver)
        main_port.fill("sender", sender)

        count = 0
        first_check = an_check_history.query.filter(an_check_history.master_id == args.get("id"),
                                                    an_check_history.times == "first").first()
        if first_check:
            count += 1

        second_check = an_check_history.query.filter(an_check_history.master_id == args.get("id"),
                                                     an_check_history.times == "second").first()
        if second_check:
            count += 1
        main_port.fill("check_times", count)

        return Success(data=main_port)

    def upload_photos(self):
        """
        上传货运图片
        """
        data = parameter_required(("shipping_front", "shipping_diaforward", "shipping_diaback", "shipping_back", "whole"))

        for url in data.get("shipping_front"):
            with db.auto_commit():
                url_instance = an_procedure_picture.query.filter(an_procedure_picture.file_url == url) \
                    .first_("该图片未上传成功， 请重新上传")
                url_instance.update({
                    "procedure_id": request.args.get("id")
                }, null="not")

        for url in data.get("shipping_diaforward"):
            with db.auto_commit():
                url_instance = an_procedure_picture.query.filter(an_procedure_picture.file_url == url) \
                    .first_("该图片未上传成功， 请重新上传")
                url_instance.update({
                    "procedure_id": request.args.get("id")
                }, null="not")

        for url in data.get("shipping_diaback"):
            with db.auto_commit():
                url_instance = an_procedure_picture.query.filter(an_procedure_picture.file_url == url) \
                    .first_("该图片未上传成功， 请重新上传")
                url_instance.update({
                    "procedure_id": request.args.get("id")
                }, null="not")

        for url in data.get("shipping_back"):
            with db.auto_commit():
                url_instance = an_procedure_picture.query.filter(an_procedure_picture.file_url == url) \
                    .first_("该图片未上传成功， 请重新上传")
                url_instance.update({
                    "procedure_id": request.args.get("id")
                }, null="not")

        for url in data.get("whole"):
            with db.auto_commit():
                url_instance = an_procedure_picture.query.filter(an_procedure_picture.file_url == url) \
                    .first_("该图片未上传成功， 请重新上传")
                url_instance.update({
                    "procedure_id": request.args.get("id")
                }, null="not")

        return Success(message="上传成功")

    def get_photos(self):
        """
        获取货运图片
        """
        args = parameter_required(("id", "token"))
        main_port = t_bgs_main_single_number.query.filter(t_bgs_main_single_number.id == args.get("id")).first()
        response = {}
        response["master_number"] = main_port.master_number
        response["port_of_departure"] = main_port.port_of_departure
        response["picture_list"] = {}
        response["picture_list"]["shipping_front"] = {}
        response["picture_list"]["shipping_diaforward"] = {}
        response["picture_list"]["shipping_diaback"] = {}
        response["picture_list"]["shipping_back"] = {}
        response["picture_list"]["whole"] = {}
        # 正面
        shipping_front = an_procedure_picture.query.filter(an_procedure_picture.type == "shipping_front",
                                                           an_procedure_picture.procedure_id == args.get("id")).all()
        url_list = []
        for url in shipping_front:
            response["picture_list"]["shipping_front"]["user_name"] = url.user_name
            response["picture_list"]["shipping_front"]["createtime"] = url.createtime
            url_list.append(url.file_url)
        response["picture_list"]["shipping_front"]["url_list"] = url_list
        # 斜前
        shipping_front = an_procedure_picture.query.filter(an_procedure_picture.type == "shipping_diaforward",
                                                           an_procedure_picture.procedure_id == args.get("id")).all()
        url_list = []
        for url in shipping_front:
            response["picture_list"]["shipping_diaforward"]["user_name"] = url.user_name
            response["picture_list"]["shipping_diaforward"]["createtime"] = url.createtime
            url_list.append(url.file_url)
        response["picture_list"]["shipping_diaforward"]["url_list"] = url_list
        # 斜后
        shipping_front = an_procedure_picture.query.filter(an_procedure_picture.type == "shipping_diaback",
                                                           an_procedure_picture.procedure_id == args.get("id")).all()
        url_list = []
        for url in shipping_front:
            response["picture_list"]["shipping_diaback"]["user_name"] = url.user_name
            response["picture_list"]["shipping_diaback"]["createtime"] = url.createtime
            url_list.append(url.file_url)
        response["picture_list"]["shipping_diaback"]["url_list"] = url_list
        # 后面
        shipping_front = an_procedure_picture.query.filter(an_procedure_picture.type == "shipping_back",
                                                           an_procedure_picture.procedure_id == args.get("id")).all()
        url_list = []
        for url in shipping_front:
            response["picture_list"]["shipping_back"]["user_name"] = url.user_name
            response["picture_list"]["shipping_back"]["createtime"] = url.createtime
            url_list.append(url.file_url)
        response["picture_list"]["shipping_back"]["url_list"] = url_list
        # 整体
        shipping_front = an_procedure_picture.query.filter(an_procedure_picture.type == "whole",
                                                           an_procedure_picture.procedure_id == args.get("id")).all()
        url_list = []
        for url in shipping_front:
            response["picture_list"]["whole"]["user_name"] = url.user_name
            response["picture_list"]["whole"]["createtime"] = url.createtime
            url_list.append(url.file_url)
        response["picture_list"]["whole"]["url_list"] = url_list

        return Success(data=response)

    def get_checklist_type(self):

        """
        获取检查单类型
        """

        data = [
            {
                "type": "Radioactivity",
                "is_next": 1,
                "next": ["Radioactive", "Nonradiative"]
            },
            {
                "type": "Dry ice",
                "is_next": 0
            },
            {
                "type": "Lithium cell",
                "is_next": 0
            }
        ]
        return Success(data=data)

    def get_checklist_item(self):

        """
        获取检查单题目
        """

        args = parameter_required(("token", "check_type", "master_id"))

        items = an_checklist.query.filter(an_checklist.check_type == args.get("check_type"))\
            .order_by(an_checklist.check_no.asc()).all_with_page()

        first_check = an_check_history.query.filter(an_check_history.master_id == args.get("master_id"),
                                                    an_check_history.times == "first").first()
        if first_check:
            first_check_id = first_check.id
            if args.get("check_type") != first_check.check_type:
                return {
                    "status": 405,
                    "status_code": 405009,
                    "message": "请选择和第一次提交相同的检查单类型"
                }
        else:
            first_check_id = None

        second_check = an_check_history.query.filter(an_check_history.master_id == args.get("master_id"),
                                                    an_check_history.times == "second").first()
        check_items = []
        error_number = 0
        total_page = 1
        total_count = 0
        if first_check and second_check:
            second_check_id = second_check.id
            items = an_checklist.query.filter(an_checklist.check_type == args.get("check_type"))\
                .order_by(an_checklist.check_no.asc()).all()
            page_num = int(args.get("page_num")) or 1
            page_size = int(args.get("page_size")) or 15
            if len(items) % page_size == 0:
                total_page = len(items) / page_size
            else:
                total_page = int(len(items) / page_size) + 1
            total_count = len(items)
            for item in items:
                check_id = item.id
                first_item = an_check_history_item.query.filter(an_check_history_item.check_id == check_id,
                                                                an_check_history_item.history_id == first_check_id)\
                    .first()
                second_item = an_check_history_item.query.filter(an_check_history_item.check_id == check_id,
                                                                an_check_history_item.history_id == second_check_id) \
                    .first()
                if first_item.check_answer != second_item.check_answer:
                    check_items.append(item)
            error_number = len(check_items)
        else:
            second_check_id = None

        items = an_checklist.query.filter(an_checklist.check_type == args.get("check_type")) \
            .order_by(an_checklist.check_no.asc()).all_with_page()

        for item in items:
            item.fill("check_topic", "【{0}】\r\n{1}".format(item.check_genre, item.check_item))
            check_type = item.check_type
            check_no = item.check_no
            if str(check_no).split(".")[-1] == "0":
                check_no = str(int(check_no))
                item.check_no = str(int(check_no))
            else:
                check_no = str(check_no)
                item.check_no = str(check_no)

            check_message_dict = self.get_checklist_abo(check_no, check_type, args.get("master_id"))
            if check_message_dict["result"]:
                item.fill("answer", check_message_dict["result"])
            else:
                item.fill("answer", None)
            if first_check_id:
                first_check_item = an_check_history_item.query.filter(
                    an_check_history_item.history_id == first_check_id,
                    an_check_history_item.check_id == item.id) \
                    .first()
                item.answer = first_check_item.check_answer
                item.fill("first_answer", first_check_item.check_answer)
            else:
                item.fill("first_answer", None)

            if check_message_dict["message"]:
                item.fill("show_message", "301")
            else:
                item.fill("show_message", "302")

            if second_check_id:
                second_check_item = an_check_history_item.query.filter(
                    an_check_history_item.history_id == second_check_id,
                    an_check_history_item.check_id == item.id)\
                    .first()
                item.fill("second_answer", second_check_item.check_answer)
            else:
                item.fill("second_answer", None)

        if first_check and second_check:

            return {
                "status": 200,
                "message": "获取检查单题目成功",
                "data": items,
                "total_page": total_page,
                "total_count": total_count,
                "error_count": error_number
            }
        else:
            return Success(data=items)

    def make_checklist_history(self):
        """
        提交检查单结果
        """
        args = request.args.to_dict()
        data = json.loads(request.data)
        user = token_to_user_(args.get("token"))
        user_id = user.id
        user_name = user.username
        history = an_check_history.query.filter(an_check_history.master_id == args.get("master_id")).all()
        if len(history) == 0:
            times = "first"
        elif len(history) == 1:
            times = "second"
        else:
            times = "last"
        history_id = str(uuid.uuid1())
        history_dict = {
            "id": history_id,
            "check_type": args.get("check_type"),
            "user_id": user_id,
            "user_name": user_name,
            "createtime": datetime.datetime.now(),
            "master_id": args.get("master_id"),
            "times": times
        }
        check_list_items = an_checklist.query.filter(an_checklist.check_type == args.get("check_type")).all()
        if len(check_list_items) != len(data):
            return {
                "status": 405,
                "status_code": 405009,
                "message": "题目提交不完整"
            }
        else:
            check_no_list = []
            with db.auto_commit():
                for item in data:
                    if item.get("check_no") not in check_no_list:
                        check_no_list.append(item.get("check_no"))
                    if not item.get("answer"):
                        return {
                            "status": 405,
                            "status_code": 405010,
                            "message": "第{0}项未选择".format(item.get("check_no"))
                        }
                    if len(item.get("check_no").split(".")) == 2:
                        check_no = float(item.get("check_no"))
                    else:
                        check_no = int(item.get("check_no"))
                    history_item_dict = {
                        "id": str(uuid.uuid1()),
                        "check_id": item.get("id"),
                        "history_id": history_id,
                        "check_no": check_no,
                        "check_item": item.get("check_item"),
                        "check_genre": item.get("check_genre"),
                        "check_answer": item.get("answer")
                    }
                    history_item_instance = an_check_history_item.create(history_item_dict)
                    db.session.add(history_item_instance)
                if len(check_list_items) != len(check_no_list):
                    return {
                        "status": 405,
                        "status_code": 405009,
                        "message": "题目提交不完整"
                    }
                history_instance = an_check_history.create(history_dict)
                db.session.add(history_instance)

            # TODO 切换正式环境后修改
            # return Success(message="提交成功")
            with db.auto_commit():
                if times == "second":
                    # TODO 替换正常格式的html_body
                    html_body = ""
                    if args.get("check_type") == "Nonradiative":
                        with open("E:\\FanstiBgs\\FanstiBgs\\non-radioactive.html", 'r', encoding='utf-8') as f:
                            html_body = f.read()
                        check_history = an_check_history.query.filter(
                            an_check_history.master_id == args.get("master_id"),
                            an_check_history.times == "second") \
                            .first_("数据库异常")
                        history_id = check_history.id
                        main_port = t_bgs_main_single_number.query.filter(
                            t_bgs_main_single_number.id == args.get("master_id")).first()
                        title_0 = datetime.datetime.now().year
                        title_1 = datetime.datetime.now().year - 2020 + 61
                        title_2 = datetime.datetime.now().year
                        title_3 = main_port.master_number
                        title_4 = main_port.port_of_departure or "PEK"
                        title_5 = main_port.destination_port or "No Available"

                        item_1 = an_check_history_item.query.filter(an_check_history_item.history_id == history_id,
                                                                    an_check_history_item.check_no == 1).first()
                        if item_1.check_answer == "YES":
                            title_6 = "√"
                            title_7 = "<br/>"
                            title_8 = "<br/>"
                        elif item_1.check_answer == "NO":
                            title_6 = "<br/>"
                            title_7 = "√"
                            title_8 = "<br/>"
                        else:
                            title_6 = "<br/>"
                            title_7 = "<br/>"
                            title_8 = "√"

                        item_2 = an_check_history_item.query.filter(an_check_history_item.history_id == history_id,
                                                                    an_check_history_item.check_no == 2).first()
                        if item_2.check_answer == "YES":
                            title_9 = "√"
                            title_10 = "<br/>"
                            title_11 = "<br/>"
                        elif item_2.check_answer == "NO":
                            title_9 = "<br/>"
                            title_10 = "√"
                            title_11 = "<br/>"
                        else:
                            title_9 = "<br/>"
                            title_10 = "<br/>"
                            title_11 = "√"

                        item_3 = an_check_history_item.query.filter(an_check_history_item.history_id == history_id,
                                                                    an_check_history_item.check_no == 3).first()
                        if item_3.check_answer == "YES":
                            title_12 = "√"
                            title_13 = "<br/>"
                            title_14 = "<br/>"
                        elif item_3.check_answer == "NO":
                            title_12 = "<br/>"
                            title_13 = "√"
                            title_14 = "<br/>"
                        else:
                            title_12 = "<br/>"
                            title_13 = "<br/>"
                            title_14 = "√"

                        item_4 = an_check_history_item.query.filter(an_check_history_item.history_id == history_id,
                                                                    an_check_history_item.check_no == 4).first()
                        if item_4.check_answer == "YES":
                            title_15 = "√"
                            title_16 = "<br/>"
                            title_17 = "<br/>"
                        elif item_4.check_answer == "NO":
                            title_15 = "<br/>"
                            title_16 = "√"
                            title_17 = "<br/>"
                        else:
                            title_15 = "<br/>"
                            title_16 = "<br/>"
                            title_17 = "√"

                        item_5 = an_check_history_item.query.filter(an_check_history_item.history_id == history_id,
                                                                    an_check_history_item.check_no == 5).first()
                        if item_5.check_answer == "YES":
                            title_18 = "√"
                            title_19 = "<br/>"
                            title_20 = "<br/>"
                        elif item_5.check_answer == "NO":
                            title_18 = "<br/>"
                            title_19 = "√"
                            title_20 = "<br/>"
                        else:
                            title_18 = "<br/>"
                            title_19 = "<br/>"
                            title_20 = "√"

                        item_6 = an_check_history_item.query.filter(an_check_history_item.history_id == history_id,
                                                                    an_check_history_item.check_no == 6).first()
                        if item_6.check_answer == "YES":
                            title_21 = "√"
                            title_22 = "<br/>"
                            title_23 = "<br/>"
                        elif item_6.check_answer == "NO":
                            title_21 = "<br/>"
                            title_22 = "√"
                            title_23 = "<br/>"
                        else:
                            title_21 = "<br/>"
                            title_22 = "<br/>"
                            title_23 = "√"

                        item_7 = an_check_history_item.query.filter(an_check_history_item.history_id == history_id,
                                                                    an_check_history_item.check_no == 7).first()
                        if item_7.check_answer == "YES":
                            title_24 = "√"
                            title_25 = "<br/>"
                            title_16 = "<br/>"
                        elif item_7.check_answer == "NO":
                            title_24 = "<br/>"
                            title_25 = "√"
                            title_26 = "<br/>"
                        else:
                            title_24 = "<br/>"
                            title_25 = "<br/>"
                            title_26 = "√"

                        item_8 = an_check_history_item.query.filter(an_check_history_item.history_id == history_id,
                                                                    an_check_history_item.check_no == 8).first()
                        if item_8.check_answer == "YES":
                            title_27 = "√"
                            title_28 = "<br/>"
                            title_29 = "<br/>"
                        elif item_8.check_answer == "NO":
                            title_27 = "<br/>"
                            title_28 = "√"
                            title_29 = "<br/>"
                        else:
                            title_27 = "<br/>"
                            title_28 = "<br/>"
                            title_29 = "√"

                        item_9 = an_check_history_item.query.filter(an_check_history_item.history_id == history_id,
                                                                    an_check_history_item.check_no == 9).first()
                        if item_9.check_answer == "YES":
                            title_30 = "√"
                            title_31 = "<br/>"
                            title_32 = "<br/>"
                        elif item_9.check_answer == "NO":
                            title_30 = "<br/>"
                            title_31 = "√"
                            title_32 = "<br/>"
                        else:
                            title_30 = "<br/>"
                            title_31 = "<br/>"
                            title_32 = "√"

                        item_10 = an_check_history_item.query.filter(an_check_history_item.history_id == history_id,
                                                                    an_check_history_item.check_no == 10).first()
                        if item_10.check_answer == "YES":
                            title_33 = "√"
                            title_34 = "<br/>"
                            title_35 = "<br/>"
                        elif item_10.check_answer == "NO":
                            title_33 = "<br/>"
                            title_34 = "√"
                            title_35 = "<br/>"
                        else:
                            title_33 = "<br/>"
                            title_34 = "<br/>"
                            title_35 = "√"

                        item_11 = an_check_history_item.query.filter(an_check_history_item.history_id == history_id,
                                                                    an_check_history_item.check_no == 11).first()
                        if item_11.check_answer == "YES":
                            title_36 = "√"
                            title_37 = "<br/>"
                            title_38 = "<br/>"
                        elif item_11.check_answer == "NO":
                            title_36 = "<br/>"
                            title_37 = "√"
                            title_38 = "<br/>"
                        else:
                            title_36 = "<br/>"
                            title_37 = "<br/>"
                            title_38 = "√"

                        item_12 = an_check_history_item.query.filter(an_check_history_item.history_id == history_id,
                                                                    an_check_history_item.check_no == 12).first()
                        if item_12.check_answer == "YES":
                            title_39 = "√"
                            title_40 = "<br/>"
                            title_41 = "<br/>"
                        elif item_12.check_answer == "NO":
                            title_39 = "<br/>"
                            title_40 = "√"
                            title_41 = "<br/>"
                        else:
                            title_39 = "<br/>"
                            title_40 = "<br/>"
                            title_41 = "√"

                        item_13 = an_check_history_item.query.filter(an_check_history_item.history_id == history_id,
                                                                    an_check_history_item.check_no == 13).first()
                        if item_13.check_answer == "YES":
                            title_42 = "√"
                            title_43 = "<br/>"
                            title_44 = "<br/>"
                        elif item_13.check_answer == "NO":
                            title_42 = "<br/>"
                            title_43 = "√"
                            title_44 = "<br/>"
                        else:
                            title_42 = "<br/>"
                            title_43 = "<br/>"
                            title_44 = "√"

                        item_14 = an_check_history_item.query.filter(an_check_history_item.history_id == history_id,
                                                                    an_check_history_item.check_no == 14).first()
                        if item_14.check_answer == "YES":
                            title_45 = "√"
                            title_46 = "<br/>"
                            title_47 = "<br/>"
                        elif item_14.check_answer == "NO":
                            title_45 = "<br/>"
                            title_46 = "√"
                            title_47 = "<br/>"
                        else:
                            title_45 = "<br/>"
                            title_46 = "<br/>"
                            title_47 = "√"

                        item_15 = an_check_history_item.query.filter(an_check_history_item.history_id == history_id,
                                                                    an_check_history_item.check_no == 15).first()
                        if item_15.check_answer == "YES":
                            title_48 = "√"
                            title_49 = "<br/>"
                            title_50 = "<br/>"
                        elif item_15.check_answer == "NO":
                            title_48 = "<br/>"
                            title_49 = "√"
                            title_50 = "<br/>"
                        else:
                            title_48 = "<br/>"
                            title_49 = "<br/>"
                            title_50 = "√"

                        item_16 = an_check_history_item.query.filter(an_check_history_item.history_id == history_id,
                                                                    an_check_history_item.check_no == 16.1).first()
                        if item_16.check_answer == "YES":
                            title_51 = "√"
                            title_52 = "<br/>"
                            title_53 = "<br/>"
                        elif item_16.check_answer == "NO":
                            title_51 = "<br/>"
                            title_52 = "√"
                            title_53 = "<br/>"
                        else:
                            title_51 = "<br/>"
                            title_52 = "<br/>"
                            title_53 = "√"

                        item_17 = an_check_history_item.query.filter(an_check_history_item.history_id == history_id,
                                                                    an_check_history_item.check_no == 16.2).first()
                        if item_17.check_answer == "YES":
                            title_54 = "√"
                            title_55 = "<br/>"
                            title_56 = "<br/>"
                        elif item_17.check_answer == "NO":
                            title_54 = "<br/>"
                            title_55 = "√"
                            title_56 = "<br/>"
                        else:
                            title_54 = "<br/>"
                            title_55 = "<br/>"
                            title_56 = "√"

                        item_18 = an_check_history_item.query.filter(an_check_history_item.history_id == history_id,
                                                                    an_check_history_item.check_no == 16.3).first()
                        if item_18.check_answer == "YES":
                            title_57 = "√"
                            title_58 = "<br/>"
                            title_59 = "<br/>"
                        elif item_18.check_answer == "NO":
                            title_57 = "<br/>"
                            title_58 = "√"
                            title_59 = "<br/>"
                        else:
                            title_57 = "<br/>"
                            title_58 = "<br/>"
                            title_59 = "√"

                        item_19 = an_check_history_item.query.filter(an_check_history_item.history_id == history_id,
                                                                    an_check_history_item.check_no == 16.4).first()
                        if item_19.check_answer == "YES":
                            title_60 = "√"
                            title_61 = "<br/>"
                            title_62 = "<br/>"
                        elif item_19.check_answer == "NO":
                            title_60 = "<br/>"
                            title_61 = "√"
                            title_62 = "<br/>"
                        else:
                            title_60 = "<br/>"
                            title_61 = "<br/>"
                            title_62 = "√"

                        item_20 = an_check_history_item.query.filter(an_check_history_item.history_id == history_id,
                                                                    an_check_history_item.check_no == 17.1).first()
                        if item_20.check_answer == "YES":
                            title_63 = "√"
                            title_64 = "<br/>"
                            title_65 = "<br/>"
                        elif item_20.check_answer == "NO":
                            title_63 = "<br/>"
                            title_64 = "√"
                            title_65 = "<br/>"
                        else:
                            title_63 = "<br/>"
                            title_64 = "<br/>"
                            title_65 = "√"

                        item_21 = an_check_history_item.query.filter(an_check_history_item.history_id == history_id,
                                                                    an_check_history_item.check_no == 17.2).first()
                        if item_21.check_answer == "YES":
                            title_66 = "√"
                            title_67 = "<br/>"
                            title_68 = "<br/>"
                        elif item_21.check_answer == "NO":
                            title_66 = "<br/>"
                            title_67 = "√"
                            title_68 = "<br/>"
                        else:
                            title_66 = "<br/>"
                            title_67 = "<br/>"
                            title_68 = "√"

                        item_22 = an_check_history_item.query.filter(an_check_history_item.history_id == history_id,
                                                                    an_check_history_item.check_no == 17.3).first()
                        if item_22.check_answer == "YES":
                            title_69 = "√"
                            title_70 = "<br/>"
                            title_71 = "<br/>"
                        elif item_22.check_answer == "NO":
                            title_69 = "<br/>"
                            title_70 = "√"
                            title_71 = "<br/>"
                        else:
                            title_69 = "<br/>"
                            title_70 = "<br/>"
                            title_71 = "√"

                        item_23 = an_check_history_item.query.filter(an_check_history_item.history_id == history_id,
                                                                    an_check_history_item.check_no == 18).first()
                        if item_23.check_answer == "YES":
                            title_72 = "√"
                            title_73 = "<br/>"
                            title_74 = "<br/>"
                        elif item_23.check_answer == "NO":
                            title_72 = "<br/>"
                            title_73 = "√"
                            title_74 = "<br/>"
                        else:
                            title_72 = "<br/>"
                            title_73 = "<br/>"
                            title_74 = "√"

                        item_24 = an_check_history_item.query.filter(an_check_history_item.history_id == history_id,
                                                                    an_check_history_item.check_no == 19).first()
                        if item_24.check_answer == "YES":
                            title_75 = "√"
                            title_76 = "<br/>"
                            title_77 = "<br/>"
                        elif item_24.check_answer == "NO":
                            title_75 = "<br/>"
                            title_76 = "√"
                            title_77 = "<br/>"
                        else:
                            title_75 = "<br/>"
                            title_76 = "<br/>"
                            title_77 = "√"

                        item_25 = an_check_history_item.query.filter(an_check_history_item.history_id == history_id,
                                                                    an_check_history_item.check_no == 20).first()
                        if item_25.check_answer == "YES":
                            title_78 = "√"
                            title_79 = "<br/>"
                            title_80 = "<br/>"
                        elif item_25.check_answer == "NO":
                            title_78 = "<br/>"
                            title_79 = "√"
                            title_80 = "<br/>"
                        else:
                            title_78 = "<br/>"
                            title_79 = "<br/>"
                            title_80 = "√"

                        item_26 = an_check_history_item.query.filter(an_check_history_item.history_id == history_id,
                                                                    an_check_history_item.check_no == 21).first()
                        if item_26.check_answer == "YES":
                            title_81 = "√"
                            title_82 = "<br/>"
                            title_83 = "<br/>"
                        elif item_26.check_answer == "NO":
                            title_81 = "<br/>"
                            title_82 = "√"
                            title_83 = "<br/>"
                        else:
                            title_81 = "<br/>"
                            title_82 = "<br/>"
                            title_83 = "√"

                        item_27 = an_check_history_item.query.filter(an_check_history_item.history_id == history_id,
                                                                    an_check_history_item.check_no == 22).first()
                        if item_27.check_answer == "YES":
                            title_84 = "√"
                            title_85 = "<br/>"
                            title_86 = "<br/>"
                        elif item_27.check_answer == "NO":
                            title_84 = "<br/>"
                            title_85 = "√"
                            title_86 = "<br/>"
                        else:
                            title_84 = "<br/>"
                            title_85 = "<br/>"
                            title_86 = "√"

                        item_28 = an_check_history_item.query.filter(an_check_history_item.history_id == history_id,
                                                                    an_check_history_item.check_no == 23).first()
                        if item_28.check_answer == "YES":
                            title_87 = "√"
                            title_88 = "<br/>"
                            title_89 = "<br/>"
                        elif item_28.check_answer == "NO":
                            title_87 = "<br/>"
                            title_88 = "√"
                            title_89 = "<br/>"
                        else:
                            title_87 = "<br/>"
                            title_88 = "<br/>"
                            title_89 = "√"

                        item_29 = an_check_history_item.query.filter(an_check_history_item.history_id == history_id,
                                                                    an_check_history_item.check_no == 24).first()
                        if item_29.check_answer == "YES":
                            title_90 = "√"
                            title_91 = "<br/>"
                            title_92 = "<br/>"
                        elif item_29.check_answer == "NO":
                            title_90 = "<br/>"
                            title_91 = "√"
                            title_92 = "<br/>"
                        else:
                            title_90 = "<br/>"
                            title_91 = "<br/>"
                            title_92 = "√"

                        item_30 = an_check_history_item.query.filter(an_check_history_item.history_id == history_id,
                                                                    an_check_history_item.check_no == 25).first()
                        if item_30.check_answer == "YES":
                            title_93 = "√"
                            title_94 = "<br/>"
                            title_95 = "<br/>"
                        elif item_30.check_answer == "NO":
                            title_93 = "<br/>"
                            title_94 = "√"
                            title_95 = "<br/>"
                        else:
                            title_93 = "<br/>"
                            title_94 = "<br/>"
                            title_95 = "√"

                        item_31 = an_check_history_item.query.filter(an_check_history_item.history_id == history_id,
                                                                    an_check_history_item.check_no == 26).first()
                        if item_31.check_answer == "YES":
                            title_96 = "√"
                            title_97 = "<br/>"
                            title_98 = "<br/>"
                        elif item_31.check_answer == "NO":
                            title_96 = "<br/>"
                            title_97 = "√"
                            title_98 = "<br/>"
                        else:
                            title_96 = "<br/>"
                            title_97 = "<br/>"
                            title_98 = "√"

                        item_32 = an_check_history_item.query.filter(an_check_history_item.history_id == history_id,
                                                                    an_check_history_item.check_no == 27).first()
                        if item_32.check_answer == "YES":
                            title_99 = "√"
                            title_100 = "<br/>"
                            title_101 = "<br/>"
                        elif item_32.check_answer == "NO":
                            title_99 = "<br/>"
                            title_100 = "√"
                            title_101 = "<br/>"
                        else:
                            title_99 = "<br/>"
                            title_100 = "<br/>"
                            title_101 = "√"

                        item_33 = an_check_history_item.query.filter(an_check_history_item.history_id == history_id,
                                                                    an_check_history_item.check_no == 28).first()
                        if item_33.check_answer == "YES":
                            title_102 = "√"
                            title_103 = "<br/>"
                            title_104 = "<br/>"
                        elif item_33.check_answer == "NO":
                            title_102 = "<br/>"
                            title_103 = "√"
                            title_104 = "<br/>"
                        else:
                            title_102 = "<br/>"
                            title_103 = "<br/>"
                            title_104 = "√"

                        item_34 = an_check_history_item.query.filter(an_check_history_item.history_id == history_id,
                                                                    an_check_history_item.check_no == 29).first()
                        if item_34.check_answer == "YES":
                            title_105 = "√"
                            title_106 = "<br/>"
                            title_107 = "<br/>"
                        elif item_34.check_answer == "NO":
                            title_105 = "<br/>"
                            title_106 = "√"
                            title_107 = "<br/>"
                        else:
                            title_105 = "<br/>"
                            title_106 = "<br/>"
                            title_107 = "√"

                        item_35 = an_check_history_item.query.filter(an_check_history_item.history_id == history_id,
                                                                    an_check_history_item.check_no == 30).first()
                        if item_35.check_answer == "YES":
                            title_108 = "√"
                            title_109 = "<br/>"
                            title_110 = "<br/>"
                        elif item_35.check_answer == "NO":
                            title_108 = "<br/>"
                            title_109 = "√"
                            title_110 = "<br/>"
                        else:
                            title_108 = "<br/>"
                            title_109 = "<br/>"
                            title_110 = "√"

                        item_36 = an_check_history_item.query.filter(an_check_history_item.history_id == history_id,
                                                                    an_check_history_item.check_no == 31.1).first()
                        if item_36.check_answer == "YES":
                            title_111 = "√"
                            title_112 = "<br/>"
                            title_113 = "<br/>"
                        elif item_36.check_answer == "NO":
                            title_111 = "<br/>"
                            title_112 = "√"
                            title_113 = "<br/>"
                        else:
                            title_111 = "<br/>"
                            title_112 = "<br/>"
                            title_113 = "√"

                        item_37 = an_check_history_item.query.filter(an_check_history_item.history_id == history_id,
                                                                    an_check_history_item.check_no == 31.2).first()
                        if item_37.check_answer == "YES":
                            title_114 = "√"
                            title_115 = "<br/>"
                            title_116 = "<br/>"
                        elif item_37.check_answer == "NO":
                            title_114 = "<br/>"
                            title_115 = "√"
                            title_116 = "<br/>"
                        else:
                            title_114 = "<br/>"
                            title_115 = "<br/>"
                            title_116 = "√"

                        item_38 = an_check_history_item.query.filter(an_check_history_item.history_id == history_id,
                                                                    an_check_history_item.check_no == 31.3).first()
                        if item_38.check_answer == "YES":
                            title_117 = "√"
                            title_118 = "<br/>"
                            title_119 = "<br/>"
                        elif item_38.check_answer == "NO":
                            title_117 = "<br/>"
                            title_118 = "√"
                            title_119 = "<br/>"
                        else:
                            title_117 = "<br/>"
                            title_118 = "<br/>"
                            title_119 = "√"

                        item_39 = an_check_history_item.query.filter(an_check_history_item.history_id == history_id,
                                                                    an_check_history_item.check_no == 31.4).first()
                        if item_39.check_answer == "YES":
                            title_120 = "√"
                            title_121 = "<br/>"
                            title_122 = "<br/>"
                        elif item_39.check_answer == "NO":
                            title_120 = "<br/>"
                            title_121 = "√"
                            title_122 = "<br/>"
                        else:
                            title_120 = "<br/>"
                            title_121 = "<br/>"
                            title_122 = "√"

                        item_40 = an_check_history_item.query.filter(an_check_history_item.history_id == history_id,
                                                                    an_check_history_item.check_no == 31.5).first()
                        if item_40.check_answer == "YES":
                            title_123 = "√"
                            title_124 = "<br/>"
                            title_125 = "<br/>"
                        elif item_40.check_answer == "NO":
                            title_123 = "<br/>"
                            title_124 = "√"
                            title_125 = "<br/>"
                        else:
                            title_123 = "<br/>"
                            title_124 = "<br/>"
                            title_125 = "√"

                        item_41 = an_check_history_item.query.filter(an_check_history_item.history_id == history_id,
                                                                    an_check_history_item.check_no == 32).first()
                        if item_41.check_answer == "YES":
                            title_126 = "√"
                            title_127 = "<br/>"
                            title_128 = "<br/>"
                        elif item_41.check_answer == "NO":
                            title_126 = "<br/>"
                            title_127 = "√"
                            title_128 = "<br/>"
                        else:
                            title_126 = "<br/>"
                            title_127 = "<br/>"
                            title_128 = "√"

                        item_42 = an_check_history_item.query.filter(an_check_history_item.history_id == history_id,
                                                                    an_check_history_item.check_no == 33).first()
                        if item_42.check_answer == "YES":
                            title_129 = "√"
                            title_130 = "<br/>"
                            title_131 = "<br/>"
                        elif item_42.check_answer == "NO":
                            title_129 = "<br/>"
                            title_130 = "√"
                            title_131 = "<br/>"
                        else:
                            title_129 = "<br/>"
                            title_130 = "<br/>"
                            title_131 = "√"

                        item_43 = an_check_history_item.query.filter(an_check_history_item.history_id == history_id,
                                                                    an_check_history_item.check_no == 34).first()
                        if item_43.check_answer == "YES":
                            title_132 = "√"
                            title_133 = "<br/>"
                            title_134 = "<br/>"
                        elif item_43.check_answer == "NO":
                            title_132 = "<br/>"
                            title_133 = "√"
                            title_134 = "<br/>"
                        else:
                            title_132 = "<br/>"
                            title_133 = "<br/>"
                            title_134 = "√"

                        item_44 = an_check_history_item.query.filter(an_check_history_item.history_id == history_id,
                                                                    an_check_history_item.check_no == 35).first()
                        if item_44.check_answer == "YES":
                            title_135 = "√"
                            title_136 = "<br/>"
                            title_137 = "<br/>"
                        elif item_44.check_answer == "NO":
                            title_135 = "<br/>"
                            title_136 = "√"
                            title_137 = "<br/>"
                        else:
                            title_135 = "<br/>"
                            title_136 = "<br/>"
                            title_137 = "√"

                        item_45 = an_check_history_item.query.filter(an_check_history_item.history_id == history_id,
                                                                    an_check_history_item.check_no == 36).first()
                        if item_45.check_answer == "YES":
                            title_138 = "√"
                            title_139 = "<br/>"
                            title_140 = "<br/>"
                        elif item_45.check_answer == "NO":
                            title_138 = "<br/>"
                            title_139 = "√"
                            title_140 = "<br/>"
                        else:
                            title_138 = "<br/>"
                            title_139 = "<br/>"
                            title_140 = "√"

                        item_46 = an_check_history_item.query.filter(an_check_history_item.history_id == history_id,
                                                                    an_check_history_item.check_no == 37).first()
                        if item_46.check_answer == "YES":
                            title_141 = "√"
                            title_142 = "<br/>"
                            title_143 = "<br/>"
                        elif item_46.check_answer == "NO":
                            title_141 = "<br/>"
                            title_142 = "√"
                            title_143 = "<br/>"
                        else:
                            title_141 = "<br/>"
                            title_142 = "<br/>"
                            title_143 = "√"

                        item_47 = an_check_history_item.query.filter(an_check_history_item.history_id == history_id,
                                                                    an_check_history_item.check_no == 38).first()
                        if item_47.check_answer == "YES":
                            title_144 = "√"
                            title_145 = "<br/>"
                            title_146 = "<br/>"
                        elif item_47.check_answer == "NO":
                            title_144 = "<br/>"
                            title_145 = "√"
                            title_146 = "<br/>"
                        else:
                            title_144 = "<br/>"
                            title_145 = "<br/>"
                            title_146 = "√"

                        item_48 = an_check_history_item.query.filter(an_check_history_item.history_id == history_id,
                                                                    an_check_history_item.check_no == 39).first()
                        if item_48.check_answer == "YES":
                            title_147 = "√"
                            title_148 = "<br/>"
                            title_149 = "<br/>"
                        elif item_48.check_answer == "NO":
                            title_147 = "<br/>"
                            title_148 = "√"
                            title_149 = "<br/>"
                        else:
                            title_147 = "<br/>"
                            title_148 = "<br/>"
                            title_149 = "√"

                        item_49 = an_check_history_item.query.filter(an_check_history_item.history_id == history_id,
                                                                    an_check_history_item.check_no == 40).first()
                        if item_49.check_answer == "YES":
                            title_150 = "√"
                            title_151 = "<br/>"
                            title_152 = "<br/>"
                        elif item_49.check_answer == "NO":
                            title_150 = "<br/>"
                            title_151 = "√"
                            title_152 = "<br/>"
                        else:
                            title_150 = "<br/>"
                            title_151 = "<br/>"
                            title_152 = "√"

                        item_50 = an_check_history_item.query.filter(an_check_history_item.history_id == history_id,
                                                                    an_check_history_item.check_no == 41).first()
                        if item_50.check_answer == "YES":
                            title_153 = "√"
                            title_154 = "<br/>"
                            title_155 = "<br/>"
                        elif item_50.check_answer == "NO":
                            title_153 = "<br/>"
                            title_154 = "√"
                            title_155 = "<br/>"
                        else:
                            title_153 = "<br/>"
                            title_154 = "<br/>"
                            title_155 = "√"

                        item_51 = an_check_history_item.query.filter(an_check_history_item.history_id == history_id,
                                                                    an_check_history_item.check_no == 42).first()
                        if item_51.check_answer == "YES":
                            title_156 = "√"
                            title_157 = "<br/>"
                            title_158 = "<br/>"
                        elif item_51.check_answer == "NO":
                            title_156 = "<br/>"
                            title_157 = "√"
                            title_158 = "<br/>"
                        else:
                            title_156 = "<br/>"
                            title_157 = "<br/>"
                            title_158 = "√"

                        item_52 = an_check_history_item.query.filter(an_check_history_item.history_id == history_id,
                                                                    an_check_history_item.check_no == 43).first()
                        if item_52.check_answer == "YES":
                            title_159 = "√"
                            title_160 = "<br/>"
                            title_161 = "<br/>"
                        elif item_52.check_answer == "NO":
                            title_159 = "<br/>"
                            title_160 = "√"
                            title_161 = "<br/>"
                        else:
                            title_159 = "<br/>"
                            title_160 = "<br/>"
                            title_161 = "√"

                        item_53 = an_check_history_item.query.filter(an_check_history_item.history_id == history_id,
                                                                    an_check_history_item.check_no == 44).first()
                        if item_53.check_answer == "YES":
                            title_162 = "√"
                            title_163 = "<br/>"
                            title_164 = "<br/>"
                        elif item_53.check_answer == "NO":
                            title_162 = "<br/>"
                            title_163 = "√"
                            title_164 = "<br/>"
                        else:
                            title_162 = "<br/>"
                            title_163 = "<br/>"
                            title_164 = "√"

                        item_54 = an_check_history_item.query.filter(an_check_history_item.history_id == history_id,
                                                                    an_check_history_item.check_no == 45).first()
                        if item_54.check_answer == "YES":
                            title_165 = "√"
                            title_166 = "<br/>"
                            title_167 = "<br/>"
                        elif item_54.check_answer == "NO":
                            title_165 = "<br/>"
                            title_166 = "√"
                            title_167 = "<br/>"
                        else:
                            title_165 = "<br/>"
                            title_166 = "<br/>"
                            title_167 = "√"

                        item_55 = an_check_history_item.query.filter(an_check_history_item.history_id == history_id,
                                                                    an_check_history_item.check_no == 46).first()
                        if item_55.check_answer == "YES":
                            title_168 = "√"
                            title_169 = "<br/>"
                            title_170 = "<br/>"
                        elif item_55.check_answer == "NO":
                            title_168 = "<br/>"
                            title_169 = "√"
                            title_170 = "<br/>"
                        else:
                            title_168 = "<br/>"
                            title_169 = "<br/>"
                            title_170 = "√"

                        item_56 = an_check_history_item.query.filter(an_check_history_item.history_id == history_id,
                                                                    an_check_history_item.check_no == 47).first()
                        if item_56.check_answer == "YES":
                            title_171 = "√"
                            title_172 = "<br/>"
                            title_173 = "<br/>"
                        elif item_56.check_answer == "NO":
                            title_171 = "<br/>"
                            title_172 = "√"
                            title_173 = "<br/>"
                        else:
                            title_171 = "<br/>"
                            title_172 = "<br/>"
                            title_173 = "√"

                        item_57 = an_check_history_item.query.filter(an_check_history_item.history_id == history_id,
                                                                    an_check_history_item.check_no == 48).first()
                        if item_57.check_answer == "YES":
                            title_174 = "√"
                            title_175 = "<br/>"
                            title_176 = "<br/>"
                        elif item_57.check_answer == "NO":
                            title_174 = "<br/>"
                            title_175 = "√"
                            title_176 = "<br/>"
                        else:
                            title_174 = "<br/>"
                            title_175 = "<br/>"
                            title_176 = "√"

                        item_58 = an_check_history_item.query.filter(an_check_history_item.history_id == history_id,
                                                                    an_check_history_item.check_no == 49).first()
                        if item_58.check_answer == "YES":
                            title_177 = "√"
                            title_178 = "<br/>"
                            title_179 = "<br/>"
                        elif item_58.check_answer == "NO":
                            title_177 = "<br/>"
                            title_178 = "√"
                            title_179 = "<br/>"
                        else:
                            title_177 = "<br/>"
                            title_178 = "<br/>"
                            title_179 = "√"

                        item_59 = an_check_history_item.query.filter(an_check_history_item.history_id == history_id,
                                                                    an_check_history_item.check_no == 50).first()
                        if item_59.check_answer == "YES":
                            title_180 = "√"
                            title_181 = "<br/>"
                            title_182 = "<br/>"
                        elif item_59.check_answer == "NO":
                            title_180 = "<br/>"
                            title_181 = "√"
                            title_182 = "<br/>"
                        else:
                            title_180 = "<br/>"
                            title_181 = "<br/>"
                            title_182 = "√"

                        item_60 = an_check_history_item.query.filter(an_check_history_item.history_id == history_id,
                                                                    an_check_history_item.check_no == 51).first()
                        if item_60.check_answer == "YES":
                            title_183 = "√"
                            title_184 = "<br/>"
                            title_185 = "<br/>"
                        elif item_60.check_answer == "NO":
                            title_183 = "<br/>"
                            title_184 = "√"
                            title_185 = "<br/>"
                        else:
                            title_183 = "<br/>"
                            title_184 = "<br/>"
                            title_185 = "√"

                        item_61 = an_check_history_item.query.filter(an_check_history_item.history_id == history_id,
                                                                    an_check_history_item.check_no == 52).first()
                        if item_61.check_answer == "YES":
                            title_186 = "√"
                            title_187 = "<br/>"
                            title_188 = "<br/>"
                        elif item_61.check_answer == "NO":
                            title_186 = "<br/>"
                            title_187 = "√"
                            title_188 = "<br/>"
                        else:
                            title_186 = "<br/>"
                            title_187 = "<br/>"
                            title_188 = "√"

                        item_62 = an_check_history_item.query.filter(an_check_history_item.history_id == history_id,
                                                                    an_check_history_item.check_no == 53).first()
                        if item_62.check_answer == "YES":
                            title_189 = "√"
                            title_190 = "<br/>"
                            title_191 = "<br/>"
                        elif item_62.check_answer == "NO":
                            title_189 = "<br/>"
                            title_190 = "√"
                            title_191 = "<br/>"
                        else:
                            title_189 = "<br/>"
                            title_190 = "<br/>"
                            title_191 = "√"

                        title_192 = check_history.user_name
                        title_193 = main_port.port_of_departure or "PEK"
                        title_194 = check_history.user_name
                        title_195 = str(check_history.createtime.year) + "/" + str(check_history.createtime.month) + "/" \
                                    + str(check_history.createtime.day)
                        title_196 = str(check_history.createtime.hour) + ":" + str(check_history.createtime.minute) + ":" \
                                    + str(check_history.createtime.second)
                        html_body.format(
                            title_0, title_1, title_2, title_3, title_4, title_5, title_6, title_7, title_8, title_9,
                            title_10, title_11, title_12, title_13, title_14, title_15, title_16, title_17, title_18, title_19,
                            title_20, title_21, title_22, title_23, title_24, title_25, title_26, title_27, title_28, title_29,
                            title_30, title_31, title_32, title_33, title_34, title_35, title_36, title_37, title_38, title_39,
                            title_40, title_41, title_42, title_43, title_44, title_45, title_46, title_47, title_48, title_49,
                            title_50, title_51, title_52, title_53, title_54, title_55, title_56, title_57, title_58, title_59,
                            title_60, title_61, title_62, title_63, title_64, title_65, title_66, title_67, title_68, title_69,
                            title_70, title_71, title_72, title_73, title_74, title_75, title_76, title_77, title_78, title_79,
                            title_80, title_81, title_82, title_83, title_84, title_85, title_86, title_87, title_88, title_89,
                            title_90, title_91, title_92, title_93, title_94, title_95, title_96, title_97, title_98, title_99,
                            title_100, title_101, title_102, title_103, title_104, title_105, title_106, title_107, title_108, title_109,
                            title_110, title_111, title_112, title_113, title_114, title_115, title_116, title_117, title_118, title_119,
                            title_120, title_121, title_122, title_123, title_124, title_125, title_126, title_127, title_128, title_129,
                            title_130, title_131, title_132, title_133, title_134, title_135, title_136, title_137, title_138, title_139,
                            title_140, title_141, title_142, title_143, title_144, title_145, title_146, title_147, title_148, title_149,
                            title_150, title_151, title_152, title_153, title_154, title_155, title_156, title_157, title_158, title_159,
                            title_160, title_161, title_162, title_163, title_164, title_165, title_166, title_167, title_168, title_169,
                            title_170, title_171, title_172, title_173, title_174, title_175, title_176, title_177, title_178, title_179,
                            title_180, title_181, title_182, title_183, title_184, title_185, title_186, title_187, title_188, title_189,
                            title_190, title_191, title_192, title_193, title_194, title_195, title_196
                        )
                    elif args.get("check_type") == "Lithium cell":
                        with open("E:\\FanstiBgs\\FanstiBgs\\lithium.html", 'r', encoding='utf-8') as f:
                            html_body = f.read()
                        check_history = an_check_history.query.filter(
                            an_check_history.master_id == args.get("master_id"),
                            an_check_history.times == "second") \
                            .first_("数据库异常")
                        history_id = check_history.id
                        main_port = t_bgs_main_single_number.query.filter(
                            t_bgs_main_single_number.id == args.get("master_id")).first()
                        title_0 = main_port.master_number
                        title_43 = main_port.master_number
                        count_no = 0
                        item_1 = an_check_history_item.query.filter(an_check_history_item.history_id == history_id,
                                                                    an_check_history_item.check_no == 1).first()
                        if item_1.check_answer == "YES":
                            title_1 = "√"
                            title_2 = "<br/>"
                            title_3 = "<br/>"
                        elif item_1.check_answer == "NO":
                            title_1 = "<br/>"
                            title_2 = "√"
                            title_3 = "<br/>"
                            count_no += 1
                        else:
                            title_1 = "<br/>"
                            title_2 = "<br/>"
                            title_3 = "√"
                        item_2 = an_check_history_item.query.filter(an_check_history_item.history_id == history_id,
                                                                    an_check_history_item.check_no == 2).first()
                        if item_2.check_answer == "YES":
                            title_4 = "√"
                            title_5 = "<br/>"
                            title_6 = "<br/>"
                        elif item_2.check_answer == "NO":
                            title_4 = "<br/>"
                            title_5 = "√"
                            title_6 = "<br/>"
                            count_no += 1
                        else:
                            title_4 = "<br/>"
                            title_5 = "<br/>"
                            title_6 = "√"
                        item_3 = an_check_history_item.query.filter(an_check_history_item.history_id == history_id,
                                                                    an_check_history_item.check_no == 3).first()
                        if item_3.check_answer == "YES":
                            title_7 = "√"
                            title_8 = "<br/>"
                            title_9 = "<br/>"
                        elif item_3.check_answer == "NO":
                            title_7 = "<br/>"
                            title_8 = "√"
                            title_9 = "<br/>"
                            count_no += 1
                        else:
                            title_7 = "<br/>"
                            title_8 = "<br/>"
                            title_9 = "√"
                        item_4 = an_check_history_item.query.filter(an_check_history_item.history_id == history_id,
                                                                    an_check_history_item.check_no == 4).first()
                        if item_4.check_answer == "YES":
                            title_10 = "√"
                            title_11 = "<br/>"
                            title_12 = "<br/>"
                        elif item_4.check_answer == "NO":
                            title_10 = "<br/>"
                            title_11 = "√"
                            title_12 = "<br/>"
                            count_no += 1
                        else:
                            title_10 = "<br/>"
                            title_11 = "<br/>"
                            title_12 = "√"
                        item_5 = an_check_history_item.query.filter(an_check_history_item.history_id == history_id,
                                                                    an_check_history_item.check_no == 5).first()
                        if item_5.check_answer == "YES":
                            title_13 = "√"
                            title_14 = "<br/>"
                            title_15 = "<br/>"
                        elif item_5.check_answer == "NO":
                            title_13 = "<br/>"
                            title_14 = "√"
                            title_15 = "<br/>"
                            count_no += 1
                        else:
                            title_13 = "<br/>"
                            title_14 = "<br/>"
                            title_15 = "√"
                        item_6 = an_check_history_item.query.filter(an_check_history_item.history_id == history_id,
                                                                    an_check_history_item.check_no == 6).first()
                        if item_6.check_answer == "YES":
                            title_16 = "√"
                            title_17 = "<br/>"
                            title_18 = "<br/>"
                        elif item_6.check_answer == "NO":
                            title_16 = "<br/>"
                            title_17 = "√"
                            title_18 = "<br/>"
                            count_no += 1
                        else:
                            title_16 = "<br/>"
                            title_17 = "<br/>"
                            title_18 = "√"
                        item_7 = an_check_history_item.query.filter(an_check_history_item.history_id == history_id,
                                                                    an_check_history_item.check_no == 7).first()
                        if item_7.check_answer == "YES":
                            title_19 = "√"
                            title_20 = "<br/>"
                            title_21 = "<br/>"
                        elif item_7.check_answer == "NO":
                            title_19 = "<br/>"
                            title_20 = "√"
                            title_21 = "<br/>"
                            count_no += 1
                        else:
                            title_19 = "<br/>"
                            title_20 = "<br/>"
                            title_21 = "√"
                        item_8 = an_check_history_item.query.filter(an_check_history_item.history_id == history_id,
                                                                    an_check_history_item.check_no == 8).first()
                        if item_8.check_answer == "YES":
                            title_22 = "√"
                            title_23 = "<br/>"
                            title_24 = "<br/>"
                        elif item_8.check_answer == "NO":
                            title_22 = "<br/>"
                            title_23 = "√"
                            title_24 = "<br/>"
                            count_no += 1
                        else:
                            title_22 = "<br/>"
                            title_23 = "<br/>"
                            title_24 = "√"
                        item_9 = an_check_history_item.query.filter(an_check_history_item.history_id == history_id,
                                                                    an_check_history_item.check_no == 9).first()
                        if item_9.check_answer == "YES":
                            title_25 = "√"
                            title_26 = "<br/>"
                            title_27 = "<br/>"
                        elif item_9.check_answer == "NO":
                            title_25 = "<br/>"
                            title_26 = "√"
                            title_27 = "<br/>"
                            count_no += 1
                        else:
                            title_25 = "<br/>"
                            title_26 = "<br/>"
                            title_27 = "√"
                        item_10 = an_check_history_item.query.filter(an_check_history_item.history_id == history_id,
                                                                     an_check_history_item.check_no == 10).first()
                        if item_10.check_answer == "YES":
                            title_28 = "√"
                            title_29 = "<br/>"
                            title_30 = "<br/>"
                        elif item_10.check_answer == "NO":
                            title_28 = "<br/>"
                            title_29 = "√"
                            title_30 = "<br/>"
                            count_no += 1
                        else:
                            title_28 = "<br/>"
                            title_29 = "<br/>"
                            title_30 = "√"
                        item_11 = an_check_history_item.query.filter(an_check_history_item.history_id == history_id,
                                                                     an_check_history_item.check_no == 11).first()
                        if item_11.check_answer == "YES":
                            title_31 = "√"
                            title_32 = "<br/>"
                            title_33 = "<br/>"
                        elif item_11.check_answer == "NO":
                            title_31 = "<br/>"
                            title_32 = "√"
                            title_33 = "<br/>"
                            count_no += 1
                        else:
                            title_31 = "<br/>"
                            title_32 = "<br/>"
                            title_33 = "√"
                        item_12 = an_check_history_item.query.filter(an_check_history_item.history_id == history_id,
                                                                     an_check_history_item.check_no == 12).first()
                        if item_12.check_answer == "YES":
                            title_34 = "√"
                            title_35 = "<br/>"
                            title_36 = "<br/>"
                        elif item_12.check_answer == "NO":
                            title_34 = "<br/>"
                            title_35 = "√"
                            title_36 = "<br/>"
                            count_no += 1
                        else:
                            title_34 = "<br/>"
                            title_35 = "<br/>"
                            title_36 = "√"
                        item_13 = an_check_history_item.query.filter(an_check_history_item.history_id == history_id,
                                                                     an_check_history_item.check_no == 13).first()
                        if item_13.check_answer == "YES":
                            title_37 = "√"
                            title_38 = "<br/>"
                            title_39 = "<br/>"
                        elif item_13.check_answer == "NO":
                            title_37 = "<br/>"
                            title_38 = "√"
                            title_39 = "<br/>"
                            count_no += 1
                        else:
                            title_37 = "<br/>"
                            title_38 = "<br/>"
                            title_39 = "√"
                        item_14 = an_check_history_item.query.filter(an_check_history_item.history_id == history_id,
                                                                     an_check_history_item.check_no == 14).first()
                        if item_14.check_answer == "YES":
                            title_40 = "√"
                            title_41 = "<br/>"
                            title_42 = "<br/>"
                        elif item_14.check_answer == "NO":
                            title_40 = "<br/>"
                            title_41 = "√"
                            title_42 = "<br/>"
                            count_no += 1
                        else:
                            title_40 = "<br/>"
                            title_41 = "<br/>"
                            title_42 = "√"

                        if count_no > 0:
                            title_55 = "□"
                            title_56 = "√"
                        else:
                            title_56 = "□"
                            title_55 = "√"
                        title_58 = check_history.user_name
                        title_59 = str(check_history.createtime.year) + "/" + str(
                            check_history.createtime.month) + "/" + str(check_history.createtime.day)
                        title_61 = str(check_history.createtime.hour) + ":" + str(
                            check_history.createtime.minute) + ":" + str(check_history.createtime.second)
                        title_60 = check_history.user_name

                        html_body = html_body.format(title_0, title_43, title_1, title_2, title_3, title_4, title_5, title_6,
                                                     title_7, title_8, title_9, title_10, title_11, title_12, title_13,
                                                     title_14, title_15, title_16, title_17, title_18, title_19,
                                                     title_20, title_21, title_22, title_23, title_24, title_25,
                                                     title_26, title_27, title_28, title_29, title_30, title_31,
                                                     title_32, title_33, title_34, title_35, title_36, title_37,
                                                     title_38, title_39, title_40, title_41, title_42, title_55,
                                                     title_56, title_58, title_59, title_60, title_61)
                    elif args.get("check_type") == "Dry ice":
                        # TODO 根据不同服务器进行实际调整
                        with open("E:\\outpack\\FanstiBgs\\FanstiBgs\\dry_ice.html", 'r', encoding='utf-8') as f:
                            html_body = f.read()
                        check_history = an_check_history.query.filter(an_check_history.master_id == args.get("master_id"),
                                                                      an_check_history.times == "second")\
                            .first_("数据库异常")
                        history_id = check_history.id
                        title_0 = datetime.datetime.now().year
                        item_1 = an_check_history_item.query.filter(an_check_history_item.history_id == history_id,
                                                                    an_check_history_item.check_no == 1).first()
                        if item_1.check_answer == "YES":
                            title_1 = "√"
                            title_2 = "<br/>"
                            title_3 = "<br/>"
                        elif item_1.check_answer == "NO":
                            title_1 = "<br/>"
                            title_2 = "√"
                            title_3 = "<br/>"
                        else:
                            title_1 = "<br/>"
                            title_2 = "<br/>"
                            title_3 = "√"
                        item_2 = an_check_history_item.query.filter(an_check_history_item.history_id == history_id,
                                                                    an_check_history_item.check_no == 2).first()
                        if item_2.check_answer == "YES":
                            title_4 = "√"
                            title_5 = "<br/>"
                            title_6 = "<br/>"
                        elif item_2.check_answer == "NO":
                            title_4 = "<br/>"
                            title_5 = "√"
                            title_6 = "<br/>"
                        else:
                            title_4 = "<br/>"
                            title_5 = "<br/>"
                            title_6 = "√"
                        item_3 = an_check_history_item.query.filter(an_check_history_item.history_id == history_id,
                                                                    an_check_history_item.check_no == 3).first()
                        if item_3.check_answer == "YES":
                            title_7 = "√"
                            title_8 = "<br/>"
                            title_9 = "<br/>"
                        elif item_3.check_answer == "NO":
                            title_7 = "<br/>"
                            title_8 = "√"
                            title_9 = "<br/>"
                        else:
                            title_7 = "<br/>"
                            title_8 = "<br/>"
                            title_9 = "√"
                        item_4 = an_check_history_item.query.filter(an_check_history_item.history_id == history_id,
                                                                    an_check_history_item.check_no == 4).first()
                        if item_4.check_answer == "YES":
                            title_10 = "√"
                            title_11 = "<br/>"
                            title_12 = "<br/>"
                        elif item_4.check_answer == "NO":
                            title_10 = "<br/>"
                            title_11 = "√"
                            title_12 = "<br/>"
                        else:
                            title_10 = "<br/>"
                            title_11 = "<br/>"
                            title_12 = "√"
                        item_5 = an_check_history_item.query.filter(an_check_history_item.history_id == history_id,
                                                                    an_check_history_item.check_no == 5).first()
                        if item_5.check_answer == "YES":
                            title_13 = "√"
                            title_14 = "<br/>"
                            title_15 = "<br/>"
                        elif item_5.check_answer == "NO":
                            title_13 = "<br/>"
                            title_14 = "√"
                            title_15 = "<br/>"
                        else:
                            title_13 = "<br/>"
                            title_14 = "<br/>"
                            title_15 = "√"
                        item_6 = an_check_history_item.query.filter(an_check_history_item.history_id == history_id,
                                                                    an_check_history_item.check_no == 6).first()
                        if item_6.check_answer == "YES":
                            title_16 = "√"
                            title_17 = "<br/>"
                            title_18 = "<br/>"
                        elif item_6.check_answer == "NO":
                            title_16 = "<br/>"
                            title_17 = "√"
                            title_18 = "<br/>"
                        else:
                            title_16 = "<br/>"
                            title_17 = "<br/>"
                            title_18 = "√"
                        item_7 = an_check_history_item.query.filter(an_check_history_item.history_id == history_id,
                                                                    an_check_history_item.check_no == 7).first()
                        if item_7.check_answer == "YES":
                            title_19 = "√"
                            title_20 = "<br/>"
                            title_21 = "<br/>"
                        elif item_7.check_answer == "NO":
                            title_19 = "<br/>"
                            title_20 = "√"
                            title_21 = "<br/>"
                        else:
                            title_19 = "<br/>"
                            title_20 = "<br/>"
                            title_21 = "√"
                        item_8 = an_check_history_item.query.filter(an_check_history_item.history_id == history_id,
                                                                    an_check_history_item.check_no == 8).first()
                        if item_8.check_answer == "YES":
                            title_22 = "√"
                            title_23 = "<br/>"
                            title_24 = "<br/>"
                        elif item_8.check_answer == "NO":
                            title_22 = "<br/>"
                            title_23 = "√"
                            title_24 = "<br/>"
                        else:
                            title_22 = "<br/>"
                            title_23 = "<br/>"
                            title_24 = "√"
                        item_9 = an_check_history_item.query.filter(an_check_history_item.history_id == history_id,
                                                                    an_check_history_item.check_no == 9).first()
                        if item_9.check_answer == "YES":
                            title_25 = "√"
                            title_26 = "<br/>"
                            title_27 = "<br/>"
                        elif item_9.check_answer == "NO":
                            title_25 = "<br/>"
                            title_26 = "√"
                            title_27 = "<br/>"
                        else:
                            title_25 = "<br/>"
                            title_26 = "<br/>"
                            title_27 = "√"
                        item_10 = an_check_history_item.query.filter(an_check_history_item.history_id == history_id,
                                                                    an_check_history_item.check_no == 10).first()
                        if item_10.check_answer == "YES":
                            title_28 = "√"
                            title_29 = "<br/>"
                            title_30 = "<br/>"
                        elif item_10.check_answer == "NO":
                            title_28 = "<br/>"
                            title_29 = "√"
                            title_30 = "<br/>"
                        else:
                            title_28 = "<br/>"
                            title_29 = "<br/>"
                            title_30 = "√"
                        item_11 = an_check_history_item.query.filter(an_check_history_item.history_id == history_id,
                                                                    an_check_history_item.check_no == 11).first()
                        if item_11.check_answer == "YES":
                            title_31 = "√"
                            title_32 = "<br/>"
                            title_33 = "<br/>"
                        elif item_11.check_answer == "NO":
                            title_31 = "<br/>"
                            title_32 = "√"
                            title_33 = "<br/>"
                        else:
                            title_31 = "<br/>"
                            title_32 = "<br/>"
                            title_33 = "√"
                        item_12 = an_check_history_item.query.filter(an_check_history_item.history_id == history_id,
                                                                    an_check_history_item.check_no == 12).first()
                        if item_12.check_answer == "YES":
                            title_34 = "√"
                            title_35 = "<br/>"
                            title_36 = "<br/>"
                        elif item_12.check_answer == "NO":
                            title_34 = "<br/>"
                            title_35 = "√"
                            title_36 = "<br/>"
                        else:
                            title_34 = "<br/>"
                            title_35 = "<br/>"
                            title_36 = "√"
                        item_13 = an_check_history_item.query.filter(an_check_history_item.history_id == history_id,
                                                                    an_check_history_item.check_no == 13).first()
                        if item_13.check_answer == "YES":
                            title_37 = "√"
                            title_38 = "<br/>"
                            title_39 = "<br/>"
                        elif item_13.check_answer == "NO":
                            title_37 = "<br/>"
                            title_38 = "√"
                            title_39 = "<br/>"
                        else:
                            title_37 = "<br/>"
                            title_38 = "<br/>"
                            title_39 = "√"
                        item_14 = an_check_history_item.query.filter(an_check_history_item.history_id == history_id,
                                                                    an_check_history_item.check_no == 14).first()
                        if item_14.check_answer == "YES":
                            title_40 = "√"
                            title_41 = "<br/>"
                            title_42 = "<br/>"
                        elif item_14.check_answer == "NO":
                            title_40 = "<br/>"
                            title_41 = "√"
                            title_42 = "<br/>"
                        else:
                            title_40 = "<br/>"
                            title_41 = "<br/>"
                            title_42 = "√"
                        item_15 = an_check_history_item.query.filter(an_check_history_item.history_id == history_id,
                                                                    an_check_history_item.check_no == 15).first()
                        if item_15.check_answer == "YES":
                            title_43 = "√"
                            title_44 = "<br/>"
                            title_45 = "<br/>"
                        elif item_15.check_answer == "NO":
                            title_43 = "<br/>"
                            title_44 = "√"
                            title_45 = "<br/>"
                        else:
                            title_43 = "<br/>"
                            title_44 = "<br/>"
                            title_45 = "√"
                        item_16 = an_check_history_item.query.filter(an_check_history_item.history_id == history_id,
                                                                    an_check_history_item.check_no == 16).first()
                        if item_16.check_answer == "YES":
                            title_46 = "√"
                            title_47 = "<br/>"
                            title_48 = "<br/>"
                        elif item_16.check_answer == "NO":
                            title_46 = "<br/>"
                            title_47 = "√"
                            title_48 = "<br/>"
                        else:
                            title_46 = "<br/>"
                            title_47 = "<br/>"
                            title_48 = "√"
                        item_17 = an_check_history_item.query.filter(an_check_history_item.history_id == history_id,
                                                                    an_check_history_item.check_no == 17).first()
                        if item_17.check_answer == "YES":
                            title_49 = "√"
                            title_50 = "<br/>"
                            title_51 = "<br/>"
                        elif item_17.check_answer == "NO":
                            title_49 = "<br/>"
                            title_50 = "√"
                            title_51 = "<br/>"
                        else:
                            title_49 = "<br/>"
                            title_50 = "<br/>"
                            title_51 = "√"
                        item_18 = an_check_history_item.query.filter(an_check_history_item.history_id == history_id,
                                                                    an_check_history_item.check_no == 18).first()
                        if item_18.check_answer == "YES":
                            title_52 = "√"
                            title_53 = "<br/>"
                            title_54 = "<br/>"
                        elif item_18.check_answer == "NO":
                            title_52 = "<br/>"
                            title_53 = "√"
                            title_54 = "<br/>"
                        else:
                            title_52 = "<br/>"
                            title_53 = "<br/>"
                            title_54 = "√"

                        title_55 = check_history.user_name
                        main_port = t_bgs_main_single_number.query.filter(t_bgs_main_single_number.id == args.get("master_id")).first()
                        title_56 = main_port.port_of_departure or "PEK"
                        title_57 = main_port.destination_port or "暂无"
                        title_58 = str(check_history.createtime.year) + "/" + str(check_history.createtime.month) + "/" + str(check_history.createtime.day)
                        title_59 = str(check_history.createtime.hour) + ":" + str(check_history.createtime.minute) + ":" + str(check_history.createtime.second)
                        title_60 = datetime.datetime.now().year - 2020 + 61
                        title_61 = datetime.datetime.now().year

                        html_body = html_body.format(title_0, title_1, title_2, title_3, title_4, title_5, title_6,
                                                     title_7, title_8, title_9, title_10, title_11, title_12, title_13,
                                                     title_14, title_15, title_16, title_17, title_18, title_19,
                                                     title_20, title_21, title_22, title_23, title_24, title_25,
                                                     title_26, title_27, title_28, title_29, title_30, title_31,
                                                     title_32, title_33, title_34, title_35, title_36, title_37,
                                                     title_38, title_39, title_40, title_41, title_42, title_43,
                                                     title_44, title_45, title_46, title_47, title_48, title_49,
                                                     title_50, title_51, title_52, title_53, title_54, title_55,
                                                     title_56, title_57, title_58, title_59, title_60, title_61)
                    elif args.get("check_type") == "Radioactive":
                        with open("E:\\FanstiBgs\\FanstiBgs\\radioactive.html", 'r', encoding='utf-8') as f:
                            html_body = f.read()

                        check_history = an_check_history.query.filter(
                            an_check_history.master_id == args.get("master_id"),
                            an_check_history.times == "second") \
                            .first_("数据库异常")
                        history_id = check_history.id
                        main_port = t_bgs_main_single_number.query.filter(
                            t_bgs_main_single_number.id == args.get("master_id")).first()
                        title_0 = datetime.datetime.now().year
                        title_1 = datetime.datetime.now().year - 2020 + 61
                        title_2 = datetime.datetime.now().year
                        title_3 = main_port.master_number
                        title_4 = main_port.port_of_departure or "PEK"
                        title_5 = main_port.destination_port or "No Available"

                        item_1 = an_check_history_item.query.filter(an_check_history_item.history_id == history_id,
                                                                    an_check_history_item.check_no == 1).first()
                        if item_1.check_answer == "YES":
                            title_6 = "√"
                            title_7 = "<br/>"
                            title_8 = "<br/>"
                        elif item_1.check_answer == "NO":
                            title_6 = "<br/>"
                            title_7 = "√"
                            title_8 = "<br/>"
                        else:
                            title_6 = "<br/>"
                            title_7 = "<br/>"
                            title_8 = "√"

                        item_2 = an_check_history_item.query.filter(an_check_history_item.history_id == history_id,
                                                                    an_check_history_item.check_no == 2).first()
                        if item_2.check_answer == "YES":
                            title_9 = "√"
                            title_10 = "<br/>"
                            title_11 = "<br/>"
                        elif item_2.check_answer == "NO":
                            title_9 = "<br/>"
                            title_10 = "√"
                            title_11 = "<br/>"
                        else:
                            title_9 = "<br/>"
                            title_10 = "<br/>"
                            title_11 = "√"

                        item_3 = an_check_history_item.query.filter(an_check_history_item.history_id == history_id,
                                                                    an_check_history_item.check_no == 3).first()
                        if item_3.check_answer == "YES":
                            title_12 = "√"
                            title_13 = "<br/>"
                            title_14 = "<br/>"
                        elif item_3.check_answer == "NO":
                            title_12 = "<br/>"
                            title_13 = "√"
                            title_14 = "<br/>"
                        else:
                            title_12 = "<br/>"
                            title_13 = "<br/>"
                            title_14 = "√"

                        item_4 = an_check_history_item.query.filter(an_check_history_item.history_id == history_id,
                                                                    an_check_history_item.check_no == 4).first()
                        if item_4.check_answer == "YES":
                            title_15 = "√"
                            title_16 = "<br/>"
                            title_17 = "<br/>"
                        elif item_4.check_answer == "NO":
                            title_15 = "<br/>"
                            title_16 = "√"
                            title_17 = "<br/>"
                        else:
                            title_15 = "<br/>"
                            title_16 = "<br/>"
                            title_17 = "√"

                        item_5 = an_check_history_item.query.filter(an_check_history_item.history_id == history_id,
                                                                    an_check_history_item.check_no == 5).first()
                        if item_5.check_answer == "YES":
                            title_18 = "√"
                            title_19 = "<br/>"
                            title_20 = "<br/>"
                        elif item_5.check_answer == "NO":
                            title_18 = "<br/>"
                            title_19 = "√"
                            title_20 = "<br/>"
                        else:
                            title_18 = "<br/>"
                            title_19 = "<br/>"
                            title_20 = "√"

                        item_6 = an_check_history_item.query.filter(an_check_history_item.history_id == history_id,
                                                                    an_check_history_item.check_no == 6).first()
                        if item_6.check_answer == "YES":
                            title_21 = "√"
                            title_22 = "<br/>"
                            title_23 = "<br/>"
                        elif item_6.check_answer == "NO":
                            title_21 = "<br/>"
                            title_22 = "√"
                            title_23 = "<br/>"
                        else:
                            title_21 = "<br/>"
                            title_22 = "<br/>"
                            title_23 = "√"

                        item_7 = an_check_history_item.query.filter(an_check_history_item.history_id == history_id,
                                                                    an_check_history_item.check_no == 7).first()
                        if item_7.check_answer == "YES":
                            title_24 = "√"
                            title_25 = "<br/>"
                            title_16 = "<br/>"
                        elif item_7.check_answer == "NO":
                            title_24 = "<br/>"
                            title_25 = "√"
                            title_26 = "<br/>"
                        else:
                            title_24 = "<br/>"
                            title_25 = "<br/>"
                            title_26 = "√"

                        item_8 = an_check_history_item.query.filter(an_check_history_item.history_id == history_id,
                                                                    an_check_history_item.check_no == 8).first()
                        if item_8.check_answer == "YES":
                            title_27 = "√"
                            title_28 = "<br/>"
                            title_29 = "<br/>"
                        elif item_8.check_answer == "NO":
                            title_27 = "<br/>"
                            title_28 = "√"
                            title_29 = "<br/>"
                        else:
                            title_27 = "<br/>"
                            title_28 = "<br/>"
                            title_29 = "√"

                        item_9 = an_check_history_item.query.filter(an_check_history_item.history_id == history_id,
                                                                    an_check_history_item.check_no == 9).first()
                        if item_9.check_answer == "YES":
                            title_30 = "√"
                            title_31 = "<br/>"
                            title_32 = "<br/>"
                        elif item_9.check_answer == "NO":
                            title_30 = "<br/>"
                            title_31 = "√"
                            title_32 = "<br/>"
                        else:
                            title_30 = "<br/>"
                            title_31 = "<br/>"
                            title_32 = "√"

                        item_10 = an_check_history_item.query.filter(an_check_history_item.history_id == history_id,
                                                                     an_check_history_item.check_no == 10).first()
                        if item_10.check_answer == "YES":
                            title_33 = "√"
                            title_34 = "<br/>"
                            title_35 = "<br/>"
                        elif item_10.check_answer == "NO":
                            title_33 = "<br/>"
                            title_34 = "√"
                            title_35 = "<br/>"
                        else:
                            title_33 = "<br/>"
                            title_34 = "<br/>"
                            title_35 = "√"

                        item_11 = an_check_history_item.query.filter(an_check_history_item.history_id == history_id,
                                                                     an_check_history_item.check_no == 11).first()
                        if item_11.check_answer == "YES":
                            title_36 = "√"
                            title_37 = "<br/>"
                            title_38 = "<br/>"
                        elif item_11.check_answer == "NO":
                            title_36 = "<br/>"
                            title_37 = "√"
                            title_38 = "<br/>"
                        else:
                            title_36 = "<br/>"
                            title_37 = "<br/>"
                            title_38 = "√"

                        item_12 = an_check_history_item.query.filter(an_check_history_item.history_id == history_id,
                                                                     an_check_history_item.check_no == 12).first()
                        if item_12.check_answer == "YES":
                            title_39 = "√"
                            title_40 = "<br/>"
                            title_41 = "<br/>"
                        elif item_12.check_answer == "NO":
                            title_39 = "<br/>"
                            title_40 = "√"
                            title_41 = "<br/>"
                        else:
                            title_39 = "<br/>"
                            title_40 = "<br/>"
                            title_41 = "√"

                        item_13 = an_check_history_item.query.filter(an_check_history_item.history_id == history_id,
                                                                     an_check_history_item.check_no == 13).first()
                        if item_13.check_answer == "YES":
                            title_42 = "√"
                            title_43 = "<br/>"
                            title_44 = "<br/>"
                        elif item_13.check_answer == "NO":
                            title_42 = "<br/>"
                            title_43 = "√"
                            title_44 = "<br/>"
                        else:
                            title_42 = "<br/>"
                            title_43 = "<br/>"
                            title_44 = "√"

                        item_14 = an_check_history_item.query.filter(an_check_history_item.history_id == history_id,
                                                                     an_check_history_item.check_no == 14).first()
                        if item_14.check_answer == "YES":
                            title_45 = "√"
                            title_46 = "<br/>"
                            title_47 = "<br/>"
                        elif item_14.check_answer == "NO":
                            title_45 = "<br/>"
                            title_46 = "√"
                            title_47 = "<br/>"
                        else:
                            title_45 = "<br/>"
                            title_46 = "<br/>"
                            title_47 = "√"

                        item_15 = an_check_history_item.query.filter(an_check_history_item.history_id == history_id,
                                                                     an_check_history_item.check_no == 15).first()
                        if item_15.check_answer == "YES":
                            title_48 = "√"
                            title_49 = "<br/>"
                            title_50 = "<br/>"
                        elif item_15.check_answer == "NO":
                            title_48 = "<br/>"
                            title_49 = "√"
                            title_50 = "<br/>"
                        else:
                            title_48 = "<br/>"
                            title_49 = "<br/>"
                            title_50 = "√"

                        item_16 = an_check_history_item.query.filter(an_check_history_item.history_id == history_id,
                                                                     an_check_history_item.check_no == 16).first()
                        if item_16.check_answer == "YES":
                            title_51 = "√"
                            title_52 = "<br/>"
                            title_53 = "<br/>"
                        elif item_16.check_answer == "NO":
                            title_51 = "<br/>"
                            title_52 = "√"
                            title_53 = "<br/>"
                        else:
                            title_51 = "<br/>"
                            title_52 = "<br/>"
                            title_53 = "√"

                        item_17 = an_check_history_item.query.filter(an_check_history_item.history_id == history_id,
                                                                     an_check_history_item.check_no == 17).first()
                        if item_17.check_answer == "YES":
                            title_54 = "√"
                            title_55 = "<br/>"
                            title_56 = "<br/>"
                        elif item_17.check_answer == "NO":
                            title_54 = "<br/>"
                            title_55 = "√"
                            title_56 = "<br/>"
                        else:
                            title_54 = "<br/>"
                            title_55 = "<br/>"
                            title_56 = "√"

                        item_18 = an_check_history_item.query.filter(an_check_history_item.history_id == history_id,
                                                                     an_check_history_item.check_no == 18).first()
                        if item_18.check_answer == "YES":
                            title_57 = "√"
                            title_58 = "<br/>"
                            title_59 = "<br/>"
                        elif item_18.check_answer == "NO":
                            title_57 = "<br/>"
                            title_58 = "√"
                            title_59 = "<br/>"
                        else:
                            title_57 = "<br/>"
                            title_58 = "<br/>"
                            title_59 = "√"

                        item_19 = an_check_history_item.query.filter(an_check_history_item.history_id == history_id,
                                                                     an_check_history_item.check_no == 19).first()
                        if item_19.check_answer == "YES":
                            title_60 = "√"
                            title_61 = "<br/>"
                            title_62 = "<br/>"
                        elif item_19.check_answer == "NO":
                            title_60 = "<br/>"
                            title_61 = "√"
                            title_62 = "<br/>"
                        else:
                            title_60 = "<br/>"
                            title_61 = "<br/>"
                            title_62 = "√"

                        item_20 = an_check_history_item.query.filter(an_check_history_item.history_id == history_id,
                                                                     an_check_history_item.check_no == 20).first()
                        if item_20.check_answer == "YES":
                            title_63 = "√"
                            title_64 = "<br/>"
                            title_65 = "<br/>"
                        elif item_20.check_answer == "NO":
                            title_63 = "<br/>"
                            title_64 = "√"
                            title_65 = "<br/>"
                        else:
                            title_63 = "<br/>"
                            title_64 = "<br/>"
                            title_65 = "√"

                        item_21 = an_check_history_item.query.filter(an_check_history_item.history_id == history_id,
                                                                     an_check_history_item.check_no == 21).first()
                        if item_21.check_answer == "YES":
                            title_66 = "√"
                            title_67 = "<br/>"
                            title_68 = "<br/>"
                        elif item_21.check_answer == "NO":
                            title_66 = "<br/>"
                            title_67 = "√"
                            title_68 = "<br/>"
                        else:
                            title_66 = "<br/>"
                            title_67 = "<br/>"
                            title_68 = "√"

                        item_22 = an_check_history_item.query.filter(an_check_history_item.history_id == history_id,
                                                                     an_check_history_item.check_no == 22.1).first()
                        if item_22.check_answer == "YES":
                            title_69 = "√"
                            title_70 = "<br/>"
                            title_71 = "<br/>"
                        elif item_22.check_answer == "NO":
                            title_69 = "<br/>"
                            title_70 = "√"
                            title_71 = "<br/>"
                        else:
                            title_69 = "<br/>"
                            title_70 = "<br/>"
                            title_71 = "√"

                        item_23 = an_check_history_item.query.filter(an_check_history_item.history_id == history_id,
                                                                     an_check_history_item.check_no == 22.2).first()
                        if item_23.check_answer == "YES":
                            title_72 = "√"
                            title_73 = "<br/>"
                            title_74 = "<br/>"
                        elif item_23.check_answer == "NO":
                            title_72 = "<br/>"
                            title_73 = "√"
                            title_74 = "<br/>"
                        else:
                            title_72 = "<br/>"
                            title_73 = "<br/>"
                            title_74 = "√"

                        item_24 = an_check_history_item.query.filter(an_check_history_item.history_id == history_id,
                                                                     an_check_history_item.check_no == 22.3).first()
                        if item_24.check_answer == "YES":
                            title_75 = "√"
                            title_76 = "<br/>"
                            title_77 = "<br/>"
                        elif item_24.check_answer == "NO":
                            title_75 = "<br/>"
                            title_76 = "√"
                            title_77 = "<br/>"
                        else:
                            title_75 = "<br/>"
                            title_76 = "<br/>"
                            title_77 = "√"

                        item_25 = an_check_history_item.query.filter(an_check_history_item.history_id == history_id,
                                                                     an_check_history_item.check_no == 23).first()
                        if item_25.check_answer == "YES":
                            title_78 = "√"
                            title_79 = "<br/>"
                            title_80 = "<br/>"
                        elif item_25.check_answer == "NO":
                            title_78 = "<br/>"
                            title_79 = "√"
                            title_80 = "<br/>"
                        else:
                            title_78 = "<br/>"
                            title_79 = "<br/>"
                            title_80 = "√"

                        item_26 = an_check_history_item.query.filter(an_check_history_item.history_id == history_id,
                                                                     an_check_history_item.check_no == 24).first()
                        if item_26.check_answer == "YES":
                            title_81 = "√"
                            title_82 = "<br/>"
                            title_83 = "<br/>"
                        elif item_26.check_answer == "NO":
                            title_81 = "<br/>"
                            title_82 = "√"
                            title_83 = "<br/>"
                        else:
                            title_81 = "<br/>"
                            title_82 = "<br/>"
                            title_83 = "√"

                        item_27 = an_check_history_item.query.filter(an_check_history_item.history_id == history_id,
                                                                     an_check_history_item.check_no == 25).first()
                        if item_27.check_answer == "YES":
                            title_84 = "√"
                            title_85 = "<br/>"
                            title_86 = "<br/>"
                        elif item_27.check_answer == "NO":
                            title_84 = "<br/>"
                            title_85 = "√"
                            title_86 = "<br/>"
                        else:
                            title_84 = "<br/>"
                            title_85 = "<br/>"
                            title_86 = "√"

                        item_28 = an_check_history_item.query.filter(an_check_history_item.history_id == history_id,
                                                                     an_check_history_item.check_no == 26).first()
                        if item_28.check_answer == "YES":
                            title_87 = "√"
                            title_88 = "<br/>"
                            title_89 = "<br/>"
                        elif item_28.check_answer == "NO":
                            title_87 = "<br/>"
                            title_88 = "√"
                            title_89 = "<br/>"
                        else:
                            title_87 = "<br/>"
                            title_88 = "<br/>"
                            title_89 = "√"

                        item_29 = an_check_history_item.query.filter(an_check_history_item.history_id == history_id,
                                                                     an_check_history_item.check_no == 27).first()
                        if item_29.check_answer == "YES":
                            title_90 = "√"
                            title_91 = "<br/>"
                            title_92 = "<br/>"
                        elif item_29.check_answer == "NO":
                            title_90 = "<br/>"
                            title_91 = "√"
                            title_92 = "<br/>"
                        else:
                            title_90 = "<br/>"
                            title_91 = "<br/>"
                            title_92 = "√"

                        item_30 = an_check_history_item.query.filter(an_check_history_item.history_id == history_id,
                                                                     an_check_history_item.check_no == 28).first()
                        if item_30.check_answer == "YES":
                            title_93 = "√"
                            title_94 = "<br/>"
                            title_95 = "<br/>"
                        elif item_30.check_answer == "NO":
                            title_93 = "<br/>"
                            title_94 = "√"
                            title_95 = "<br/>"
                        else:
                            title_93 = "<br/>"
                            title_94 = "<br/>"
                            title_95 = "√"

                        item_31 = an_check_history_item.query.filter(an_check_history_item.history_id == history_id,
                                                                     an_check_history_item.check_no == 29).first()
                        if item_31.check_answer == "YES":
                            title_96 = "√"
                            title_97 = "<br/>"
                            title_98 = "<br/>"
                        elif item_31.check_answer == "NO":
                            title_96 = "<br/>"
                            title_97 = "√"
                            title_98 = "<br/>"
                        else:
                            title_96 = "<br/>"
                            title_97 = "<br/>"
                            title_98 = "√"

                        item_32 = an_check_history_item.query.filter(an_check_history_item.history_id == history_id,
                                                                     an_check_history_item.check_no == 30).first()
                        if item_32.check_answer == "YES":
                            title_99 = "√"
                            title_100 = "<br/>"
                            title_101 = "<br/>"
                        elif item_32.check_answer == "NO":
                            title_99 = "<br/>"
                            title_100 = "√"
                            title_101 = "<br/>"
                        else:
                            title_99 = "<br/>"
                            title_100 = "<br/>"
                            title_101 = "√"

                        item_33 = an_check_history_item.query.filter(an_check_history_item.history_id == history_id,
                                                                     an_check_history_item.check_no == 31).first()
                        if item_33.check_answer == "YES":
                            title_102 = "√"
                            title_103 = "<br/>"
                            title_104 = "<br/>"
                        elif item_33.check_answer == "NO":
                            title_102 = "<br/>"
                            title_103 = "√"
                            title_104 = "<br/>"
                        else:
                            title_102 = "<br/>"
                            title_103 = "<br/>"
                            title_104 = "√"

                        item_34 = an_check_history_item.query.filter(an_check_history_item.history_id == history_id,
                                                                     an_check_history_item.check_no == 32).first()
                        if item_34.check_answer == "YES":
                            title_105 = "√"
                            title_106 = "<br/>"
                            title_107 = "<br/>"
                        elif item_34.check_answer == "NO":
                            title_105 = "<br/>"
                            title_106 = "√"
                            title_107 = "<br/>"
                        else:
                            title_105 = "<br/>"
                            title_106 = "<br/>"
                            title_107 = "√"

                        item_35 = an_check_history_item.query.filter(an_check_history_item.history_id == history_id,
                                                                     an_check_history_item.check_no == 33).first()
                        if item_35.check_answer == "YES":
                            title_108 = "√"
                            title_109 = "<br/>"
                            title_110 = "<br/>"
                        elif item_35.check_answer == "NO":
                            title_108 = "<br/>"
                            title_109 = "√"
                            title_110 = "<br/>"
                        else:
                            title_108 = "<br/>"
                            title_109 = "<br/>"
                            title_110 = "√"

                        item_36 = an_check_history_item.query.filter(an_check_history_item.history_id == history_id,
                                                                     an_check_history_item.check_no == 34).first()
                        if item_36.check_answer == "YES":
                            title_111 = "√"
                            title_112 = "<br/>"
                            title_113 = "<br/>"
                        elif item_36.check_answer == "NO":
                            title_111 = "<br/>"
                            title_112 = "√"
                            title_113 = "<br/>"
                        else:
                            title_111 = "<br/>"
                            title_112 = "<br/>"
                            title_113 = "√"

                        item_37 = an_check_history_item.query.filter(an_check_history_item.history_id == history_id,
                                                                     an_check_history_item.check_no == 35).first()
                        if item_37.check_answer == "YES":
                            title_114 = "√"
                            title_115 = "<br/>"
                            title_116 = "<br/>"
                        elif item_37.check_answer == "NO":
                            title_114 = "<br/>"
                            title_115 = "√"
                            title_116 = "<br/>"
                        else:
                            title_114 = "<br/>"
                            title_115 = "<br/>"
                            title_116 = "√"

                        item_38 = an_check_history_item.query.filter(an_check_history_item.history_id == history_id,
                                                                     an_check_history_item.check_no == 36).first()
                        if item_38.check_answer == "YES":
                            title_117 = "√"
                            title_118 = "<br/>"
                            title_119 = "<br/>"
                        elif item_38.check_answer == "NO":
                            title_117 = "<br/>"
                            title_118 = "√"
                            title_119 = "<br/>"
                        else:
                            title_117 = "<br/>"
                            title_118 = "<br/>"
                            title_119 = "√"

                        item_39 = an_check_history_item.query.filter(an_check_history_item.history_id == history_id,
                                                                     an_check_history_item.check_no == 37).first()
                        if item_39.check_answer == "YES":
                            title_120 = "√"
                            title_121 = "<br/>"
                            title_122 = "<br/>"
                        elif item_39.check_answer == "NO":
                            title_120 = "<br/>"
                            title_121 = "√"
                            title_122 = "<br/>"
                        else:
                            title_120 = "<br/>"
                            title_121 = "<br/>"
                            title_122 = "√"

                        item_40 = an_check_history_item.query.filter(an_check_history_item.history_id == history_id,
                                                                     an_check_history_item.check_no == 38.1).first()
                        if item_40.check_answer == "YES":
                            title_123 = "√"
                            title_124 = "<br/>"
                            title_125 = "<br/>"
                        elif item_40.check_answer == "NO":
                            title_123 = "<br/>"
                            title_124 = "√"
                            title_125 = "<br/>"
                        else:
                            title_123 = "<br/>"
                            title_124 = "<br/>"
                            title_125 = "√"

                        item_41 = an_check_history_item.query.filter(an_check_history_item.history_id == history_id,
                                                                     an_check_history_item.check_no == 38.2).first()
                        if item_41.check_answer == "YES":
                            title_126 = "√"
                            title_127 = "<br/>"
                            title_128 = "<br/>"
                        elif item_41.check_answer == "NO":
                            title_126 = "<br/>"
                            title_127 = "√"
                            title_128 = "<br/>"
                        else:
                            title_126 = "<br/>"
                            title_127 = "<br/>"
                            title_128 = "√"

                        item_42 = an_check_history_item.query.filter(an_check_history_item.history_id == history_id,
                                                                     an_check_history_item.check_no == 38.3).first()
                        if item_42.check_answer == "YES":
                            title_129 = "√"
                            title_130 = "<br/>"
                            title_131 = "<br/>"
                        elif item_42.check_answer == "NO":
                            title_129 = "<br/>"
                            title_130 = "√"
                            title_131 = "<br/>"
                        else:
                            title_129 = "<br/>"
                            title_130 = "<br/>"
                            title_131 = "√"

                        item_43 = an_check_history_item.query.filter(an_check_history_item.history_id == history_id,
                                                                     an_check_history_item.check_no == 39).first()
                        if item_43.check_answer == "YES":
                            title_132 = "√"
                            title_133 = "<br/>"
                            title_134 = "<br/>"
                        elif item_43.check_answer == "NO":
                            title_132 = "<br/>"
                            title_133 = "√"
                            title_134 = "<br/>"
                        else:
                            title_132 = "<br/>"
                            title_133 = "<br/>"
                            title_134 = "√"

                        item_44 = an_check_history_item.query.filter(an_check_history_item.history_id == history_id,
                                                                     an_check_history_item.check_no == 40).first()
                        if item_44.check_answer == "YES":
                            title_135 = "√"
                            title_136 = "<br/>"
                            title_137 = "<br/>"
                        elif item_44.check_answer == "NO":
                            title_135 = "<br/>"
                            title_136 = "√"
                            title_137 = "<br/>"
                        else:
                            title_135 = "<br/>"
                            title_136 = "<br/>"
                            title_137 = "√"

                        item_45 = an_check_history_item.query.filter(an_check_history_item.history_id == history_id,
                                                                     an_check_history_item.check_no == 41).first()
                        if item_45.check_answer == "YES":
                            title_138 = "√"
                            title_139 = "<br/>"
                            title_140 = "<br/>"
                        elif item_45.check_answer == "NO":
                            title_138 = "<br/>"
                            title_139 = "√"
                            title_140 = "<br/>"
                        else:
                            title_138 = "<br/>"
                            title_139 = "<br/>"
                            title_140 = "√"

                        item_46 = an_check_history_item.query.filter(an_check_history_item.history_id == history_id,
                                                                     an_check_history_item.check_no == 42).first()
                        if item_46.check_answer == "YES":
                            title_141 = "√"
                            title_142 = "<br/>"
                            title_143 = "<br/>"
                        elif item_46.check_answer == "NO":
                            title_141 = "<br/>"
                            title_142 = "√"
                            title_143 = "<br/>"
                        else:
                            title_141 = "<br/>"
                            title_142 = "<br/>"
                            title_143 = "√"

                        item_47 = an_check_history_item.query.filter(an_check_history_item.history_id == history_id,
                                                                     an_check_history_item.check_no == 43).first()
                        if item_47.check_answer == "YES":
                            title_144 = "√"
                            title_145 = "<br/>"
                            title_146 = "<br/>"
                        elif item_47.check_answer == "NO":
                            title_144 = "<br/>"
                            title_145 = "√"
                            title_146 = "<br/>"
                        else:
                            title_144 = "<br/>"
                            title_145 = "<br/>"
                            title_146 = "√"

                        item_48 = an_check_history_item.query.filter(an_check_history_item.history_id == history_id,
                                                                     an_check_history_item.check_no == 44).first()
                        if item_48.check_answer == "YES":
                            title_147 = "√"
                            title_148 = "<br/>"
                            title_149 = "<br/>"
                        elif item_48.check_answer == "NO":
                            title_147 = "<br/>"
                            title_148 = "√"
                            title_149 = "<br/>"
                        else:
                            title_147 = "<br/>"
                            title_148 = "<br/>"
                            title_149 = "√"

                        item_49 = an_check_history_item.query.filter(an_check_history_item.history_id == history_id,
                                                                     an_check_history_item.check_no == 45).first()
                        if item_49.check_answer == "YES":
                            title_150 = "√"
                            title_151 = "<br/>"
                            title_152 = "<br/>"
                        elif item_49.check_answer == "NO":
                            title_150 = "<br/>"
                            title_151 = "√"
                            title_152 = "<br/>"
                        else:
                            title_150 = "<br/>"
                            title_151 = "<br/>"
                            title_152 = "√"

                        item_50 = an_check_history_item.query.filter(an_check_history_item.history_id == history_id,
                                                                     an_check_history_item.check_no == 46).first()
                        if item_50.check_answer == "YES":
                            title_153 = "√"
                            title_154 = "<br/>"
                            title_155 = "<br/>"
                        elif item_50.check_answer == "NO":
                            title_153 = "<br/>"
                            title_154 = "√"
                            title_155 = "<br/>"
                        else:
                            title_153 = "<br/>"
                            title_154 = "<br/>"
                            title_155 = "√"

                        item_51 = an_check_history_item.query.filter(an_check_history_item.history_id == history_id,
                                                                     an_check_history_item.check_no == 47).first()
                        if item_51.check_answer == "YES":
                            title_156 = "√"
                            title_157 = "<br/>"
                            title_158 = "<br/>"
                        elif item_51.check_answer == "NO":
                            title_156 = "<br/>"
                            title_157 = "√"
                            title_158 = "<br/>"
                        else:
                            title_156 = "<br/>"
                            title_157 = "<br/>"
                            title_158 = "√"

                        item_52 = an_check_history_item.query.filter(an_check_history_item.history_id == history_id,
                                                                     an_check_history_item.check_no == 48).first()
                        if item_52.check_answer == "YES":
                            title_159 = "√"
                            title_160 = "<br/>"
                            title_161 = "<br/>"
                        elif item_52.check_answer == "NO":
                            title_159 = "<br/>"
                            title_160 = "√"
                            title_161 = "<br/>"
                        else:
                            title_159 = "<br/>"
                            title_160 = "<br/>"
                            title_161 = "√"

                        item_53 = an_check_history_item.query.filter(an_check_history_item.history_id == history_id,
                                                                     an_check_history_item.check_no == 49).first()
                        if item_53.check_answer == "YES":
                            title_162 = "√"
                            title_163 = "<br/>"
                            title_164 = "<br/>"
                        elif item_53.check_answer == "NO":
                            title_162 = "<br/>"
                            title_163 = "√"
                            title_164 = "<br/>"
                        else:
                            title_162 = "<br/>"
                            title_163 = "<br/>"
                            title_164 = "√"

                        title_192 = check_history.user_name
                        title_193 = main_port.port_of_departure or "PEK"
                        title_194 = check_history.user_name
                        title_195 = str(check_history.createtime.year) + "/" + str(check_history.createtime.month) + "/" \
                                    + str(check_history.createtime.day)
                        title_196 = str(check_history.createtime.hour) + ":" + str(
                            check_history.createtime.minute) + ":" \
                                    + str(check_history.createtime.second)
                        html_body.format(
                            title_0, title_1, title_2, title_3, title_4, title_5, title_6, title_7, title_8, title_9,
                            title_10, title_11, title_12, title_13, title_14, title_15, title_16, title_17, title_18,
                            title_19, title_20, title_21, title_22, title_23, title_24, title_25, title_26, title_27,
                            title_28, title_29, title_30, title_31, title_32, title_33, title_34, title_35, title_36,
                            title_37, title_38, title_39, title_40, title_41, title_42, title_43, title_44, title_45,
                            title_46, title_47, title_48, title_49, title_50, title_51, title_52, title_53, title_54,
                            title_55, title_56, title_57, title_58, title_59, title_60, title_61, title_62, title_63,
                            title_64, title_65, title_66, title_67, title_68, title_69, title_70, title_71, title_72,
                            title_73, title_74, title_75, title_76, title_77, title_78, title_79, title_80, title_81,
                            title_82, title_83, title_84, title_85, title_86, title_87, title_88, title_89, title_90,
                            title_91, title_92, title_93, title_94, title_95, title_96, title_97, title_98, title_99,
                            title_100, title_101, title_102, title_103, title_104, title_105, title_106, title_107,
                            title_108, title_109, title_110, title_111, title_112, title_113, title_114, title_115,
                            title_116, title_117, title_118, title_119, title_120, title_121, title_122, title_123,
                            title_124, title_125, title_126, title_127, title_128, title_129, title_130, title_131,
                            title_132, title_133, title_134, title_135, title_136, title_137, title_138, title_139,
                            title_140, title_141, title_142, title_143, title_144, title_145, title_146, title_147,
                            title_148, title_149, title_150, title_151, title_152, title_153, title_154, title_155,
                            title_156, title_157, title_158, title_159, title_160, title_161, title_162, title_163,
                            title_164, title_192, title_193, title_194, title_195, title_196
                        )
                    else:
                        html_body = """
                                    <!DOCTYPE html>
                                    <html>
                                       <head>
                                          <meta charset="UTF-8">
                                          <title>Shipper Demo</title>
                                       </head>
                                    </html>
                                    """
                    from FanstiBgs.config.secret import WK_HTML_TO_IMAGE, WindowsRoot
                    # path_wkhtmltopdf_image = WK_HTML_TO_IMAGE
                    import imgkit, platform, os
                    # config_img = imgkit.config(wkhtmltoimage=path_wkhtmltopdf_image)
                    from FanstiBgs.config.secret import LinuxRoot, LinuxImgs, WindowsImgs, WindowsRoot
                    if platform.system() == "Windows":
                        rootdir = WindowsRoot
                        pic_name = "{0}.png".format(str(uuid.uuid1()))
                        outdir = rootdir + "\\check_item\\{0}".format(pic_name)
                        if not os.path.exists(outdir):
                            os.makedirs(outdir)
                    else:
                        rootdir = LinuxRoot + LinuxImgs
                        pic_name = "{0}-{1}.png".format(args.get("check_type"), str(uuid.uuid1()))
                        outdir = rootdir + "/check_item/{0}".format(pic_name)
                        if not os.path.exists(outdir):
                            os.makedirs(outdir)
                    current_app.logger.info(str(html_body))
                    current_app.logger.info(">>>>>>>>>>>>>>>>outdir:" + str(outdir))
                    if platform.system() == "Windows":
                        rootdir = WindowsRoot
                        pic_name = "{0}.html".format(uuid.uuid1())
                        outdir = rootdir + "\\check_item\\{0}".format(pic_name)
                        if not os.path.exists(outdir):
                            os.makedirs(outdir)
                    else:
                        rootdir = LinuxRoot + LinuxImgs
                        pic_name = "{0}-{1}.html".format(args.get("check_type"), str(uuid.uuid1()))
                        outdir = rootdir + "/check_item/{0}".format(pic_name)
                        if not os.path.exists(outdir):
                            os.makedirs(outdir)
                    inset_html = open("{0}".format(outdir), "w")
                    inset_html.write("print()")
                    inset_html.close()

                    # imgkit.from_string(str(html_body), output_path=outdir, config=config_img)

                    local_url = "file://E:/fstfile/check_item/{0}".format(pic_name)
                    from selenium import webdriver
                    pic_name = "{0}.png".format(str(uuid.uuid1()))
                    save_fn = rootdir + "\\check_item\\{0}".format(pic_name)

                    option = webdriver.ChromeOptions()
                    option.add_argument('--headless')
                    option.add_argument('--disable-gpu')
                    option.add_argument("--window-size=1280,1024")
                    option.add_argument("--hide-scrollbars")

                    # TODO 对应环境替换路径
                    driver = webdriver.Chrome(chrome_options=option, executable_path="F:/chromedriver")

                    driver.get(local_url)

                    scroll_width = driver.execute_script('return document.body.parentNode.scrollWidth')
                    scroll_height = driver.execute_script('return document.body.parentNode.scrollHeight')
                    driver.set_window_size(scroll_width, scroll_height)
                    driver.save_screenshot(save_fn)
                    driver.quit()

                    picture_dict = {
                        "id": str(uuid.uuid1()),
                        "procedure_id": args.get("master_id"),
                        "file_name": pic_name,
                        "file_src": save_fn,
                        "user_id": user_id,
                        "user_name": user_name,
                        "createtime": datetime.datetime.now(),
                        "type": "check_item"
                    }
                    picture_instance = an_procedure_picture.create(picture_dict)
                    db.session.add(picture_instance)

            return Success(message="提交成功")


    def get_checklist_message(self):
        """
        获取检查单题目详情
        """
        args = parameter_required(("token", "master_id", "check_item_id"))

        check_item = an_checklist.query.filter(an_checklist.id == args.get("check_item_id")).first_("未找到该题目")
        check_type = check_item.check_type
        check_no = check_item.check_no
        if str(check_no).split(".")[-1] == "0":
            check_no = str(int(check_no))
        else:
            check_no = str(check_no)

        check_message_dict = self.get_checklist_abo(check_no, check_type, args.get("master_id"))

        return Success(data={"message": check_message_dict["message"]})

    def get_checklist_abo(self, check_no, check_type, master_number):
        """
        基于各种信息获取检查单详情
        """
        if check_type in ["Nonradiative", "Radioactive"]:
            if check_no == "1":
                return {
                    "result": "YES",
                    "message": None
                }
            elif check_no == "2":
                receiver_dict = t_bgs_shipper_consignee_info.query.filter(
                    t_bgs_shipper_consignee_info.master_number == master_number,
                    t_bgs_shipper_consignee_info.info_state == "2") \
                    .first()
                sender_dict = t_bgs_shipper_consignee_info.query.filter(
                    t_bgs_shipper_consignee_info.master_number == master_number,
                    t_bgs_shipper_consignee_info.info_state == "1") \
                    .first()

                result_check_list = []
                receiver = "Consignee："
                if receiver_dict.country:
                    receiver += "<br/>Country：{0}".format(receiver_dict.country)
                    result_check_list.append("YES")
                else:
                    result_check_list.append("NO")
                if receiver_dict.city:
                    receiver += "<br/>City：{0}".format(receiver_dict.city)
                    result_check_list.append("YES")
                else:
                    result_check_list.append("NO")
                if receiver_dict.company_name:
                    receiver += "<br/>Company Name：{0}".format(receiver_dict.company_name)
                if receiver_dict.company_address:
                    receiver += "<br/>Company Address：{0}".format(receiver_dict.company_address)
                    result_check_list.append("YES")
                else:
                    result_check_list.append("NO")
                if receiver_dict.name:
                    receiver += "<br/>Name：{0}".format(receiver_dict.name)
                    result_check_list.append("YES")
                else:
                    result_check_list.append("NO")
                if receiver_dict.mailbox:
                    receiver += "<br/>Email：{0}".format(receiver_dict.mailbox)
                if receiver_dict.fax:
                    receiver += "<br/>Fax：{0}".format(receiver_dict.fax)
                if receiver_dict.phone:
                    receiver += "<br/>Tel：{0}".format(receiver_dict.phone)
                    result_check_list.append("YES")
                else:
                    result_check_list.append("NO")
                sender = "<br/>Shipper："
                if sender_dict.country:
                    sender += "<br/>Country：{0}".format(sender_dict.country)
                    result_check_list.append("YES")
                else:
                    result_check_list.append("NO")
                if sender_dict.city:
                    sender += "<br/>City：{0}".format(sender_dict.city)
                    result_check_list.append("YES")
                else:
                    result_check_list.append("NO")
                if sender_dict.company_name:
                    sender += "<br/>Company Name：{0}".format(sender_dict.company_name)
                if sender_dict.company_address:
                    sender += "<br/>Company Address：{0}".format(sender_dict.company_address)
                    result_check_list.append("YES")
                else:
                    result_check_list.append("NO")
                if sender_dict.name:
                    sender += "<br/>Name：{0}".format(sender_dict.name)
                    result_check_list.append("YES")
                else:
                    result_check_list.append("NO")
                if sender_dict.mailbox:
                    sender += "<br/>Email：{0}".format(sender_dict.mailbox)
                if sender_dict.fax:
                    sender += "<br/>Fax：{0}".format(sender_dict.fax)
                if sender_dict.phone:
                    sender += "<br/>Tel：{0}".format(sender_dict.phone)
                    result_check_list.append("YES")
                else:
                    result_check_list.append("NO")

                receiver = receiver + sender

                if "NO" in result_check_list:
                    result = "NO"
                else:
                    result = "YES"

                return {
                    "result": result,
                    "message": receiver
                }
            elif check_no == "3":
                if master_number:
                    result = "YES"
                else:
                    master_number = ""
                    result = "NO"
                return {
                    "result": result,
                    "message": "Air Waybill No：" + str(master_number)
                }
            elif check_no == "4":
                # 2020/11/10 确认需求
                return {
                    "result": "YES",
                    "message": None
                }
            elif check_no in ["5", "26", "44", "53"]:
                # 展示货运类型
                message = self.get_declaration_abo(4, master_number)
                if check_no in ["26", "44", "53"]:
                    if message.replace("This shipment is within the limitations prescribed for：", "") \
                            == "CARGO AIRCRAFT ONLY":
                        result = "YES"
                    elif message.replace("This shipment is within the limitations prescribed for：", "") \
                            == "PASSENGER AND CARGO AIRCRAFT":
                        result = "N/A"
                    else:
                        result = None
                else:
                    result = None
                return {
                    "result": result,
                    "message": message
                }
            elif check_no == "6":
                # 展示起运港目的港
                message = self.get_declaration_abo(3, master_number)
                if message.split("<br/>")[0].replace("Airport of Departure：", ""):
                    result = "YES"
                else:
                    result = "NO"
                return {
                    "result": result,
                    "message": message
                }
            elif check_no == "7":
                # 展示货运方式
                message = self.get_declaration_abo(2, master_number)
                if message.replace("Shipment type：", ""):
                    result = "YES"
                else:
                    result = "NO"
                return {
                    "result": result,
                    "message": message
                }
            elif check_no == "8":
                # 展示UN编号
                un_list = self.get_declaration_abo(5, master_number)
                un_head = "UN or ID No.："
                un_message = ""
                for un in un_list:
                    if un_message:
                        un_message += "<br/>"
                    un_message += un
                un_head += un_message
                return {
                    "result": "YES",
                    "message": un_head
                }
            elif check_no == "9":
                # 展示UN编号与品名
                un_list = self.get_declaration_abo(6, master_number)
                un_message = ""
                for un_dict in un_list:
                    if un_message:
                        un_message += "<br/>"
                    un_message += "UN or ID No.：" + str(un_dict[0]) \
                                  + "<br/>" + "Proper Shipping Name：" + str(un_dict[1] or "")
                return {
                    "result": "YES",
                    "message": un_message
                }
            elif check_no in ["10", "11"]:
                # 展示UN编号与主次要危险品
                un_list = self.get_declaration_abo(7, master_number)
                un_message = ""
                for un_dict in un_list:
                    if un_message:
                        un_message += "<br/>"
                    un_message += "UN or ID No.：" + str(un_dict[0]) \
                                  + "<br/>" + "Class or Division(Subsidiary risk)：" + str(un_dict[1] or "")
                if check_no == "10":
                    result = "YES"
                else:
                    result = "N/A"
                    for un_dict in un_list:
                        if "(" in un_dict[1] and ")" in un_dict[1]:
                            result = "YES"
                return {
                    "result": result,
                    "message": un_message
                }
            elif check_no == "12":
                # 展示UN编号与包装等级
                un_list = self.get_declaration_abo(8, master_number)
                un_message = ""
                result = "N/A"
                for un_dict in un_list:
                    if un_message:
                        un_message += "<br/>"
                    if un_dict[1]:
                        result = "YES"
                    un_message += "UN or ID No.：" + str(un_dict[0]) \
                                  + "<br/>" + "Packing Group：" + str(un_dict[1] or "")
                return {
                    "result": result,
                    "message": un_message
                }
            elif check_no in ["13", "14"]:
                # 展示UN编号与商品名称
                un_list = self.get_declaration_abo(9, master_number)
                un_message = ""
                for un_dict in un_list:
                    if un_message:
                        un_message += "<br/>"
                    un_message += "UN or ID No.：" + str(un_dict[0]) \
                                  + "<br/>" + "Quantity and type of packing：" + str(un_dict[1] or "")
                return {
                    "result": None,
                    "message": un_message
                }
            elif check_no == "15":
                # 1类危险品展示 主次要危险品和商品名称，其他不展示
                un_list = t_bgs_un.query.filter(t_bgs_un.MAIN_DANGEROUS_ID == "1", master_number == master_number).all()
                if un_list:
                    un_message = ""
                    for un in un_list:
                        un_number = un.UN_NUMBER
                        first_risk = un.MAIN_DANGEROUS_ID
                        second_risk = un.SECOND_DANGEROUS_IDA
                        if second_risk:
                            first_risk = first_risk + "(" + second_risk + ")"
                        pack_number = un.packNumber
                        material = un.material
                        weight = un.weight
                        unit = un.unit
                        if not material or len(material) < 2:
                            product_name = ""
                        else:
                            product_name = str(pack_number) + " " + material[1] + " " + "x" + str(weight) + str(unit)
                        un_message += "UN or ID No.：" + un_number + "<br/>" + "Class or Division(Subsidiary risk)：" \
                                      + first_risk + "<br/>" + "Quantity and type of packing：" + product_name
                    result = "YES"
                else:
                    un_message = None
                    result = "N/A"
                return {
                    "result": result,
                    "message": un_message
                }
            elif check_no in ["16.1", "16.2", "16.3", "16.4", "17.1", "17.2", "17.3", "35", "36", "37", "38", "39",
                              "40", "41", "42", "43", "45", "46", "47", "49", "50", "51"]:
                un_list = t_bgs_un.query.filter(master_number == master_number).all()
                if un_list:
                    un_message = ""
                    for un in un_list:
                        un_number = un.UN_NUMBER
                        first_risk = un.MAIN_DANGEROUS_ID
                        second_risk = un.SECOND_DANGEROUS_IDA
                        if second_risk:
                            first_risk = first_risk + "(" + second_risk + ")"
                        pack_number = un.packNumber
                        material = un.material
                        weight = un.weight
                        unit = un.unit
                        if not material or len(material) < 2:
                            product_name = ""
                        else:
                            product_name = str(pack_number) + " " + material[1] + " " + "x" + str(weight) + str(unit)
                        un_message += "UN or ID No.：" + un_number + "<br/>" \
                                      + "Proper Shipping Name" + str(un.product_Name or "") + "<br/>" \
                                      + "Class or Division(Subsidiary risk)：" + first_risk + "<br/>" \
                                      + "Packing Group" + str(un.packaging_grade or "") + "<br/>" \
                                      + "Quantity and type of packing：" + product_name
                else:
                    un_message = None
                return {
                    "result": None,
                    "message": un_message
                }
            elif check_no == "18":
                # 展示UN编号与包装指导
                un_list = self.get_declaration_abo(10, master_number)
                un_message = ""
                for un_dict in un_list:
                    if un_message:
                        un_message += "<br/>"
                    un_message += "UN or ID No.：" + str(un_dict[0]) \
                                  + "<br/>" + "Packing Inst.：" + str(un_dict[1] or "")
                return {
                    "result": "YES",
                    "message": un_message
                }
            elif check_no == "19":
                # 展示UN编号/包装指导/包装说明
                un_list = t_bgs_un.query.filter(master_number == master_number).all()
                if un_list:
                    un_message = ""
                    for un in un_list:
                        un_number = un.UN_NUMBER

                        un_message += "UN or ID No.：" + un_number + "<br/>" \
                                      + "Packing Inst.：" + str(un.packaging_instruction or "") + "<br/>" \
                                      + "Authorization：" + str(un.introduce or "") + "<br/>"
                else:
                    un_message = None
                return {
                    "result": None,
                    "message": un_message
                }
            elif check_no == "20":
                # 展示UN编号与包装说明
                un_list = self.get_declaration_abo(10, master_number)
                un_message = ""
                for un_dict in un_list:
                    if un_message:
                        un_message += "<br/>"
                    un_message += "UN or ID No.：" + str(un_dict[0]) \
                                  + "<br/>" + "Authorization：" + str(un_dict[1] or "")
                return {
                    "result": None,
                    "message": un_message
                }
            elif check_no in ["21", "24", "25", "27", "28", "29", "30", "31.1", "31.2", "31.3", "31.4", "31.5", "32",
                              "33", "34", "48"]:
                # 无需展示任何内容
                if check_no == "24":
                    result = "N/A"
                else:
                    result = None
                return {
                    "result": result,
                    "message": None
                }
            elif check_no == "22":
                un_list = t_bgs_un.query.filter(master_number == master_number).all()
                if un_list:
                    un_message = ""
                    for un in un_list:
                        un_number = un.UN_NUMBER
                        first_risk = un.MAIN_DANGEROUS_ID
                        second_risk = un.SECOND_DANGEROUS_IDA
                        if second_risk:
                            first_risk = first_risk + "(" + second_risk + ")"
                        pack_number = un.packNumber
                        material = un.material
                        weight = un.weight
                        unit = un.unit
                        if not material or len(material) < 2:
                            product_name = ""
                        else:
                            product_name = str(pack_number) + " " + material[1] + " " + "x" + str(weight) + str(unit)
                        un_message += "UN or ID No.：" + un_number + "<br/>" \
                                      + "Proper Shipping Name" + str(un.product_Name or "") + "<br/>" \
                                      + "Class or Division(Subsidiary risk)：" + first_risk + "<br/>" \
                                      + "Packing Group" + str(un.packaging_grade or "") + "<br/>" \
                                      + "Quantity and type of packing：" + product_name + "<br/>" \
                                      + "Packing Inst.：" + str(un.packaging_instruction or "")
                else:
                    un_message = None
                return {
                    "result": None,
                    "message": un_message
                }
            elif check_no == "23":
                # 展示签字信息
                message = self.get_declaration_abo(12, master_number)
                return {
                    "result": "YES",
                    "message": message
                }
            elif check_no == "52":
                # 展示起运港/目的地/紧急联系信息
                message_dep = self.get_declaration_abo(3, master_number)
                message_tra = self.get_declaration_abo(13, master_number)
                return {
                    "result": None,
                    "message": message_dep + "<br/>" + message_tra
                }
            else:
                return {
                    "result": None,
                    "message": None
                }
        else:
            return {
                "result": None,
                "message": None
            }

    def get_declaration_abo(self, location, master_number):
        """
        获取申报单信息
        """
        main_port = t_bgs_main_single_number.query.filter(
            t_bgs_main_single_number.id == master_number).first()
        un_list = t_bgs_un.query.filter(t_bgs_un.master_number == master_number).all()
        if location == 1:
            # 无需处理 2020/11/10确认
            message = None
        elif location == 2:
            # 货运类型
            freight_type = main_port.freight_type or ""
            message = "Shipment type：" + str(freight_type)
        elif location == 3:
            # 起运港/目的港
            port_of_departure = main_port.port_of_departure or ""
            destination_port = main_port.destination_port or ""
            message = "Airport of Departure：" + str(port_of_departure) \
                      + "<br/>" + "Airport of Destination：" + str(destination_port)
        elif location == 4:
            # 运输方式
            type_of_shipping = main_port.type_of_shipping or ""
            message = "This shipment is within the limitations prescribed for：" + str(type_of_shipping)
        elif location == 5:
            # UN号
            un_no = []
            for un in un_list:
                un_no.append("UN" + str(un.UN_NUMBER))
            message = un_no
        elif location == 6:
            # 品名
            product_name = []
            for un in un_list:
                un_dict = []
                un_dict.append("UN" + str(un.UN_NUMBER))
                un_dict.append(un.product_Name)
                product_name.append(un_dict)
            message = product_name
        elif location == 7:
            # 主要危险品（次要危险品）
            risk_name = []
            for un in un_list:
                un_dict = []
                un_dict.append("UN" + str(un.UN_NUMBER))
                first_risk = un.MAIN_DANGEROUS_ID
                second_risk = un.SECOND_DANGEROUS_IDA
                if second_risk:
                    first_risk = first_risk + "(" + second_risk + ")"
                un_dict.append(first_risk)
                risk_name.append(un_dict)
            message = risk_name
        elif location == 8:
            # 包装等级
            packing_grade = []
            for un in un_list:
                un_dict = []
                un_dict.append("UN" + str(un.UN_NUMBER))
                un_dict.append(un.packaging_grade)
                packing_grade.append(un_dict)
            message = packing_grade
        elif location == 9:
            # [件数] [包装类型1] [x] [数量][单位]
            type_packing = []
            for un in un_list:
                un_dict = []
                un_dict.append("UN" + str(un.UN_NUMBER))
                pack_number = un.packNumber
                material = un.material
                weight = un.weight
                unit = un.unit
                if not material or len(material) < 2:
                    un_dict.append(None)
                else:
                    un_dict.append(str(pack_number) + " " + material[1] + " " + "x" + str(weight) + str(unit))
                type_packing.append(un_dict)
            message = type_packing
        elif location == 10:
            # 包装指导
            packaging_instruction = []
            for un in un_list:
                un_dict = []
                un_dict.append("UN" + str(un.UN_NUMBER))
                un_dict.append(un.packaging_instruction)
                packaging_instruction.append(un_dict)
            message = packaging_instruction
        elif location == 11:
            # 包装说明
            introduce = []
            for un in un_list:
                un_dict = []
                un_dict.append("UN" + str(un.UN_NUMBER))
                un_dict.append(un.introduce)
                introduce.append(un_dict)
            message = introduce
        elif location == 12:
            # 姓名/职务/地址/日期
            statement_name = main_port.statement_name or ""
            statement_title = main_port.statement_title or ""
            statement_address = main_port.statement_address or ""
            place_and_data = main_port.place_and_data or ""

            message = "Name of Signatory：" + statement_name + "<br/>" + "Title of Signatory：" + statement_title \
                      + "<br/>" + "Place：" + statement_address + "<br/>" + "Date：" + place_and_data
        elif location == 13:
            ATTN = main_port.ATTN or ""
            emergency_contact = main_port.emergency_contact or ""
            note = main_port.note or ""

            message = "ATTN：" + ATTN + "<br/>" + "TEL：" + emergency_contact + "<br/>" + "Note：" + note
        else:
            message = None

        return message

