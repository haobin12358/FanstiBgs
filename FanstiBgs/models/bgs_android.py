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