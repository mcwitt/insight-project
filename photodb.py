from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.ext.declarative import declarative_base
from geoalchemy2 import Geography

Base = declarative_base()

class Photo(Base):
    __tablename__ = 'photo'
    id = Column(Integer, primary_key=True)
    datetaken = Column(DateTime)
    location = Column(Geography('POINT'))
    owner = Column(String)
    ownername = Column(String)
    url = Column(String)
    views = Column(Integer)
    label = Column(Integer)
