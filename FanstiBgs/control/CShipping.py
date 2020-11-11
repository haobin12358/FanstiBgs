"""
本文件用于处理收运管理
create user: haobin12358
last update time: 2020-09-09
"""

import hashlib, datetime, requests, uuid, json
from flask import request, current_app

from FanstiBgs.extensions.params_validates import parameter_required
from FanstiBgs.extensions.request_handler import token_to_user_
from FanstiBgs.extensions.register_ext import db
from FanstiBgs.extensions.success_response import Success
from FanstiBgs.models.bgs_android import an_procedure, an_procedure_picture, an_checklist, an_check_history, \
    an_check_history_item
from FanstiBgs.models.bgs_cloud import t_bgs_main_single_number, t_bgs_un, t_bgs_shipper_consignee_info, t_bgs_file

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

        count = 0
        first_check = an_check_history.query.filter(an_check_history.master_id == args.get("master_id"),
                                                    an_check_history.times == "first").first()
        if first_check:
            count += 1

        second_check = an_check_history.query.filter(an_check_history.master_id == args.get("master_id"),
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
                "type": "radioactivity",
                "is_next": 1,
                "next": ["radioactive", "nonradiative"]
            },
            {
                "type": "dry ice",
                "is_next": 0
            },
            {
                "type": "lithium cell",
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
                    "status_code": 405007,
                    "message": "请选择和第一次提交相同的检查单类型"
                }
        else:
            first_check_id = None

        second_check = an_check_history.query.filter(an_check_history.master_id == args.get("master_id"),
                                                    an_check_history.times == "second").first()
        if first_check and second_check:
            second_check_id = second_check.id
            check_items = an_checklist.query.filter(an_checklist.check_type == args.get("check_type"))\
                .order_by(an_checklist.check_no.asc()).all()
            items = []
            for item in check_items:
                check_id = item.id
                first_item = an_check_history_item.query.filter(an_check_history_item.check_id == check_id,
                                                                an_check_history_item.history_id == first_check_id)\
                    .first()
                second_item = an_check_history_item.query.filter(an_check_history_item.check_id == check_id,
                                                                an_check_history_item.history_id == second_check_id) \
                    .first()
                if first_item.check_answer != second_item.check_answer:
                    items.append(item)
        else:
            second_check_id = None


        for item in items:
            item.fill("check_topic", "【{0}】{1}".format(item.check_genre, item.check_item))
            check_type = item.check_type
            check_no = item.check_no
            if str(check_no).split(".")[-1] == "0":
                check_no = str(int(check_no))
            else:
                check_no = str(check_no)

            check_message_dict = self.get_checklist_abo(check_no, check_type, args.get("master_id"))
            if check_message_dict["result"]:
                item.fill("answer", check_message_dict["result"])
            else:
                item.fill("answer", None)
            if check_message_dict["message"]:
                item.fill("show_message", "301")
            else:
                item.fill("show_message", "302")

            if first_check_id:
                first_check_item = an_check_history_item.query.filter(
                    an_check_history_item.history_id == first_check_id,
                    an_check_history_item.check_id == item.id)\
                    .first()
                item.fill("first_answer", first_check_item.check_answer)
            else:
                item.fill("first_answer", None)
            if second_check_id:
                second_check_item = an_check_history_item.query.filter(
                    an_check_history_item.history_id == first_check_id,
                    an_check_history_item.check_id == item.id)\
                    .first()
                item.fill("second_answer", second_check_item.check_answer)
            else:
                item.fill("second_answer", None)

        return Success(data=items)

    def make_checklist_history(self):
        """
        提交检查单结果
        """
        args = parameter_required(("token", "master_id", "check_type"))
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
            with db.auto_commit():
                for item in data:
                    if not item.get("answer"):
                        return {
                            "status": 405,
                            "status_code": 405010,
                            "message": "第{0}项未选择".format(item.get("check_no"))
                        }
                    history_item_dict = {
                        "id": str(uuid.uuid1()),
                        "check_id": item.get("id"),
                        "history_id": history_id,
                        "check_no": item.get("check_no"),
                        "check_item": item.get("check_item"),
                        "check_genre": item.get("check_genre"),
                        "check_answer": item.get("answer")
                    }
                    history_item_instance = an_check_history_item.create(history_item_dict)
                    db.session.add(history_item_instance)
                history_instance = an_check_history.create(history_dict)
                db.session.add(history_instance)
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
        if check_type in ["nonradiative", "radioactive"]:
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

