import numpy as np
from sqlalchemy import cast, create_engine, distinct, func
from sqlalchemy import BigInteger, Column, Float, ForeignKey, Integer, String
from sqlalchemy.orm import relationship, sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from geoalchemy2 import Geography, Geometry
from geoalchemy2.functions import ST_X, ST_Y
from itertools import islice


Base = declarative_base()


def _grouper(n, iterable):
    it = iter(iterable)
    while True:
       chunk = tuple(islice(it, n))
       if not chunk:
           return
       yield chunk


class Node(Base):
    __tablename__ = 'node'
    id = Column(BigInteger, primary_key=True)
    loc = Column(Geography('POINT'), index=True)
    score = Column(Float)
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


def create_tables(engine):
    Base.metadata.create_all(engine)


class RouteDB:

    def __init__(self, session):
        self.session = session


    def _in_neighborhood(self, node1, node2, expand=1):

        geog1 = cast(node1.loc, Geography)
        geog2 = cast(node2.loc, Geography)
        radius = self.session.query(geog1.ST_Distance(geog2)).first()[0]
        radius *= expand

        return (Node.loc.ST_DWithin(geog1, radius) |
                Node.loc.ST_DWithin(geog2, radius))


    def get_relevant_waypoints(self, node1, node2, expand=1):

        # is intersection or terminal point
        is_xnode_or_terminal = (
            (Node.num_ways > 1) | (Node.id == node1.id) | (Node.id == node2.id))

        in_neighborhood = self._in_neighborhood(node1, node2, expand)

        return (
            self.session
            .query(Waypoint)
            .join(Node)
            .filter(in_neighborhood & is_xnode_or_terminal)
            .order_by(Waypoint.way_id, Waypoint.idx))


    def get_nearest_xnodes(self, lat, lon, radius):
        pt = cast('POINT({} {})'.format(lon, lat), Geography)
        return (
            self.session
            .query(Node)
            .filter(Node.loc.ST_DWithin(pt, radius) &
                   (Node.num_ways > 1)) # XXX: only allow intersections for now...
            .order_by(Node.loc.ST_Distance(pt)))


    def update_scores(self, model, chunksize=10000):

        # update node scores
        waypoint_nodes = (
            self.session.query(
                Node,
                ST_X(cast(Node.loc, Geometry)),
                ST_Y(cast(Node.loc, Geometry)))
                .filter(Node.num_ways != 0)
                .order_by(func.random()))   # random order

        # process nodes in chunks for memory efficiency.
        # note: normalization of scores is done per chunk, which should be a
        # reasonable approximation to global normalization when the chunks are
        # large since the query specifies random ordering
        for chunk in _grouper(chunksize, waypoint_nodes):
            nodes, x, y = zip(*chunk)
            X = np.vstack((x, y)).T
            scores = model.score_samples(X)
            for node, score in zip(nodes, scores):
                node.score = score

        # update cumulative scores
        sq = (
            self.session.query(
                Waypoint.id.label('id'),
                func.sum(Node.score).over(
                    partition_by=Waypoint.way_id,
                    order_by=Waypoint.idx).label('cscore'))
                .join(Node)
                .subquery())

        (self.session.query(Waypoint)
             .filter(Waypoint.id == sq.c.id)
             .update({Waypoint.cscore: sq.c.cscore}))

