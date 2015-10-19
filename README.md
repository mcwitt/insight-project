# [ScenicStroll](http://www.scenicstroll.xyz)

ScenicStroll is a web app that finds scenic routes between two locations based
on the density of geotagged photos from Flickr. The scenery model uses a kernel
density estimate to create a probability map of photo locations. Optimal routes
are then found by a graph search on OpenStreetMap road data where the graph
edge weights are determined from a combination of distance and scenery score,
where the relative weight of the two metrics is controlled by the user.


## Database generation

The backend uses PostgreSQL with PostGIS extensions for geospatial queries.
To build the database, first download OpenStreetMap XML data, e.g. from
[Mapzen](https://mapzen.com/data/metro-extracts/).
Next, create a new database and enable PostGIS extensions:
```
psql> CREATE DATABASE scenicstroll;
psql> \connect scenicstroll
psql> CREATE EXTENSION postgis;
```
Finally, generate the routing database by running, e.g.
```
python parse_osm.py san-francisco-bay_california.osm postgres:///scenicstroll
psql -c prep_routes.sql
```

Computation of scenery scores is handled by `notebooks/scenery_score.ipynb`.


## Web server setup

To install the dependencies for the web server:
```
pip install $(cat requirements.txt)
```

Then start the server with
```
python app.py
```
