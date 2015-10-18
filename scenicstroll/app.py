from flask import Flask, jsonify
from forms import InputForm
from flask import render_template, request, redirect, url_for
from geoalchemy2 import Geography, Geometry
from geoalchemy2.functions import ST_X, ST_Y
from geopy.geocoders import GoogleV3
from sqlalchemy import cast, create_engine
from sqlalchemy.orm import sessionmaker
from photo_db import Photo, PhotoCluster
from route_db import RouteDB, Node, Waypoint
from route_graph import RoutingGraph


app = Flask(__name__)
app.config.from_object('config')
geolocator = GoogleV3()

# connect database
engine = create_engine(app.config['DATABASE'])
Session = sessionmaker(bind=engine)
session = Session()
db = RouteDB(session)

@app.route('/')
@app.route('/index')
def index():
    form = InputForm(request.form)
    return render_template('index.html',
                           form=form,
                           center_latlon='37.7577,-122.4376',
                           zoom=12)


@app.route('/query', methods=['POST'])
def query():

    form = InputForm(request.form)
    if not form.validate():
        return jsonify(success=False, message='Invalid input.')

    addresses = [form.address1.data, form.address2.data]
    locs = tuple(geolocator.geocode(address) for address in addresses)
    alpha = float(form.alpha.data)

    for loc, address in zip(locs, addresses):
        if not loc:
            msg = "Sorry, I don't recognize '{}'. Try something else?"
            return jsonify(success=False, message=msg.format(address))

    nodes = tuple(db.get_nearest_xnodes(
                    loc.latitude,
                    loc.longitude,
                    app.config['SEARCH_RADIUS']).first()
                  for loc in locs)

    for node, address in zip(nodes, addresses):
        if not node:
            msg = "Sorry, I don't have data near {} yet. Try something else?"
            return jsonify(success=False, message=msg.format(address))

    try:
        path, dist = get_optimal_path(nodes[0], nodes[1], alpha)
    except:
        msg = "Sorry, I couldn't find a route. Try something else?"
        return jsonify(success=False, message=msg)

    latlngs = [(lat, lng) for _, lat, lng in path]
    clusters = get_nearby_clusters(path)

    dist_mi = dist/1609.34
    aan = 'a' if str(dist_mi)[0] in '012345679' else 'an'
    msg = 'Found {} {:.1f}-mile walk.'.format(aan, dist_mi)

    return jsonify(success=True,
                   message=msg,
                   latlngs=latlngs,
                   dist=dist,
                   clusters=clusters)


def get_optimal_path(node1, node2, alpha):

    # build road graph
    waypoints = db.get_relevant_waypoints(node1, node2)
    rg = RoutingGraph(waypoints, alpha)
    _, edges = rg.get_optimal_path(node1.id, node2.id)
    dist = sum(edge['dist'] for edge in edges)
    path = []


    # get detailed path information for each edge
    for edge in edges:
        nodes = (
            db.session.query(
                Node,
                ST_X(cast(Node.loc, Geometry)),
                ST_Y(cast(Node.loc, Geometry)))
            .join(Waypoint)
            .filter(
                (Waypoint.way_id == edge['way_id']) &
                (Waypoint.idx >= edge['idx1']) &
                (Waypoint.idx <= edge['idx2']))
            .order_by(Waypoint.idx).all())

        if edge['reversed']:
            nodes = nodes[::-1]

        path.extend((node.id, y, x) for node, x, y in nodes)

    return path, dist


def get_nearby_clusters(path):

    node_ids = set(r[0] for r in path)
    nodes_query = db.session.query(Node.loc).filter(Node.id.in_(node_ids))

    # find set of clusters near nodes in the path
    nearby_clusters = set([])

    for node in nodes_query:

        nearby_clusters_query = (
            session.query(PhotoCluster.label)
            .filter(PhotoCluster.centroid.ST_DWithin(
                    cast(node.loc, Geography), app.config['SIGHT_DISTANCE'])))

        nearby_clusters.update(label for (label,) in nearby_clusters_query)

    # get info for nearby clusters
    clusters_query = (
        session.query(
            PhotoCluster,
            ST_X(cast(PhotoCluster.centroid, Geometry)),
            ST_Y(cast(PhotoCluster.centroid, Geometry)))
        .filter(PhotoCluster.label.in_(nearby_clusters)))

    # construct the response
    clusters = []
    for cluster, x, y in clusters_query:

        most_viewed_url = (
            session.query(Photo.url)
            .filter(Photo.id == cluster.most_viewed)
            .first())[0]

        clusters.append({
            'location': (y, x),
            'size': cluster.num_photos,
            'repr_url': most_viewed_url,
        })

    return clusters


if __name__ == '__main__':
    app.run()
