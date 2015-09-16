import config
import numpy as np
from .forms import InputForm
from app import app
from flask import render_template, request, redirect, url_for

import folium
from geopy.distance import EARTH_RADIUS
from geopy.geocoders import Nominatim

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from photodb import Photo

from shapely import wkb

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

geolocator = Nominatim()

engine = create_engine('postgresql://:app@localhost/app')
Session = sessionmaker(bind=engine)
session = Session()


@app.route('/', methods=['GET','POST'])
@app.route('/index', methods=['GET','POST'])
def input():
    form = InputForm(request.form)

    if request.method == 'POST' and form.validate():
        return redirect(url_for('output',
                        address=form.address.data,
                        distance=form.distance.data,
                        units=form.units.data))

    return render_template("input.html", form=form)


conversion = dict(mi=1609.34, km=1000)

@app.route('/output', methods=['GET'])
def output():
    address = request.args.get('address')
    distance = float(request.args.get('distance'))
    units = request.args.get('units')

    distance_meters = conversion[units]*distance

    loc = geolocator.geocode(address)
    loc = (loc.latitude, loc.longitude)

    bmap = folium.Map(
        location=loc,
        zoom_start=14,
    )

    bmap.simple_marker(location=loc)

    bmap.circle_marker(
        location=loc,
        radius=distance_meters,
        fill_color=colors[0],
        line_color=colors[0],
        fill_opacity=0.2
    )

    query = session.query(Photo).filter(
        Photo.location.ST_Distance(
            'POINT({lat} {lon})'.format(
                lat=loc[0],
                lon=loc[1],
            )
        ) < (180/np.pi)*1e-3*distance_meters/EARTH_RADIUS
    )

    for photo in query:

        color = colors[photo.label % len(colors)]
        photo_loc = wkb.loads(bytes(photo.location.data))

        bmap.circle_marker(
            location=[photo_loc.x, photo_loc.y],
            popup='<img src={url} width=200 height=200>'.format(url=photo.url),
            fill_color=color,
            line_color=color,
            radius=20,
        )

    map_name = 'map.html'
    map_path = '{}/templates/{}'.format(config.base_url, map_name)
    bmap.create_map(path=map_path)

    return render_template("output.html", map_name=map_name)
