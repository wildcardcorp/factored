from sqlalchemy import Column, Integer, Text, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from factored.sm import registerSession
from datetime import datetime
from factored.utils import make_random_code


DBSession = sessionmaker()
registerSession('f', DBSession)
Base = declarative_base()


def generate_user_code():
    return make_random_code(12)


class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    username = Column(Text, unique=True)
    secret = Column(Text, unique=True)
    generated_code = Column(Text, default=generate_user_code)
    generated_code_time_stamp = Column(DateTime, default=datetime.utcnow)

    def __init__(self, username, secret):
        self.username = username
        self.secret = secret
