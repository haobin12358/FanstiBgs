# -*- coding: utf-8 -*-

from sqlalchemy import Integer, String, Text, DateTime, orm
from FanstiBgs.extensions.base_model import Base, Column

class oauth_client_details(Base):
    __tablename__ = "oauth_client_details"
    client_id = Column(String(255), primary_key=True)
    resource_ids = Column(String(255), nullable=False)
