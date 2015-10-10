import folium
import numpy as np
from flask import Flask
from forms import InputForm
from flask import flash, render_template, request, redirect, url_for
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


@app.route('/', methods=['GET','POST'])
@app.route('/index', methods=['GET','POST'])
def index():
    form = InputForm(request.form)

    if request.method == 'POST' and form.validate():
        return redirect(url_for('route',
                        address1=form.address1.data,
                        address2=form.address2.data,
                        alpha=form.alpha.data))

    return render_template("index.html", map_name='map-init.html', form=form)

@app.route('/route', methods=['GET','POST'])
def route():
    form = InputForm(request.form)
    addresses = tuple(request.args.get(_) for _ in ('address1', 'address2'))
    alpha = float(request.args.get('alpha'))
    locs = tuple(geolocator.geocode(address) for address in addresses)

    for loc, address in zip(locs, addresses):
        if not loc:
            flash("Sorry, I don't recognize '{}'. Try something else?"
                  .format(address))
            return redirect(url_for('index'))


    # find optimal route

    nodes = tuple(db.get_nearest_xnodes(
                    loc.latitude,
                    loc.longitude,
                    app.config['SEARCH_RADIUS']).first()
                  for loc in locs)

    for node, address in zip(nodes, addresses):
        if not node:
            flash("Sorry, I don't have data near {} yet. Try something else?"
                  .format(address))
            return redirect(url_for('index'))

    waypoints = db.get_relevant_waypoints(nodes[0], nodes[1])
    G = RoutingGraph(waypoints, alpha)

    try:
        nodes, edges = G.get_optimal_path(nodes[0].id, nodes[1].id)
    except:
        flash("Sorry, I couldn't find a route. Try something else?")
        return redirect(url_for('index'))

    dist = sum(edge['dist'] for edge in edges)
    miles = dist/1609.34
    aan = 'a' if str(miles)[0] in '012345679' else 'an'
    flash('Found {} {:.1f} mile walk.'.format(aan, miles))


    # create map

    latlons = tuple(np.array([loc.latitude, loc.longitude]) for loc in locs)
    latlon_center = 0.5*(latlons[0] + latlons[1])

    bmap = folium.Map(
        location=tuple(latlon_center),
        zoom_start=12
    )

    bmap.simple_marker(location=latlons[0])
    bmap.simple_marker(location=latlons[1])
    nearby_labels = set()

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
                (Waypoint.idx <= edge['idx2'])))
        
        yx = []

        for node, x, y in nodes:

            yx.append((y, x))
            geog = cast(node.loc, Geography)

            nearby_labels_query = (
                session.query(PhotoCluster.label)
                .filter(PhotoCluster.centroid.ST_DWithin(
                        geog, app.config['SIGHT_DISTANCE'])))

            nearby_labels.update(label for (label,) in nearby_labels_query)

        bmap.line(yx)

    nearby_clusters = (
        session.query(
            PhotoCluster,
            ST_X(cast(PhotoCluster.centroid, Geometry)),
            ST_Y(cast(PhotoCluster.centroid, Geometry)))
        .filter(PhotoCluster.label.in_(nearby_labels)))

    for cluster, x, y in nearby_clusters:

        most_viewed_url = (
            session.query(Photo.url)
            .filter(Photo.id == cluster.most_viewed)
            .first())[0]

        bmap.circle_marker(
            location=(y, x),
            popup='<img src={url} width={width}>'.format(
                url=most_viewed_url,
                width=app.config['IMAGE_WIDTH']),
            fill_color='red',
            line_color='red',
            radius=5*np.sqrt(cluster.num_photos)
        )
        

    # mark photo clusters

    map_name = 'map-output.html'
    map_path = 'templates/{}'.format(map_name)
    bmap.create_map(path=map_path)

    return render_template(
        'index.html',
        map_name=map_name,
        form=form,
        address1=addresses[0],
        address2=addresses[1],
        alpha=alpha)


if __name__ == '__main__':
    app.run()
