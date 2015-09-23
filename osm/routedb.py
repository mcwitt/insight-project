from sqlalchemy import BigInteger, Column, ForeignKey, Integer, String, distinct
from sqlalchemy.ext.declarative import declarative_base
from geoalchemy2 import Geometry
from xml.etree.cElementTree import iterparse

walkable_types = (
    'primary',
    'secondary',
    'tertiary',
    'residential',
    'living_street',
    'pedestrian',
    'track',
    'steps',
    'path',
    'footway',
    'steps',
    'path'
)

type_id = {t: i for i, t in enumerate(walkable_types)}

Base = declarative_base()

class Node(Base):
    __tablename__ = 'node'
    id = Column(BigInteger, primary_key=True)
    location = Column(Geometry('POINT', srid=4326))
    
class Way(Base):
    __tablename__ = 'way'
    id = Column(BigInteger, primary_key=True)
    name = Column(String)
    type_id = Column(Integer, ForeignKey('type.id'))
    
class Topology(Base):
    __tablename__ = 'topology'
    id = Column(BigInteger, primary_key=True)
    node_id = Column(BigInteger, ForeignKey('node.id'))
    way_id = Column(BigInteger, ForeignKey('way.id'))
    order = Column(Integer)
    
class Type(Base):
    __tablename__ = 'type'
    id = Column(Integer, primary_key=True)
    name = Column(String)


def parse_and_remove(source, path):
    '''
    Parse XML using small memory footprint.
    From Python cookbook except for additions XXX.
    '''
    
    path_parts = path.split('/')
    doc = iterparse(source, ('start', 'end'))
    
    # Skip the root element
    next(doc)

    tag_stack = []
    elem_stack = []
    for event, elem in doc:
        if event == 'start':
            tag_stack.append(elem.tag)
            elem_stack.append(elem)
        elif event == 'end':
            if tag_stack == path_parts:
                yield elem
                try: # XXX
                    elem_stack[-2].remove(elem)
                except IndexError: # XXX
                    pass
            try:
                tag_stack.pop()
                elem_stack.pop()
            except IndexError:
                pass


def _maybe_add_way(elem, session):

    name = None
    way_type = None
    
    # scan tags for type and name
    for tag in elem.iterfind('tag'):
        
        if tag.get('k') == 'highway':
            way_type = tag.get('v')
            if way_type not in type_id: # not walkable
                return
            
        if tag.get('k') == 'name':
            name = tag.get('v')
    
    if way_type is None:    # no `highway` tag
        return
    
    way_id = int(elem.get('id'))
    way = Way(id=way_id, name=name, type_id=type_id[way_type])
    session.add(way)
    session.commit()
    
    # add topology
    for i, nd in enumerate(elem.iterfind('nd')):
        session.add(Topology(node_id=int(nd.get('ref')),
                             way_id=way_id,
                             order=i))


def parse_osm(source, session):

    # node table
    for i, elem in enumerate(parse_and_remove(source, 'node')):
        lat, lon = (elem.get(_) for _ in ('lat', 'lon'))
        session.add(Node(id=int(elem.get('id')),
                    location='SRID=4326;POINT({} {})'.format(lat, lon)))
        if (i+1) % 10000 == 0:
            print('processed {} nodes'.format(i+1))
            session.commit()

    # type table
    for i, t in enumerate(walkable_types):
        session.add(Type(id=i, name=t))

    session.commit()

    # way and topology tables
    for i, elem in enumerate(parse_and_remove(source, 'way')):
        _maybe_add_way(elem, session)
        if (i+1) % 10000 == 0:
            print('processed {} ways'.format(i+1))
            session.commit()

    # remove unused nodes
    used_nodes = session.query(distinct(Topology.node_id)).subquery()
    unused_nodes = session.query(Node).filter(~Node.id.in_(used_nodes))

    for node in unused_nodes:
        session.delete(node)

    session.commit()


if __name__ == '__main__':

    from argparse import ArgumentParser
    from bz2 import BZ2File
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    parser = ArgumentParser()
    parser.add_argument('input', type=str, help='OSM XML file')
    parser.add_argument('db', type=str, help='PostgreSQL database')
    args = parser.parse_args()

    engine = create_engine(args.db)
    Base.metadata.create_all(engine)

    Session = sessionmaker(bind=engine)
    session = Session()

    #with BZ2File(args.input) as f:
    #    parse_osm(f, session)

    parse_osm(args.input, session)
