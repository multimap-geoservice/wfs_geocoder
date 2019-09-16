# -*- coding: utf-8 -*-
# encoding: utf-8

from wfs_geocoder import GeoCoderWSGI


if __name__ == "__main__":
    gc = GeoCoderWSGI
    #gc.out_geom = "gml"
    #gc.out_geom = "wkt"
    wsgi = gc(
        port=3008, 
        host='0.0.0.0', 
        url='http://localhost:3007', 
        debug=True, 
    )
    wsgi()