"""
本文件用于处理进出港出入库及盘库
create user: haobin12358
last update time: 2020-09-09
"""

import datetime, uuid, json
from flask import request

from FanstiBgs.extensions.params_validates import parameter_required
from FanstiBgs.extensions.interface.user_interface import token_required
from FanstiBgs.extensions.error_response import ParamsError, NoPreservationError
from FanstiBgs.extensions.register_ext import db
from FanstiBgs.extensions.success_response import Success
from FanstiBgs.models.bgs_android import an_user, an_area, an_storing_location, an_preservation_type, \
    an_procedure, an_procedure_picture
from FanstiBgs.models.bgs_cloud import t_bgs_main_single_number

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

    @token_required
    def get(self):
        """
        获取详情
        1.基于id（获取详情）
        2.基于master_number（创建一条数据后，返回详情）
        """
        args = parameter_required(("procedure_type", ))
        if args.get("procedure_type") not in ["in", "out"]:
            return ParamsError("参数类型错误")
        if args.get("id"):
            procedure = an_procedure.query.filter(an_procedure.procedure_type == args.get("procedure_type"),
                                                  an_procedure.id == args.get("id"))\
                .first_("未找到该单据")
            if procedure.freight_type == "PASSENGER AND CARGO AIRCRAFT":
                procedure.fill("freight_type_ch", "客货均可")
            elif procedure.freight_type == "CARGO AIRCRAFT ONLY":
                procedure.fill("freight_type_ch", "仅限货机")
            else:
                procedure.fill("freight_type_ch", None)
            if procedure.type_of_shipping == "NON-RADIOACTIVE":
                procedure.fill("type_of_shipping_ch", "非放射性")
            elif procedure.type_of_shipping == "RADIOACTIVE":
                procedure.fill("type_of_shipping_ch", "放射性")
            else:
                procedure.fill("type_of_shipping_ch", None)
            history_list = self._get_history_list(procedure)
            procedure_picture_list = an_procedure_picture.query.filter(
                an_procedure_picture.procedure_id == args.get("id")).all()
            procedure.fill("history_list", history_list)
            procedure.fill("picture_list", procedure_picture_list)
            return Success(data=procedure)
        elif args.get("master_number"):
            procedure_dict = {}
            procedure_dict["procedure_type"] = args.get("procedure_type")
            procedure_dict["master_number"] = args.get("master_number")
            procedure_dict["inputer_id"] = getattr(request, "user").id
            user_dict = an_user.query.filter(an_user.user_id == getattr(request, "user").id).first_("未找到该用户")
            procedure_dict["inputer_name"] = user_dict.user_truename
            procedure_dict["inputer_card_no"] = user_dict.cardno
            procedure_dict["create_time"] = datetime.datetime.now()
            procedure_dict["preservation"] = "wait"
            id = str(uuid.uuid1())
            procedure_dict["id"] = id
            procedure_dict["master_number_cut"] = str(args.get("master_number"))[-4:] or ""
            main_port = t_bgs_main_single_number.query.filter(
                t_bgs_main_single_number.master_number == args.get("master_number")).first()
            if main_port:
                procedure_dict["port_of_departure"] = main_port.port_of_departure
                procedure_dict["destination_port"] = main_port.destination_port
                # 2020/12/1 增加字段
                procedure_dict["type_of_shipping"] = main_port.type_of_shipping
                procedure_dict["freight_type"] = main_port.freight_type
                # 数量用来填写
                procedure_dict["product_number"] = None
            with db.auto_commit():
                procedure_instance = an_procedure.create(procedure_dict)
                db.session.add(procedure_instance)

            procedure = an_procedure.query.filter(an_procedure.id == id).first()
            procedure.fill("picture_list", [])
            history_list = self._get_history_list(procedure)
            procedure.fill("history_list", history_list)
            return Success(data=procedure)
        else:
            return ParamsError()

    def _get_history_list(self, procedure):
        history_list = []
        if procedure.handover_inputer_id:
            history_dict = {}
            user = an_user.query.filter(an_user.user_id == procedure.handover_inputer_id).first()
            history_dict["procedure_status"] = "已入库"
            history_dict["area_name"] = "区域：" + (procedure.preservation_area or "")
            history_dict["storing_name"] = "仓位：" + (procedure.storing_location or "")
            if procedure.storing_location in ["大货区", "锂电池暂存区", "ETV区", "Stacker区"]:
                history_dict["preservation_type_name"] = None
                history_dict["board_no"] = "板号：" + (procedure.board_no or "")
            else:
                history_dict["preservation_type_name"] = "类别：" + procedure.preservation_type or ""
                history_dict["board_no"] = None
            history_dict["product_number"] = "件数：" + str(procedure.product_number or "")
            history_dict["weight"] = "重量：" + str(procedure.weight or "")
            if procedure.create_time:
                history_dict["inputer_time"] = "操作时间：" + procedure.create_time.strftime("%Y-%m-%d %H:%M") or ""
            else:
                history_dict["inputer_time"] = "操作时间：" + ""
            history_dict["inputer_name"] = "操作人：" + (user.user_truename or "")
            history_dict["inputer_card_no"] = "操作人身份证号：" + (user.cardno or "")
            history_list.append(history_dict)
        if procedure.delivery_inputer_id:
            history_dict = {}
            user = an_user.query.filter(an_user.user_id == procedure.delivery_inputer_id).first()
            history_dict["procedure_status"] = "已出库"
            history_dict["area_name"] = "区域：" + (procedure.preservation_area or "")
            history_dict["storing_name"] = "仓位：" + (procedure.storing_location or "")
            if procedure.storing_location in ["大货区", "锂电池暂存区", "ETV区", "Stacker区"]:
                history_dict["preservation_type_name"] = None
                history_dict["board_no"] = "板号：" + (procedure.board_no or "")
            else:
                history_dict["preservation_type_name"] = "类别：" + (procedure.preservation_type or "")
                history_dict["board_no"] = None
            history_dict["product_number"] = "件数：" + str(procedure.product_number or "")
            history_dict["weight"] = "重量：" + str(procedure.weight or "")
            if procedure.delivery_time:
                history_dict["inputer_time"] = "操作时间：" + procedure.delivery_time.strftime("%Y-%m-%d %H:%M") or ""
            else:
                history_dict["inputer_time"] = "操作时间：" + ""
            history_dict["inputer_name"] = "操作人：" + (user.user_truename or "")
            history_dict["inputer_card_no"] = "操作人身份证号：" + (user.cardno or "")
            history_list.append(history_dict)
        if procedure.repeat_warehousing_inputer_id:
            history_dict = {}
            user = an_user.query.filter(an_user.user_id == procedure.repeat_warehousing_inputer_id).first()
            history_dict["procedure_status"] = "已重新入库"
            history_dict["area_name"] = "区域：" + (procedure.preservation_area or "")
            history_dict["storing_name"] = "仓位：" + (procedure.storing_location or "")
            if procedure.storing_location in ["大货区", "锂电池暂存区", "ETV区", "Stacker区"]:
                history_dict["preservation_type_name"] = None
                history_dict["board_no"] = "板号：" + (procedure.board_no or "")
            else:
                history_dict["preservation_type_name"] = "类别：" + (procedure.preservation_type or "")
                history_dict["board_no"] = None
            history_dict["product_number"] = "件数：" + str(procedure.product_number or "")
            history_dict["weight"] = "重量：" + str(procedure.weight or "")
            if procedure.repeat_warehousing_time:
                history_dict["inputer_time"] = "操作时间：" + procedure.repeat_warehousing_time.strftime("%Y-%m-%d %H:%M") or ""
            else:
                history_dict["inputer_time"] = "操作时间：" + ""
            history_dict["inputer_name"] = "操作人：" + (user.user_truename or "")
            history_dict["inputer_card_no"] = "操作人身份证号：" + (user.cardno or "")
            history_list.append(history_dict)

        return history_list

    def list(self):
        """
        获取列表
        """
        args = parameter_required(("procedure_type", ))
        filter_args = []
        filter_args.append(an_procedure.procedure_type == args.get("procedure_type"))
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

        # TODO 2021/3/15 新增需求
        if args.get("preservation"):
            filter_args.append(an_procedure.preservation == args.get("preservation"))

        page_size = args.get("page_size") or 15
        page_num = args.get("page_num") or 1

        procedure_list = an_procedure.query.filter(*filter_args).order_by(an_procedure.create_time.desc()).all_with_page()

        i = 1
        for procedure in procedure_list:
            if not procedure.product_number:
                procedure.product_number = 0
            procedure.fill("procedure_no", int(page_size) * (int(page_num) - 1) + i)
            i = i + 1

        return Success(data=procedure_list)

    @token_required
    def stork_in(self):
        """
        入库
        """
        data = parameter_required(("handover_name", "handover_card_no", "area_id", "storing_id", "product_number",
                                   "weight", "procedure_id"))
        procedure_instance = an_procedure.query.filter(an_procedure.id == data.get("procedure_id")).first()
        procedure_dict = {}
        procedure_dict["handover_name"] = data.get("handover_name")
        procedure_dict["handover_card_no"] = data.get("handover_card_no")
        procedure_dict["handover_time"] = datetime.datetime.now()
        procedure_dict["handover_inputer_id"] = getattr(request, "user").id
        procedure_dict["handover_inputer_name"] = getattr(request, "user").username

        if data.get("preservation_id"):
            preservation = an_preservation_type.query.filter(an_preservation_type.id == data.get("preservation_id")) \
                .first_("未找到该类别")
            storing_id = preservation.storing_id
            if storing_id != data.get("storing_id"):
                return ParamsError("仓位中无此类别，请先选择仓位再选择类别")
            storing = an_storing_location.query.filter(an_storing_location.id == storing_id).first_("未找到该仓位")
            area_id = storing.area_id
            if area_id != data.get("area_id"):
                return ParamsError("该区域中无此仓位，请先选择区域再选择仓位")
            area = an_area.query.filter(an_area.id == data.get("area_id")).first_("未找到该区域")

            procedure_dict["preservation_type"] = preservation.preservation_type_name
        elif data.get("board_no"):
            storing = an_storing_location.query.filter(an_storing_location.id == data.get("storing_id")) \
                .first_("未找到该仓位")
            if storing.storing_location_name not in ["大货区", "锂电池暂存区", "ETV区", "Stacker区"]:
                return ParamsError("需要选择特殊仓位")
            area_id = storing.area_id
            if area_id != data.get("area_id"):
                return ParamsError("该区域中无此仓位，请先选择区域再选择仓位")
            area = an_area.query.filter(an_area.id == data.get("area_id")).first_("未找到该区域")

            procedure_dict["board_no"] = data.get("board_no")
        else:
            return ParamsError("请输入类别或者板号")

        procedure_dict["preservation_area"] = area.area_name
        procedure_dict["storing_location"] = storing.storing_location_name
        procedure_dict["weight"] = data.get("weight")
        procedure_dict["product_number"] = data.get("product_number")
        if data.get("remarks"):
            procedure_dict["remarks"] = data.get("remarks")

        procedure_dict["preservation"] = "in"
        # TODO 图片上传
        if data.get("picture_list"):
            for row in data.get("picture_list"):
                url_instance = an_procedure_picture.query.filter(an_procedure_picture.file_url == row)\
                    .first_("该图片未上传成功， 请重新上传")
                with db.auto_commit():
                    url_instance.update({
                        "procedure_id": data.get("procedure_id")
                    }, null="not")
                    db.session.add(url_instance)


        with db.auto_commit():
            procedure_instance.update(procedure_dict, null="not")
            db.session.add(procedure_instance)

        return Success(message="入库成功")

    @token_required
    def stork_out(self):
        """
        出库
        """
        data = parameter_required(("delivery_name", "delivery_card_no", "procedure_id"))
        procedure_instance = an_procedure.query.filter(an_procedure.id == data.get("procedure_id")).first()
        procedure_dict = {}
        procedure_dict["delivery_name"] = data.get("delivery_name")
        procedure_dict["delivery_card_no"] = data.get("delivery_card_no")
        procedure_dict["delivery_time"] = datetime.datetime.now()
        procedure_dict["preservation"] = "out"
        procedure_dict["delivery_inputer_id"] = getattr(request, "user").id
        procedure_dict["delivery_inputer_name"] = getattr(request, "user").username

        with db.auto_commit():
            procedure_instance.update(procedure_dict, null="not")
            db.session.add(procedure_instance)

        return Success(message="出库成功")

    @token_required
    def stork_repeat(self):
        """
        重新入库
        """
        data = parameter_required(("repeat_warehousing_name", "repeat_warehousing_card_no", "procedure_id"))
        procedure_instance = an_procedure.query.filter(an_procedure.id == data.get("procedure_id")).first()
        procedure_dict = {}
        procedure_dict["repeat_warehousing_name"] = data.get("delivery_name")
        procedure_dict["repeat_warehousing_card_no"] = data.get("delivery_card_no")
        procedure_dict["repeat_warehousing_time"] = datetime.datetime.now()
        procedure_dict["preservation"] = "repeat"
        procedure_dict["repeat_warehousing_inputer_id"] = getattr(request, "user").id
        procedure_dict["repeat_warehousing_inputer_name"] = getattr(request, "user").username

        with db.auto_commit():
            procedure_instance.update(procedure_dict, null="not")
            db.session.add(procedure_instance)

        return Success(message="重新入库成功")

    def get_master_number(self):
        """
        模糊搜索单号
        """
        args = parameter_required(("master_number", ))
        procedure = an_procedure.query.filter(an_procedure.master_number.like("%{0}%".format(args.get("master_number"))))\
            .all_with_page()
        master_dict = []
        for row in procedure:
            master_dict.append(row.master_number)
        return Success(data=master_dict)

    def update_procedure(self):
        """
        更新目的港/货运类型/运输方式/单号
        """
        data = json.loads(request.data)
        if data.get("type_of_shipping"):
            if data.get("type_of_shipping") not in ["PASSENGER AND CARGO AIRCRAFT", "CARGO AIRCRAFT ONLY"]:
                return {
                    "status": 405,
                    "status_code": 405202,
                    "message": "运输方式请填写‘PASSENGER AND CARGO AIRCRAFT’或者‘CARGO AIRCRAFT ONLY’"
                }
        else:
            data["type_of_shipping"] = None
        if data.get("freight_type"):
            if data.get("freight_type") not in ["RADIOACTIVE", "NON-RADIOACTIVE"]:
                return {
                    "status": 405,
                    "status_code": 405202,
                    "message": "货运类型请填写‘RADIOACTIVE’或‘NON-RADIOACTIVE’"
                }
        else:
            data["freight_type"] = None


        args = request.args.to_dict()
        if "procedure_id" not in args:
            return {
                "status": 405,
                "status_code": 405202,
                "message": "procedure_id参数缺失"
            }
        procedure = an_procedure.query.filter(an_procedure.id == args.get("procedure_id")).first_("未找到数据")
        with db.auto_commit():
            procedure_dict = {
                "id": args.get("procedure_id"),
                "type_of_shipping": data.get("type_of_shipping"),
                "freight_type": data.get("freight_type"),
                "destination_port": data.get("destination_port")
            }
            procedure_instance = procedure.update(procedure_dict, null="not")
            db.session.add(procedure_instance)
        return Success("编辑成功")

    def update_procedure_master_number(self):
        """
        更新单号
        """
        args = request.args.to_dict()
        if "procedure_id" not in args:
            return {
                "status": 405,
                "status_code": 405202,
                "message": "procedure_id参数缺失"
            }

        data = json.loads(request.data)
        if data.get("master_number"):
            master_number_cut = str(data.get("master_number"))[-4:] or ""
        else:
            master_number_cut = ""

        procedure = an_procedure.query.filter(an_procedure.id == args.get("procedure_id")).first_("未找到数据")
        with db.auto_commit():
            procedure_dict = {
                "id": args.get("procedure_id"),
                "master_number": data.get("master_number"),
                "master_number_cut": master_number_cut
            }
            procedure_instance = procedure.update(procedure_dict, null="not")
            db.session.add(procedure_instance)
        return Success("编辑成功")