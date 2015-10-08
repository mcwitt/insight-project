import folium
import numpy as np
from flask import Flask
from forms import InputForm
from flask import flash, render_template, request, redirect, url_for
from geopy.geocoders import GoogleV3
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from photo_db import Photo, PhotoCluster
from route_db import RouteDB, Node, Waypoint
from route_graph import RoutingGraph
from shapely import wkb


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

#conversion = dict(mi=1609.34, km=1000)

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

    latlons = tuple(np.array([loc.latitude, loc.longitude]) for loc in locs)
    latlon_center = 0.5*(latlons[0] + latlons[1])

    bmap = folium.Map(
        location=tuple(latlon_center),
        zoom_start=12
    )

    bmap.simple_marker(location=latlons[0])
    bmap.simple_marker(location=latlons[1])

    for cluster in session.query(PhotoCluster):
        loc = wkb.loads(bytes(cluster.centroid.data))

        most_viewed_url = (
            session.query(Photo.url)
                   .filter(Photo.id == cluster.most_viewed)
                   .first())[0]

        bmap.circle_marker(
            location=(loc.y, loc.x),
            popup='<img src={url} width=200>'.format(url=most_viewed_url),
            fill_color='red',
            line_color='red',
            radius=5*np.sqrt(cluster.num_photos)
        )


    # find optimal route

    nodes = tuple(db.get_nearest_xnodes(loc.latitude, loc.longitude, 500).first()
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
    flash('Found a {:.1f} mile walk.'.format(dist/1609.34))

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
        address1=addresses[0],
        address2=addresses[1],
        alpha=alpha)


if __name__ == '__main__':
    app.run()
