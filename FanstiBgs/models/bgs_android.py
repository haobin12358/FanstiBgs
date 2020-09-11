# -*- coding: utf-8 -*-

from sqlalchemy import Integer, String, Text, DateTime, orm, Boolean
from FanstiBgs.extensions.base_model import Base, Column
import datetime

class an_user(Base):
    """
    android端用户表
    """
    __tablename__ = "an_user"
    user_id = Column(String(40), primary_key=True)
    user_name = Column(String(255), nullable=False, comment="用户名")
    user_password = Column(String(128), nullable=False, comment="密码")
    user_mobile = Column(String(20), comment="手机号")
    isdelete = Column(Boolean, default=False, comment="状态0可用1不可用")
    createtime = Column(DateTime, default=datetime.datetime.now(), nullable=False, comment="创建时间")
    updatetime = Column(DateTime, default=datetime.datetime.now(), nullable=False, comment="更新时间")
    cardno = Column(String(255), comment="证件号")
    cardtype = Column(String(10), comment="证件类型1身份证2护照3港澳台")
    user_sex = Column(String(10), comment="性别1男2女")
    user_truename = Column(String(50), nullable=False, comment="姓名")
    user_email = Column(String(128), comment="邮箱")
    user_level = Column(String(10), default="0", comment="用户权限")

class an_procedure(Base):
    """
    进出港
    """
    __tablename__ = "an_procedure"
    id = Column(String(40), primary_key=True)
    master_number = Column(String(40), nullable=False, comment="运单号")
    port_of_departure = Column(String(255), comment="起运港")
    destination_port = Column(String(255), comment="目的港")
    product_number = Column(Integer, comment="件数")
    preservation_area = Column(String(128), comment="区域")
    storing_location = Column(String(128), comment="仓位")
    preservation_type = Column(String(128), comment="类别")
    board_no = Column(String(255), comment="板号")
    weight = Column(Integer, comment="重量")
    remarks = Column(String(255), comment="备注")
    inputer_id = Column(String(40), comment="操作人id", nullable=False)
    inputer_name = Column(String(50), comment="操作人", nullable=False)
    inputer_card_no = Column(String(255), comment="操作人证件号", nullable=False)
    handover_name = Column(String(50), comment="交接人")
    handover_card_no = Column(String(255), comment="交接人身份证号")
    delivery_name = Column(String(50), comment="出库人")
    delivery_card_no = Column(String(255), comment="出库人身份证号")
    repeat_warehousing_name = Column(String(50), comment="重新入库人")
    repeat_warehousing_card_no = Column(String(255), comment="重新入库人身份证号")
    create_time = Column(DateTime, default=datetime.datetime.now(), comment="创建时间")
    handover_time = Column(DateTime, comment="交接时间")
    delivery_time = Column(DateTime, comment="出库时间")
    repeat_warehousing_time = Column(DateTime, comment="重新入库时间")
    procedure_type = Column(String(10), comment="出入港类型，in入港out出港")
    preservation = Column(String(10), comment="出入库状态，in入库out出库repeat重新入库")

class an_procedure_picture(Base):
    """
    进出港图片
    """
    __tablename__ = "an_procedure_picture"
    id = Column(String(40), primary_key=True)
    procedure_id = Column(String(40), nullable=False)
    file_name = Column(String(100), comment="图片名")
    file_src = Column(String(255), comment="图片路径")
    file_url = Column(String(255), comment="图片路由")

class an_area(Base):
    """
    区域
    """
    __tablename__ = "an_area"
    isdelete = Column(Boolean, default=0)
    id = Column(String(40), primary_key=True)
    area_name = Column(String(128), comment="区域名称")

class an_storing_location(Base):
    """
    仓位
    """
    __tablename__ = "an_storing_location"
    isdelete = Column(Boolean, default=0)
    id = Column(String(40), primary_key=True)
    area_id = Column(String(40), comment="区域id")
    storing_location_name = Column(String(128), comment="仓位名称")

class an_preservation_type(Base):
    """
    类别
    """
    __tablename__ = "an_preservation_type"
    isdelete = Column(Boolean, default=0)
    id = Column(String(40), primary_key=True)
    storing_id = Column(String(40), comment="仓位id")
    preservation_type_name = Column(String(128), comment="类别名称")