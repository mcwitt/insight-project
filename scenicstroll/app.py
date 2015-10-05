from flask import Flask

import numpy as np
from forms import InputForm
from flask import flash, render_template, request, redirect, url_for

import folium
from geopy.geocoders import GoogleV3

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from photo_db import Photo

from shapely import wkb

from route_db import RouteDB, Node, Waypoint
from route_graph import RoutingGraph

from collections import defaultdict

app = Flask(__name__)
app.config.from_object('config')

colors = [
    "#7fc97f",
    "#beaed4",
    "#fdc086",
    "#ffff99",
    "#386cb0",
    "#f0027f",
    "#bf5b17",
    "#666666",
]

geolocator = GoogleV3()

engine = create_engine('postgresql://scenic@localhost/photodb')
Session = sessionmaker(bind=engine)
session = Session()

engine = create_engine('postgresql://scenic@localhost/scenicstroll2')
Session = sessionmaker(bind=engine)
db = RouteDB(Session())


def ll2wkt(lat, lon):
    return 'POINT({} {})'.format(lon, lat)


def wkb2ll(b):
    loc = wkb.loads(b)
    return loc.x, loc.y



@app.route('/', methods=['GET','POST'])
@app.route('/index', methods=['GET','POST'])
def index():
    form = InputForm(request.form)

    if request.method == 'POST' and form.validate():
        return redirect(url_for('output',
                        address1=form.address1.data,
                        address2=form.address2.data,
                        alpha=form.alpha.data))

    return render_template("index.html", map_name='map-init.html', form=form)


#conversion = dict(mi=1609.34, km=1000)

@app.route('/output', methods=['GET','POST'])
def output():

    form = InputForm(request.form)
    address1 = request.args.get('address1')
    address2 = request.args.get('address2')
    alpha = float(request.args.get('alpha'))

    loc1 = geolocator.geocode(address1)
    loc2 = geolocator.geocode(address2)

    for loc, address in ((loc1, address1), (loc2, address2)):
        if not loc:
            flash("Sorry, I don't recognize '{}'. Try something else?"
                  .format(address))
            return redirect(url_for('index'))

    latlon1 = np.array([loc1.latitude, loc1.longitude])
    latlon2 = np.array([loc2.latitude, loc2.longitude])

    latlon_center = 0.5*(latlon1 + latlon2)

    bmap = folium.Map(
        location=tuple(latlon_center),
        zoom_start=12
    )

    bmap.simple_marker(location=latlon1)
    bmap.simple_marker(location=latlon2)

    point1 = ll2wkt(*latlon1)
    point2 = ll2wkt(*latlon2)

    query = session.query(Photo)

    for photo in query:
        color = colors[photo.label % len(colors)]
        bmap.circle_marker(
            location=wkb2ll(bytes(photo.location.data)),
            popup='<img src={url} width=200 height=200>'.format(url=photo.url),
            fill_color=color,
            line_color=color,
            radius=20
        )

    ####################
    # find optimal route

    node1 = db.nearest_xnodes(loc1.latitude, loc1.longitude, 500).first()
    node2 = db.nearest_xnodes(loc2.latitude, loc2.longitude, 500).first()

    for node, address in ((node1, address1), (node2, address2)):
        if not node:
            flash("Sorry, I don't have data near {} yet. Try something else?"
                  .format(address))
            return redirect(url_for('index'))

    waypoints = defaultdict(list)

    for wp in db.get_waypoints(node1, node2):
        waypoints[wp.way_id].append(wp)

    G = RoutingGraph()

    for way_id, wps in waypoints.items():
        G.add_way(wps)

    G.reweight(alpha)

    try:
        nodes, edges = G.get_optimal_path(node1.id, node2.id)
    except: # TODO: exception?
        flash("Sorry, I couldn't find a route. Try something else?")
        return redirect(url_for('index'))

    for edge in edges:
        nodes = (
            db.session.query(Node.loc)
            .join(Waypoint)
            .filter((Waypoint.way_id == edge['way_id']) &
                    (Waypoint.idx >= edge['i']) &
                    (Waypoint.idx <= edge['j'])))
        
        xy = []
        for node in nodes:
            loc = wkb.loads(bytes(node.loc.data))
            xy.append((loc.y, loc.x))
            
        bmap.line(xy)
        
    map_name = 'map-output.html'
    map_path = 'templates/{}'.format(map_name)
    bmap.create_map(path=map_path)

    return render_template(
        'index.html',
        map_name=map_name,
        form=form,
        address1=address1,
        address2=address2,
        alpha=alpha)


if __name__ == '__main__':
    app.run()
