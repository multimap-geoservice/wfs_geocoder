# -*- coding: utf-8 -*-
# encoding: utf-8

import ogr
import json
import copy
import eventlet

owslib = eventlet.import_patched('owslib')

WebFeatureService = owslib.WebFeatureService
etree = owslib.etree

from gc_filters import WfsFilter


########################################################################
class GeoCoder(WfsFilter):
    """
    geocoder
    
    Default settings
    ----------------
    wfs_ver - 1.1.0 default!!!
    wfs_timeout = None/int sec - max timeout to response wfs server 
    out_geom - (Default - None - json)|gml|wkt
    """
    wfs_ver = '1.1.0'
    wfs_timeout = None
    out_geom = None
    

    #----------------------------------------------------------------------
    def __init__(self, url='http://localhost:3007', map_name='', debug=False):
        WfsFilter.__init__(self)
        if map_name:
            wfs_url = u"{0}/{1}".format(url, map_name)
        else:
            wfs_url = url
        self.debug = debug
        self.map_name_use = map_name
        self.green_pool = eventlet.GreenPool(200)
        
        wfs_args = {
            "url": wfs_url,
            "version": self.wfs_ver,
        }
        if isinstance(self.wfs_timeout, int):
            wfs_args["timeout"] = self.wfs_timeout
        try:
            self.wfs = WebFeatureService(**wfs_args)
        except Exception as err:
            raise Exception(
                u"WFS is not support in '{0}'\n{1}".format(
                    wfs_url, 
                    err
                )
            )
        else:
            self.capabilities = None
            self.get_capabilities()
            self.info = None
            self.get_info()
            self._set_def_resp_params()
        
    def _set_def_resp_params(self):
        self.epsg_code_cap = self.capabilities["epsg_code"]
        self.epsg_code_use = None
        self.layer_property_cap = self.capabilities["layer_property"]
        self.layer_property_use = None
        self.geom_property_cap = None
        self.response = []
        
    def echo2json(self, dict_):
        print json.dumps(
            dict_,
            sort_keys=True,
            indent=4,
            separators=(',', ': '), 
            ensure_ascii=False, 
        )
 
    def create_json_crs(self, crs_string):
        crs_string = crs_string.split(":")
        if len(crs_string) == 2:
            if crs_string[0].lower() == "epsg":
                return {
                    "type": "EPSG",
                    "properties": {
                            "code": crs_string[-1],
                        },
                    }
 
    def gml2json(self, gml):
        json_out = {
            "type": "FeatureCollection",
            "features": [],
        }
        geom_crs = None
        tree = etree.fromstring(gml)
        nsmap = tree.nsmap
        tag_name = lambda t: t.tag.split("{%s}" % nsmap[t.prefix])[-1]
        for feature in tree.getiterator("{%s}featureMember" % nsmap["gml"]):
            json_feature = {
                "type": "Feature",
                "properties": {},
                "geometry": None,
            }
            for layer in feature.iterfind('{%s}*' % nsmap["ms"]):
                json_feature["properties"]["layer"] = tag_name(layer)
                wfs_id = layer.get("{%s}id" % nsmap["gml"], None)
                if wfs_id and self.map_name_use:
                    wfs_id = u"{0}.{1}".format(
                        self.map_name_use, 
                        wfs_id
                    )
                json_feature["properties"]["id"] = wfs_id
                for prop in layer.iterfind('{%s}*' % nsmap["ms"]):
                    get_prop = True
                    for geom in prop.iterfind("{%s}*" % nsmap["gml"]):
                        get_prop = False
                        geom_crs = geom.get("srsName", None)
                        ogr_geom = ogr.CreateGeometryFromGML(etree.tostring(geom))
                        if isinstance(ogr_geom, ogr.Geometry):
                            json_feature["geometry"] = json.loads(
                                ogr_geom.ExportToJson()
                            )
                            if geom_crs:
                                json_feature["geometry"]["crs"] = self.create_json_crs(
                                    geom_crs
                                )
                            if self.out_geom:
                                ogr_geom = ogr.CreateGeometryFromJson(
                                    str(
                                        json.dumps(
                                            json_feature["geometry"], 
                                            ensure_ascii=False
                                        )
                                    )
                                )
                                if self.out_geom == "gml":
                                    json_feature["geometry"] = ogr_geom.ExportToGML()
                                elif self.out_geom == "wkt":
                                    json_feature["geometry"] = ogr_geom.ExportToWkt()
                                else:
                                    raise Exception(
                                        'out_geom="{} is not valid (None,gml,wkt)use"'.format(
                                            self.out_geom
                                        )
                                    )
                    if get_prop:
                        json_feature["properties"][tag_name(prop)] = prop.text
                json_out["features"].append(json_feature)
        if geom_crs:
            json_out["crs"] = self.create_json_crs(geom_crs)
        if self.debug:
            self.echo2json(json_out)
        return json_out
   
    def get_help(self):
        filter_tags = {
            my: self.filter_tags[my]()
            for my
            in self.filter_tags
        }
        comparsion_opts = {
            my: self.filter_opts[my]()
            for my
            in self.filter_opts
            if not isinstance(self.filter_opts[my](), dict)
        }
        spatial_opts = {
            my: self.filter_opts[my]()
            for my
            in self.filter_opts
            if isinstance(self.filter_opts[my](),dict)
        }
        json_out = {
            "filter":{
                "tags": filter_tags,
                "comparsion opts": comparsion_opts,
                "spatial opts": spatial_opts,
                "example": {
                    "tag": [
                        {
                            "tag": {
                                "property 1": {
                                    "comparsion opt": "value",
                                },
                                "property 2": {
                                    "comparsion opt 1": "value",
                                    "comparsion opt 2": ["value 1", "value 2"],
                                    "spatial opt": {
                                        "spatial opt key 1": "value", 
                                        "spatial opt key 2": "value",
                                    },
                                },
                            }, 
                        },
                        {
                            "any key": {
                                "spatial opt": {
                                    "spatial opt key 1": "value", 
                                    "spatial opt key 2": "value",
                                },
                            },
                        }, 
                    ],
                },
            }, 
        }
        if self.debug:
            self.echo2json(json_out)
        return json_out
    
    def get_info(self):
        if self.info is None:
            json_out = {}
            for layer_name in self.wfs.contents:
                if self.wfs.contents[layer_name].metadataUrls:
                    wfs_opts = self.wfs.contents[layer_name].metadataUrls[0]
                    wfs_opts["gml"] = self.wfs.contents[layer_name].outputFormats[0]
                else:
                    wfs_opts = None
                json_out[layer_name] = {
                    "wgs84_bbox": list(self.wfs.contents[layer_name].boundingBoxWGS84),
                    "wfs_opts": wfs_opts, 
                }
            if self.debug:
                self.echo2json(json_out)
            self.info = json_out
        return self.info
    
    def get_capabilities(self):
        if self.capabilities is None:
            json_out = {
                "max_features": None,
                "filter": None,
                "layers": {},
            }
            all_epsg_code = None
            all_layer_property = None
            all_geom_property = None
            for layer_name in self.wfs.contents:
                layer_schema = self.wfs.get_schema(layer_name)
                if layer_schema:
                    geom_property = layer_schema['geometry_column']
                    layer_property = []
                    layer_property.append(geom_property)
                    layer_property += layer_schema['properties'].keys()
                    epsg_code = [
                        my.code 
                        for my 
                        in self.wfs.contents[layer_name].crsOptions
                    ]
                    json_out['layers'][layer_name] = {
                        "epsg_code": epsg_code, 
                        "layer_property": layer_property,
                        "geom_property": geom_property,
                        "max_features": None,
                        "filter": None,
                    }

                    if all_layer_property is None:
                        all_layer_property = layer_property
                    else:
                        all_layer_property = list(
                            set(all_layer_property).intersection(set(layer_property))
                        )

                    if all_geom_property is None:
                        all_geom_property = geom_property
                    elif all_geom_property is not False:
                        if all_geom_property != geom_property:
                            all_geom_property = False

                    if all_epsg_code is None:
                        all_epsg_code = epsg_code
                    else:
                        all_epsg_code = list(
                            set(all_epsg_code).intersection(set(epsg_code))
                        )
            json_out.update({
                "epsg_code": all_epsg_code,
                "layer_property": all_layer_property,
                "geom_property": all_geom_property,
            })
            if self.debug:
                self.echo2json(json_out)
            self.capabilities = json_out
        return self.capabilities

    def get_feature_eventlet(self, com_opts):
        """
        kwargs (for eventlet imap) - keys:
            layer_name
            filter_json
            every ....
        """
        if not isinstance(com_opts, dict):
            return
        layer_name = com_opts.get("layer_name", None)
        if layer_name:
            del com_opts['layer_name']
        else:
            return

        if com_opts.has_key("filter_json"):
            filter_json = com_opts["filter_json"]
            del com_opts['filter_json']
        else:
            filter_json = None
            
        return self.get_feature(layer_name, filter_json, **com_opts)
       
    
    def get_feature(self, layer_name, filter_json=None, **kwargs):
        feature_args = [
            "propertyname", 
            "maxfeatures", 
            "srsname"
        ]
        out_args = {
            "typename": layer_name,
        }
        if isinstance(filter_json, dict):
            out_args["filter"] = self.filter_engine(filter_json)

        for arg in feature_args:
            if kwargs.get(arg, None):
                out_args[arg] = kwargs[arg]
        
        return self.gml2json(
            self.wfs.getfeature(**out_args).read()
        )
    
    def merge_gjson(self, gjson):
        if not isinstance(self.response, list) or not isinstance(gjson, dict):
            return
        elif not gjson['features']:
            return
        elif not self.response:
            self.response = [gjson]
        else:
            gj = {}
            gj_test_fea = copy.deepcopy(gjson['features'][0])
            gj['props'] = set(gj_test_fea['properties'].keys())
            if isinstance(gj_test_fea['geometry'], dict):
                gj['crs'] = copy.deepcopy(gjson['crs'])
                gj['geom'] = gj_test_fea['geometry']['type']
            else:
                gj['crs'] = None
                gj['geom'] = None
            merge = False
            for lst_element in self.response:
                if isinstance(lst_element, dict):
                    lst = {}
                    lst_test_fea = copy.deepcopy(lst_element['features'][0])
                    lst['props'] = set(lst_test_fea['properties'].keys())
                    if isinstance(lst_test_fea['geometry'], dict):
                        lst['crs'] = copy.deepcopy(lst_element['crs'])
                        lst['geom'] = lst_test_fea['geometry']['type']
                    else:
                        lst['crs'] = None
                        lst['geom'] = None
                    if gj == lst:
                        index = self.response.index(lst_element)
                        self.response[index]['features'].extend(gjson['features'])
                        merge = True
                        break
            if not merge:
                self.response.append(gjson)
    
    def get_response(self, request_):
        def_com_opts = {
            "layer_name": [u"{}", "layer"],
            "filter_json": [{}, "filter"],
            "propertyname": [[], "layer_property"],
            "maxfeatures": [u"{}", "max_features"],
            "srsname": [u"EPSG:{}", "epsg_code"],
        }
        self._set_def_resp_params()  # start response
        capabilities = copy.deepcopy(self.capabilities)
        cap_layers = {my:{} for my in capabilities["layers"]}
        req_layers = {
            my:request_.get("layers", cap_layers)[my] 
            for my 
            in request_.get("layers", cap_layers)
            if cap_layers.has_key(my)
        }
        req_opts = copy.deepcopy(request_)
        if req_opts.has_key("layers"):
            del(req_opts["layers"])
        
        all_opts = []
        for layer in req_layers:
            capabilities['layers'][layer]["layer"] = None
            layer_opts = {"layer": layer}
            layer_opts.update(req_opts)
            if isinstance(req_layers[layer], dict):
                layer_opts.update(req_layers[layer])
            com_opts = copy.deepcopy(def_com_opts)
            for opt in com_opts:
                cap_param = capabilities['layers'][layer][def_com_opts[opt][1]]
                param = layer_opts.get(com_opts[opt][1], None)
                if cap_param:
                    # test param from capabilites
                    cap_param = [self.data2literal(my) for my in cap_param]
                    if isinstance(param, list):
                        param = [self.data2literal(my) for my in param]
                        param = list(set(param).intersection(set(cap_param)))
                    elif isinstance(param, (str, unicode, int, float)):
                        param = self.data2literal(param)
                        if param not in cap_param:
                            param = None
                if param:
                    if isinstance(com_opts[opt][0], unicode):
                        if isinstance(param, (str, unicode, int, float)):
                            com_opts[opt] = com_opts[opt][0].format(param)
                    elif isinstance(com_opts[opt][0], (dict)):
                        if isinstance(param, dict):
                            com_opts[opt] = copy.deepcopy(param)
                    elif isinstance(com_opts[opt][0], list):
                        if isinstance(param, list):
                            com_opts[opt] = copy.deepcopy(param)
                    else:
                        com_opts[opt] = None
                else:
                    com_opts[opt] = None
            # data for use in filter
            self.epsg_code_cap = capabilities["layers"][layer]["epsg_code"]
            self.epsg_code_use = layer_opts.get(
                "epsg_code", 
                capabilities["layers"][layer]["epsg_code"][0]
            )
            self.layer_property_cap = capabilities["layers"][layer]["layer_property"]
            self.geom_property_cap = capabilities["layers"][layer]["geom_property"]
            self.layer_property_use = layer_opts.get(
                "layer_property", 
                capabilities["layers"][layer]["layer_property"]
            )
            all_opts.append(com_opts)
            #self.merge_gjson(
                #self.get_feature(**com_opts)
            #)
            
        #return gjson & merge
        for green_out in self.green_pool.imap(self.get_feature_eventlet, all_opts):
            self.merge_gjson(green_out)
        
        resp_out = copy.deepcopy(self.response)
        self._set_def_resp_params()  # end response
        if len(resp_out) == 0:
            return {}
        elif len(resp_out) == 1:
            return resp_out[0]
        else:
            return resp_out
        
    def get_properties(self):
        disable_prop = [
            "layer", 
            "id", 
            "osm_id"
        ]
        out = {}
        layers = self.capabilities["layers"].keys()
        for layer in layers:
            out[layer] = {}
            req = {
                "layers": {
                    layer: None,
                    },
            }
            resp = self.get_response(req)
            prop_list = resp["features"][0]["properties"].keys()
            for prop in prop_list:
                if prop not in disable_prop:
                    out[layer][prop] = list(set([
                        my["properties"][prop]
                        for
                        my
                        in
                        resp["features"]
                    ]))
        return out
        
    def __call__(self, *args, **kwargs):
        return self.get_response(*args, **kwargs)