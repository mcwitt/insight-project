from sqlalchemy import cast, create_engine, func
from sqlalchemy import BigInteger, Column, Float, ForeignKey, Integer, String
from sqlalchemy.orm import relationship, sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from geoalchemy2 import Geography
from geoalchemy2.functions import ST_X, ST_Y


Base = declarative_base()


class Node(Base):
    __tablename__ = 'node'
    id = Column(BigInteger, primary_key=True)
    loc = Column(Geography('POINT'), index=True)
    num_ways = Column(Integer)
    ways = relationship('Segment', backref='node', cascade='delete')


class Score(Base):
    __tablename__ = 'score'
    seg_id = Column(Integer, ForeignKey('segment.id'), primary_key=True)
    score = Column(Float)
    cscore = Column(Float)


class WayType(Base):
    __tablename__ = 'way_type'
    id = Column(Integer, primary_key=True)
    name = Column(String)


class Way(Base):
    __tablename__ = 'way'
    id = Column(BigInteger, primary_key=True)
    name = Column(String)
    way_type_id = Column(Integer, ForeignKey('way_type.id'))

    
class Segment(Base):
    __tablename__ = 'segment'
    id = Column(Integer, primary_key=True)
    way_id = Column(BigInteger, ForeignKey('way.id'), index=True)
    idx = Column(Integer)
    node_id = Column(BigInteger, ForeignKey('node.id'))
    dist = Column(Float)
    cdist = Column(Float)
    way = relationship('Way', backref='way_segments')


class RouteDB:

    def __init__(self, url):
        self.engine = create_engine(url)
        Session = sessionmaker(bind=self.engine)
        self.session = Session()


    def create_tables(self):
        Base.metadata.create_all(self.engine)


    def get_routing_data(self, lat, lon, radius):
        pt = 'POINT({} {})'.format(lon, lat)
        query = (
            self.session
            .query(Segment, Score)
            .join(Node)
            .join(Score)
            .filter(Node.loc.ST_DWithin(pt, radius) &
                   (Node.num_ways != 0) &
                   (Node.num_ways != 2))
            .order_by(Segment.way_id, Segment.idx))

        return query


    def nearest_rnodes(self, lat, lon, radius):
        pt = 'SRID=4326;POINT({} {})'.format(lon, lat)
        return (self.session
                .query(Node)
                .filter(Node.loc.ST_DWithin(pt, radius) &
                       (Node.num_ways != 0))
                .order_by(Node.loc.ST_Distance(pt)))


