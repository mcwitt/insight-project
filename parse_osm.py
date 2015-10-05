from datetime import datetime
from time import time
from xml.etree.cElementTree import iterparse
from scenicstroll.route_db import create_tables, Node, Waypoint, Way, WayType


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

class Logger:
    def __init__(self, f):
        self.f = f

    def write(self, mesg):
        ts = time()
        st = datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S')
        self.f.write('[{}] {}\n'.format(st, mesg))
        self.f.flush()


def parse_tags(source, tags):
    for event, elem in iterparse(source):
        if elem.tag in tags:
            yield elem
            elem.clear()


def _inside_bbox(x, y, bbox):
    xmin, ymin, xmax, ymax = bbox
    return (x > xmin and y > ymin and
            x < xmax and y < ymax)


def _maybe_add_way(elem, session):

    name = None
    way_type = None
    
    # scan tags for type and name
    for tag in elem.iterfind('tag'):
        
        if tag.get('k') == 'highway':
            way_type = tag.get('v')
            if way_type not in type_id: # not walkable
                return False
            
        if tag.get('k') == 'name':
            name = tag.get('v')
    
    if way_type is None:    # no `highway` tag; ignore
        return False
    
    way_id = int(elem.get('id'))
    way = Way(id=way_id, name=name, way_type_id=type_id[way_type])
    session.add(way)
    session.commit()
    
    # add topology
    for i, nd in enumerate(elem.iterfind('nd')):
        node_id = int(nd.get('ref'))
        if session.query(Node).filter(Node.id == node_id).first():
            session.add(Waypoint(way_id=way_id, idx=i, node_id=node_id))

    return True


def parse_osm(source, session, bbox, log):

    # way_type table
    for i, name in enumerate(walkable_types):
        session.add(WayType(id=i, name=name))

    session.commit()
    log.write('started parsing XML')

    # nodes and ways
    nodes_done = 0
    ways_done = 0

    for elem in parse_tags(source, ('node', 'way')):

        if elem.tag == 'node':
            x, y = elem.get('lon'), elem.get('lat')

            if not _inside_bbox(float(x), float(y), bbox):
                continue

            loc = 'POINT({} {})'.format(x, y)
            session.add(Node(id=int(elem.get('id')), loc=loc))
            nodes_done += 1

        elif elem.tag == 'way':
            if _maybe_add_way(elem, session):
                ways_done += 1

        if (nodes_done + ways_done) % 10000 == 0:
            log.write('{} nodes, {} ways'.format(nodes_done, ways_done))
            session.commit()

    session.commit()


if __name__ == '__main__':

    import sys
    from argparse import ArgumentParser
    from bz2 import BZ2File
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    parser = ArgumentParser()
    parser.add_argument('input', type=str, help='OSM XML file')
    parser.add_argument('url', type=str, help='database URL')

    parser.add_argument(
            '--bbox',
            type=lambda s: [float(c) for c in s.split(',')],
            default='-122.525,37.6936,-122.3499,37.8152',
            help='xmin,ymin,xmax,ymax')

    args = parser.parse_args()

    engine = create_engine(args.url)
    create_tables(engine)

    Session = sessionmaker(bind=engine)
    session = Session()

    parse_osm(args.input,
              session,
              args.bbox,
              Logger(sys.stdout))
