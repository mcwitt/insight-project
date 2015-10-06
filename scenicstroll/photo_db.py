from sqlalchemy import Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship
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
    cluster_id = Column(Integer, ForeignKey('cluster.id'))


class PhotoCluster(Base):
    __tablename__ = 'cluster'
    id = Column(Integer, primary_key=True)
    num_photos = Column(Integer)
    photos = relationship('Photo', backref='cluster')


def create_tables(engine):
    Base.metadata.create_all(engine)


class PhotoDB:

    def __init__(self, session):
        self.session = session

    
