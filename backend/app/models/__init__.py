"""
数据模型模块
"""

from sqlalchemy import Column, Integer, String, DateTime, Boolean
from app.core.db import Base


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(64), unique=True, index=True, nullable=False)
    password = Column(String(255), nullable=False)
    email = Column(String(255), nullable=True)
    phone = Column(String(32), nullable=True, index=True)


class VerifyCode(Base):
    __tablename__ = "verify_codes"
    id = Column(Integer, primary_key=True, index=True)
    scene = Column(String(32), nullable=False)
    target = Column(String(255), index=True, nullable=False)  # phone or email
    code = Column(String(16), nullable=False)
    expire_at = Column(DateTime, nullable=False)
    verified = Column(Boolean, default=False)
