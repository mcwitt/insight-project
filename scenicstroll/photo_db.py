from sqlalchemy import BigInteger, Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
from geoalchemy2 import Geography


Base = declarative_base()


class Photo(Base):
    __tablename__ = 'photo'
    id = Column(BigInteger, primary_key=True)
    datetaken = Column(DateTime)
    location = Column(Geography('POINT'))
    owner = Column(String)
    ownername = Column(String)
    url = Column(String)
    views = Column(Integer)
    label = Column(Integer, ForeignKey('cluster.label'))


class PhotoCluster(Base):
    __tablename__ = 'cluster'
    label = Column(Integer, primary_key=True)
    centroid = Column(Geography('POINT'))
    num_photos = Column(Integer)
    most_viewed = Column(BigInteger)
    photos = relationship('Photo', backref='cluster')


def create_tables(engine):
    Base.metadata.create_all(engine)


