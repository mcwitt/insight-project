from sqlalchemy import create_engine, BigInteger, Column, Float, ForeignKey, Integer, String
from sqlalchemy.orm import relationship, sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from geoalchemy2 import Geography


Base = declarative_base()


class Node(Base):
    __tablename__ = 'node'
    id = Column(BigInteger, primary_key=True)
    loc = Column(Geography('POINT'))
    ways = relationship('WayNode', backref='node', cascade='delete')
    

class WayType(Base):
    __tablename__ = 'way_type'
    id = Column(Integer, primary_key=True)
    name = Column(String)


class Way(Base):
    __tablename__ = 'way'
    id = Column(BigInteger, primary_key=True)
    name = Column(String)
    way_type_id = Column(Integer, ForeignKey('way_type.id'))

    
class WayNode(Base):
    __tablename__ = 'way_node'
    way_id = Column(BigInteger, ForeignKey('way.id'), primary_key=True)
    idx = Column(Integer, primary_key=True)
    node_id = Column(BigInteger, ForeignKey('node.id'))
    dist = Column(Float)
    cdist = Column(Float)
    score = Column(Float)
    cscore = Column(Float)
    way = relationship('Way', backref='way_nodes')
    

class RouteDB:

    def __init__(self, url):
        self.engine = create_engine(url)
        Session = sessionmaker(bind=self.engine)
        self.session = Session()

    def create_tables(self):
        Base.metadata.create_all(self.engine)

