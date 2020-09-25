# -*- coding: utf-8 -*-

from sqlalchemy import Integer, String, Text, DateTime, orm, Boolean
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