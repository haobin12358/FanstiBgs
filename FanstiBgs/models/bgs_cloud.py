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
    __tablename__ = "t_bgs_file"
    id = Column(String(40), primary_key=True)
    file_name = Column(String(100), comment="文件名")
    file_type = Column(String(10), comment="文件类型1,2,3")
    file_src = Column(String(255), comment="文件路径")
    f_id = Column(String(40), comment="关联外键")
    file_suffix = Column(String(20), comment="文件后缀")
    create_time = Column(DateTime, default=datetime.datetime.now())
    file_class = Column(String(100), comment="标记")

class t_bgs_main_single_number(Base):
    """
    主单号表
    """
    __tablename__ = "t_bgs_main_single_number"
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
    place_and_data = Column(String(255), comment="签名日期")
    note = Column(String(255), comment="备注")
    is_print = Column(String(255), comment="是否生成预申报单预览1生成0不生成")
    is_pack = Column(String(255), comment="是否打包")
    order_time = Column(String(255), comment="预约时间")

class t_bgs_odd_number(Base):
    """
    分单号表
    """
    __tablename__ = "t_bgs_odd_number"
    id = Column(String(40), primary_key=True)
    odd_number = Column(String(50), comment="分单号")
    master_number = Column(String(40), comment="对应的主单号")

class t_bgs_un(Base):
    """un与主分单对应表"""
    __tablename__ = "t_bgs_un"
    id = Column(String(40), primary_key=True)
    UN_NUMBER = Column(String(255), comment="UN编号")
    packaging_instruction = Column(String(255), comment="包装指导")
    packaging_grade = Column(String(255), comment="包装等级")
    packaging_category = Column(String(255), comment="包装类别")
    product_Name = Column(String(255), comment="品名")
    introduce = Column(String(255), comment="说明")
    MAIN_DANGEROUS_ID = Column(Integer, comment="主要危险品id")
    SECOND_DANGEROUS_IDA = Column(String(255), comment="次要危险品ida")
    SECOND_DANGEROUS_IDB = Column(String(255), comment="次要危险品idb")
    odd_number = Column(String(40), comment="分单号")
    master_number = Column(String(255), comment="主单号")
    RadioactivityLevel = Column(String(255), comment="放射性等级")
    TIM = Column(String(255))
    nuclideName = Column(String(255))
    height = Column(String(255))
    width = Column(String(255))
    un_long = Column(String(255))
    weight = Column(String(255), comment="重量")
    unit = Column(String(255), comment="单位")
    packNumber = Column(String(255), comment="件数")
    material = Column(String(255), comment="材质")
    TechnicalName = Column(String(255), comment="技术名称")
    productNameSelect = Column(String(255), comment="两个特殊下拉项")
    difference = Column(String(255))

class t_bgs_un_pack(Base):
    """
    包装详情
    """
    __tablename__ = "t_bgs_un_pack"
    id = Column(Integer, primary_key=True, autoincrement=True)
    status = Column(String(255), comment="打包状态")
    packInfo = Column(String(255), comment="打包信息")
    Qnumber = Column(Integer)
    material = Column(String(255))
    introduceX = Column(String(255))
    packNumber = Column(String(255))
    unit = Column(String(255), comment="单位")
    oddNumberId = Column(String(255), comment="分单号id")
    oddNumber = Column(String(255), comment="分单号")
    masterNumber = Column(String(255), comment="主单号id")
    unNumber = Column(String(255), comment="UN编号")
    unNumberId = Column(String(255), comment="UN编号id")
    MAIN_DANGEROUS_ID = Column(Integer, comment="主要危险品ID")
    packaging_category = Column(String(255), comment="包装类别")
    product_name = Column(String(255), comment="品名")
    TechnicalName = Column(String(255), comment="技术名称")
    productNameSelect = Column(String(255), comment="两个特殊下拉项")
    difference = Column(String(255))

class t_bgs_packing_dictionaries(Base):
    """
    包装名称表
    """
    __tablename__ = "t_bgs_packing_dictionaries"
    id = Column(Integer, primary_key=True, autoincrement=True)
    packing_name = Column(String(255), comment="包装名称")
    packing_name_englist = Column(String(255), comment="包装英文")
    packing_id = Column(Integer)

class t_bgs_shipper_consignee_info(Base):
    """
    收发货人信息表
    """
    __tablename__ = "t_bgs_shipper_consignee_info"
    id = Column(String(40), primary_key=True)
    company_name = Column(String(255), comment="公司名称")
    company_address = Column(String(255), comment="公司地址")
    country = Column(String(255), comment="国家")
    phone = Column(String(255), comment="电话")
    name = Column(String(255), comment="姓名")
    mailbox = Column(String(255), comment="邮箱")
    fax = Column(String(255), comment="传真")
    state_code = Column(String(255), comment="洲代码")
    info_state = Column(String(255), comment="货运人信息状态1发货人2收货人")
    odd_number = Column(String(40), comment="归属分单号")
    master_number = Column(String(255), comment="主单号")
    city = Column(String(255), comment="城市")
