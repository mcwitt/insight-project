from datetime import datetime
from routedb import RouteDB, Node, WayType, Way, WayNode
from sqlalchemy import not_
from time import time
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
    
    if way_type is None:    # no `highway` tag; ignore
        return
    
    way_id = int(elem.get('id'))
    way = Way(id=way_id, name=name, way_type_id=type_id[way_type])
    session.add(way)
    session.commit()
    
    # add topology
    for i, nd in enumerate(elem.iterfind('nd')):
        session.add(WayNode(way_id=way_id,
                            idx=i,
                            node_id=int(nd.get('ref')),
                            dist=float('NaN'),
                            cdist=float('NaN'),
                            score=float('NaN'),
                            cscore=float('NaN')))


def parse_osm(source, session, log, prune_unused=False):

    # way_type table
    for i, name in enumerate(walkable_types):
        session.add(WayType(id=i, name=name))

    session.commit()

    # nodes and ways
    nodes_done = 0
    ways_done = 0

    log.write('started parsing XML')

    for i, elem in enumerate(parse_tags(source, ('node', 'way')), 1):

        if elem.tag == 'node':

            x, y = (elem.get(_) for _ in ('lon', 'lat'))

            session.add(Node(id=int(elem.get('id')),
                        loc='POINT({} {})'.format(x, y)))

            nodes_done += 1

        elif elem.tag == 'way':
            _maybe_add_way(elem, session)
            ways_done += 1

        if i % 10000 == 0:
            log.write('{} nodes, {} ways'.format(nodes_done, ways_done))
            session.commit()

    session.commit()

    if prune_unused:
        log.write('pruning unused nodes...')
        unused_nodes = session.query(Node).filter(not_(Node.ways.any()))
        unused_nodes.delete(synchronize_session=False)
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
    parser.add_argument('--prune', action='store_true', help='prune unused nodes')
    args = parser.parse_args()

    db = RouteDB(args.url)
    db.create_tables()

    #with BZ2File(args.input) as f:
    #    parse_osm(f, session)

    log = Logger(sys.stdout)
    parse_osm(args.input, db.session, log, prune_unused=args.prune)
