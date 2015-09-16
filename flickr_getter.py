import csv
from flickrapi import FlickrAPI
from datetime import date, timedelta
from time import sleep
from credentials.flickr import api_key, api_secret

output_name = "photometa{n:02d}.csv"
start_date = date(2014,9,12)
end_date = date(2015,9,12)
lat, lon = 37.7577, -122.4376 # SF
radius = 20 # km

api = FlickrAPI(api_key, api_secret)

extras_to_get = ','.join([
    'description',
    'license',
    'date_upload',
    'date_taken',
    'owner_name',
    'original_format',
    'geo',
    'tags',
    'machine_tags',
    'o_dims',
    'views',
    'media',
    'url_o',
    'url_n',
])

search_args = dict(
    has_geo=1, # only geotagged
    privacy_filter=1, # public
    safe_search=1, # safe
    content_type=1, # photos only
    media='photos',
    extras=extras_to_get,
    lat=lat,
    lon=lon,
    radius=radius, # km
    per_page=500,
)

converters = [
    ("id", str),
    ("owner", str),
    ("secret", str),
    #("server", int),
    #("farm", int),
    ("title", str),
    ('description', str),
    #("ispublic", bool),
    #("isfriend", bool),
    #("isfamily", bool),
    ("license", int),
    ("dateupload", str),
    ("datetaken", str),
    #("datetakengranularity", int),
    #("datetakenunknown", int),
    ("ownername", str),
    ("views", int),
    ("tags", str), # split on space
    ("machine_tags", str), # split on space
    #("originalsecret", str),
    #("originalformat", str),
    ("latitude", float),
    ("longitude", float),
    ("accuracy", int),
    ("context", int),
    ("place_id", str),
    ("woeid", str),
    #("geo_is_family", bool),
    #("geo_is_friend", bool),
    #("geo_is_contact", bool),
    #("geo_is_public", bool),
    ("media", str),
    ("media_status", str),
    ("url_o", str), # preview
    ("url_n", str), # full size
] 


def convert_values(elem):
    return tuple(converter(elem.get(key)) for key, converter in converters)


def iter_days(start_date, end_date):
    cur_date = start_date
    while cur_date < end_date:
        yield cur_date, cur_date + timedelta(days=1)
        cur_date += timedelta(days=1)


def get_size(elem):

    h0 = elem.get("o_height")
    h1 = elem.get("height_o")
    w0 = elem.get("o_width")
    w1 = elem.get("width_o")

    if h0:
        h = int(h0)
    elif h1:
        h = int(h1)
    else:
        h = None

    if w0:
        w = int(w0)
    elif w1:
        w = int(w1)
    else:
        w = None

    return w, h


if __name__ == '__main__':

    import os, sys

    # don't overwrite existing output files (increment suffix)
    n = 0
    while os.path.isfile(output_name.format(n=n)):
        n += 1

    with open(output_name.format(n=n), 'w') as output_file:

        csv_writer = csv.writer(output_file)
        csv_writer.writerow(list(zip(*converters))[0] + ('width','height'))

        # Flickr API limits the number of unique photos returned per search
        # query. Solution here is to iterate over days in the date range and
        # make a separate query for each.
        # (see http://stackoverflow.com/questions/1994037/flickr-api-returning-duplicate-photos)
        for min_date, max_date in iter_days(start_date, end_date):

            print("{start} to {end}: ".format(
                    start=min_date,
                    end=max_date,
                ),
                end=""
            )

            success = False

            while not success:
                sleep(2)
                try:
                
                    # iterator over search results
                    walker = api.walk(
                        min_taken_date=min_date,
                        max_taken_date=max_date,
                        **search_args
                    )

                    # collect results
                    data = [convert_values(elem) + get_size(elem)
                            for elem in walker]

                except KeyboardInterrupt as e:
                    raise KeyboardInterrupt(e)
                except:
                    sys.stderr.write("failed, trying again...\n")
                else:
                    success = True
                    csv_writer.writerows(data)
                    print("fetched {n} photos".format(n=len(data)))
