# -*- coding: utf-8 -*-

from sqlalchemy import Integer, String, Text, DateTime, orm, Boolean
from FanstiBgs.extensions.base_model import Base, Column
import datetime

class oauth_client_details(Base):
    __tablename__ = "oauth_client_details"
    client_id = Column(String(255), primary_key=True)
    resource_ids = Column(String(255))
    client_secret = Column(String(255), nullable=False)
    scope = Column(String(255), nullable=False)
    authorized_grant_types = Column(String(255), nullable=False)
    web_server_redirect_uri = Column(String(255))
    authorities = Column(String(255))
    access_token_validity = Column(Integer, nullable=False)
    refresh_token_validity = Column(Integer, nullable=False)
    additional_information = Column(Text)
    autoapprove = Column(Boolean, nullable=False)
    origin_secret = Column(String(255))

class t_bgs_file(Base):
    """
    文件存储
    """
    id = Column(String(40), primary_key=True)
    file_name = Column(String(100), comment="文件名")
    file_type = Column(String(10), comment="文件类型1,2,3")
    file_src = Column(String(255), comment="文件路径")
    f_id = Column(String(40), comment="关联外键")
    file_suffix = Column(String(20), comment="文件后缀")
    create_time = Column(DateTime, default=datetime.datetime.now())

class t_bgs_main_single_number(Base):
    """
    主单号表
    """
    id = Column(String(40), primary_key=True)
    master_number = Column(String(30), comment="主单号")
    type_of_shipping = Column(String(255), comment="运输方式")
    freight_type = Column(String(255), comment="货运类型")
    port_of_departure = Column(String(255), comment="起运港")
    destination_port = Column(String(255), comment="目的港")
    emergency_contact = Column(String(255), comment="紧急联系人电话")
    ATTN = Column(String(255), comment="紧急联系人")
    statement = Column(String(255), comment="声明")
    statement_name = Column(String(255), comment="声明人名称")
    statement_title = Column(String(255), comment="声明人职务")
    statement_address = Column(String(255), comment="声明人地址")
    name_image_file = Column(String(255), comment="签名图片位置")
    WARNING = Column(String(255), comment="警告")
    create_time = Column(DateTime, default=datetime.datetime.now())
    place_an_data = Column(String(255), comment="签名日期")

class t_bgs_odd_number(Base):
    """
    分单号表
    """
    id = Column(String(40), primary_key=True)
    odd_number = Column(String(50), comment="分单号")
    master_number = Column(String(40), comment="对应的主单号")

class t_bgs_packing_dictionaries(Base):
    """
    包装名称表
    """
    id = Column(Integer, primary_key=True, autoincrement=True)
    packing_name = Column(String(255), comment="包装名称")
    packing_name_englist = Column(String(255), comment="包装英文")
    packing_id = Column(Integer)

