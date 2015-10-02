from sqlalchemy import cast, create_engine, distinct, func
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
    ways = relationship('Waypoint', backref='node', cascade='delete')


class WayType(Base):
    __tablename__ = 'way_type'
    id = Column(Integer, primary_key=True)
    name = Column(String)


class Way(Base):
    __tablename__ = 'way'
    id = Column(BigInteger, primary_key=True)
    name = Column(String)
    way_type_id = Column(Integer, ForeignKey('way_type.id'))

    
class Waypoint(Base):
    __tablename__ = 'waypoint'
    id = Column(Integer, primary_key=True)
    way_id = Column(BigInteger, ForeignKey('way.id'), index=True)
    idx = Column(Integer)
    node_id = Column(BigInteger, ForeignKey('node.id'))
    cdist = Column(Float)
    cscore = Column(Float)
    way = relationship('Way', backref='waypoints')



class RouteDB:

    def __init__(self, url):
        self.engine = create_engine(url)
        Session = sessionmaker(bind=self.engine)
        self.session = Session()


    def create_tables(self):
        Base.metadata.create_all(self.engine)


    def _in_neighborhood(self, node1, node2, expand=1):

        geo1 = cast(node1.loc, Geography)
        geo2 = cast(node2.loc, Geography)
        radius = self.session.query(geo1.ST_Distance(geo2)).first()[0]
        radius *= expand

        return (Node.loc.ST_DWithin(geo1, radius) |
                Node.loc.ST_DWithin(geo2, radius))


    def get_waypoints(self, node1, node2, expand=1):

        is_routing_entry = (
            (Node.num_ways > 1) |
            (Node.id in (node1.id, node2.id)))

        return (
            self.session
            .query(Waypoint)
            .join(Node)
            .filter(self._in_neighborhood(node1, node2, expand) & is_routing_entry)
            .order_by(Waypoint.way_id, Waypoint.idx))


    def nearest_rnodes(self, lat, lon, radius):
        pt = cast('POINT({} {})'.format(lon, lat), Geography)
        return (
            self.session
            .query(Node)
            .filter(Node.loc.ST_DWithin(pt, radius) &
                   (Node.num_ways > 1)) # only look at intersections for now...
            .order_by(Node.loc.ST_Distance(pt)))


