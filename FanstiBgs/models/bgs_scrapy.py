# -*- coding: utf-8 -*-

from sqlalchemy import Integer, String, Text, DateTime, orm, Boolean, DATE
from FanstiBgs.extensions.base_model import Base, Column
import datetime

class air_hwys_lines(Base):
    __tablename__ = "air_hwys_lines"
    id = Column(String(200), primary_key=True)                  # 主键id
    airline = Column(String(200))                               # 航线编号
    aircompany = Column(String(200))                            # 航空公司
    airname = Column(String(200))                               # 航空类型
    flight = Column(String(200))                                # 航班编号
    depa = Column(String(50))                                   # 起飞地
    dest = Column(String(50))                                   # 目的地
    mydate = Column(String(50))                                 # 航班日期
    etd = Column(String(50))                                    # 起飞时间
    eta = Column(String(50))                                    # 落地时间
    supporttime = Column(String(100))                           # 交单时间
    aircraft = Column(String(200))                              # 机型
    remark = Column(Text)                                       # 备注

class air_hwys_dgr(Base):
    __tablename__ = "air_hwys_dgr"
    id = Column(String(200), primary_key=True)              # 主键
    unno = Column(String(200))                              # UN号
    unname = Column(String(200))                            # 运输专用名称
    untype = Column(String(40))                             # 类别

class air_hwys_dgr_level(Base):
    __tablename__ = "air_hwys_dgr_level"
    id = Column(String(200), primary_key=True)              # 主键
    dgr_id = Column(String(200))                            # 关联外键
    dgr_level = Column(String(200))                         # 等级
    airliner_capacity = Column(String(200))                 # 客机容量
    airliner_description_no = Column(String(200))           # 客机说明号
    airliner_is_single = Column(String(200))                # 客机是否可单一
    airfreighter_capacity = Column(String(200))             # 货机容量
    airfreighter_description_no = Column(String(200))       # 货机说明号
    airfreighter_is_single = Column(String(200))            # 货机是否可单一
    message = Column(String(2000))                          # 备注

class air_hwys_dgr_container(Base):
    __tablename__ = "air_hwys_dgr_container"
    id = Column(String(200), primary_key=True)              # 主键
    dgr_level_id = Column(String(200))                      # 关联外键
    dgr_container = Column(String(200))                     # 容器类型
    dgr_container_capacity = Column(String(200))            # 容量
    dgr_type = Column(String(60))                           # 客机/货机
    dgr_container_message = Column(String(2000))            #

class air_hwys_jd(Base):
    __tablename__ = "air_hwys_jd"
    id = Column(String(200), primary_key=True)                  # 主键id
    jcno = Column(String(1000))                                 # 进仓编号
    createtime = Column(DATE, default=datetime.datetime.now())  # 创建时间
    endtime = Column(DATE)                                      # 出鉴定日期
    reportno = Column(String(1000))                             # 报告编号
    chinesename = Column(String(2000))                          # 中文品名
    englishname = Column(String(2000))                          # 英文品名
    appearance = Column(String(200))                            # 外观-颜色
    identificationunits = Column(String(200))                   # 鉴定委托单位
    cost = Column(String(200), default="未填写")                # 费用
    remarks = Column(String(2000))                              # 备注
    principal = Column(String(200))                             # 鉴定委托人
    jdtime = Column(DATE)                                       # 做鉴定日期
    singlenode = Column(String(20))                             # 是否结单
    crz = Column(String(200))                                   # 客服人
    unno = Column(String(200))                                  # UN信息
    wphw = Column(String(20))                                   # 危险品/普货
    cz = Column(String(200))                                    # 单据操作者
    flag = Column(String(10))                                   # 是否带入中文品名
    flag2 = Column(String(10))                                  # 是否带入英文品名
    flag3 = Column(String(10))                                  # 是否带入成本费用
    flag4 = Column(String(10), default="0")                     # 展示标识
    flag5 = Column(String(10))                                  # 带入鉴定单
    factory = Column(String(200))                               # 生产厂家
    appearance2 = Column(String(200))                           # 外观-状态
    casno = Column(String(100))                                 # CAS NO号码
    costtype = Column(String(50))                               # 费用种类

class t_bgs_un_dictionaries(Base):
    __tablename__ = "t_bgs_un_dictionaries"
    id = Column(Integer, primary_key=True)
    UNNumberA = Column(String(11), comment="UN编号")
    ProperShippingNameB = Column(String(5000), comment="英文品名")
    ClassDivSubC = Column(String(255))
    HazardLabelsD = Column(String(255))
    PackingGroupE = Column(String(255))
    ExceptedQtyF = Column(String(255))
    PCALtdQtyPIG = Column(String(255))
    PCALtdQtyMaxNetQtyH = Column(String(255))
    PCAPII = Column(String(255))
    PCAMaxNetQtyJ = Column(String(255))
    CAOPIK = Column(String(255))
    CAOMaxNetQtyL = Column(String(255))
    SPM = Column(String(255))
    ERGN = Column(String(255))
    ColumnENEqui = Column(String(255))
    ColumnSORT = Column(String(3000))
    ColumnBOLD = Column(String(5000))
    ColumnSearch = Column(String(5000))
    Images = Column(String(255))