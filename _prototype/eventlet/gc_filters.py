# -*- coding: utf-8 -*-
# encoding: utf-8

import ogr
import osr
import json
import copy
import eventlet

owslib = eventlet.import_patched('owslib')
etree = owslib.etree
PropertyIsBetween = owslib.PropertyIsBetween  # между
PropertyIsEqualTo = owslib.PropertyIsEqualTo  # =
PropertyIsGreaterThan = owslib.PropertyIsGreaterThan  # >
PropertyIsGreaterThanOrEqualTo = owslib.PropertyIsGreaterThanOrEqualTo  # >=
PropertyIsLessThan = owslib.PropertyIsLessThan  # <
PropertyIsLessThanOrEqualTo = owslib.PropertyIsLessThanOrEqualTo  # <=
PropertyIsLike = owslib.PropertyIsLike  #как  * . ! 
PropertyIsNotEqualTo = owslib.PropertyIsNotEqualTo  # !=
PropertyIsNull = owslib.PropertyIsNull  # =NULL
BBox = owslib.BBox


########################################################################
class WfsFilter(object):
    """
    create filter for wfs
    """

    #----------------------------------------------------------------------
    def __init__(self):
        """Constructor"""
        self.epsg_code_cap = None
        self.epsg_code_use = None
        self.layer_property_cap = None
        self.layer_property_use = None
        self.geom_property_cap = None
        self.filter_tags = {
            "and": self.filter_tag_and,
            "or": self.filter_tag_or,
            "not": self.filter_tag_not,
            "filter": self.filter_tag_filter,
        } 
        self.filter_opts = {
            "=": self.filter_comp_equal_to,
            "!=": self.filter_comp_not_equal_to,
            ">": self.filter_comp_greater_than,
            ">=": self.filter_comp_graater_than_or_equal_to,
            "<": self.filter_comp_less_than,
            "<=": self.filter_comp_less_than_or_equal_to,
            "between": self.filter_comp_beetwen,
            "null": self.filter_comp_null,
            "like": self.filter_comp_like,
            "bbox": self.filter_spat_bbox,
            "buffer": self.filter_spat_buffer,
        }
        
    def filter_engine(self, content, bool_tag=True, filter_tag=True):
        all_filter = u""
        for key in content:
            cont_key = copy.deepcopy(content[key])
            if self.filter_tags.has_key(key):
                if isinstance(cont_key, dict):
                    cont = self.filter_engine(
                                cont_key, 
                                bool_tag=False, 
                                filter_tag=False
                            )
                    all_filter = "{0}{1}".format(
                        all_filter,
                        self.filter_tags[key](cont)
                    )
                elif isinstance(cont_key, list):
                    cont_arr = []
                    for cont_next in cont_key:
                        cont_arr.append(
                            self.filter_engine(
                                cont_next, 
                                bool_tag=True, 
                                filter_tag=False
                            )
                        )
                    all_filter = "{0}{1}".format(
                        all_filter,
                        self.filter_tags[key](*cont_arr)
                    )
            else:
                for f_opt in cont_key:
                    if self.filter_opts.has_key(f_opt):
                        f_arg = cont_key[f_opt]
                        if not f_arg:
                            f_kwarg = {}
                            f_arg = []
                        elif isinstance(f_arg, dict):
                            f_kwarg = copy.deepcopy(f_arg)
                            f_arg = []
                        elif isinstance(f_arg, list):
                            f_kwarg = {}
                        else:
                            f_kwarg = {}
                            f_arg = [f_arg] 
                        f_arg.insert(0, key)
                        all_filter = "{0}{1}".format(
                            all_filter, 
                            self.filter_opts[f_opt](*f_arg, **f_kwarg)
                        )
                    else:
                        raise Exception(
                            "Error: filter option '{}' not found".format(f_opt)
                        )
        if bool_tag:
            condit_0 = []
            condit_0.append(len(content) != 1)
            condit_1 = []
            condit_1.append(len(content) == 1)
            condit_1.append(len(content.values()[0]) != 1)
            condit_1.append(content.keys()[0] not in self.filter_tags.keys())
            condit_0.append(False not in condit_1)
            if True in condit_0:
                all_filter = self.filter_tags['and'](all_filter)
        if filter_tag:
            all_filter = self.filter_tags['filter'](all_filter)
        return all_filter
   
    def dec_filters_tags(method):
        def wrapper(self, *args):
            if args:
                all_args = []
                for arg in args:
                    all_args.append(arg)
                return method(self).format("".join(all_args))
            else:
                return ["filter opts"]
        return wrapper
   
    @dec_filters_tags
    def filter_tag_and(self):
        return "<AND>{}</AND>"
    
    @dec_filters_tags
    def filter_tag_or(self):
        return "<OR>{}</OR>"
   
    @dec_filters_tags
    def filter_tag_not(self):
        return "<NOT>{}</NOT>"
    
    @dec_filters_tags
    def filter_tag_filter(self):
        return "<Filter>{}</Filter>"

    def data2literal(self, data):
        if isinstance(data, (int, float)):
            data = str(data)
        if isinstance(data, str):
            data = data.decode('utf-8')
        return u"{}".format(data)

    def dec_filters_literal_opts(method):
        def wrapper(self, propertyname=None, literal=None):
            if propertyname and literal:
                tag = method(
                    self, 
                    propertyname=self.data2literal(propertyname), 
                    literal=self.data2literal(literal), 
                )
                return etree.tostring(tag.toXML()).decode("utf-8")
            elif not propertyname and not literal:
                return "value"
            else:
                raise Exception("Filter literal error")
        return wrapper
    
    def dec_test_propertiname(method):
        def wrapper(self, propertyname=None, *args, **kwargs):
            if propertyname: 
                layer_property_cap = [
                    self.data2literal(my) 
                    for my 
                    in self.layer_property_cap
                ] 
                if self.data2literal(propertyname) not in layer_property_cap:
                    raise Exception(
                        "Filter: error 'layer_property'='{}' not in capabilites".format(
                            propertyname
                        )
                    )
            return method(self, propertyname, *args, **kwargs)
        return wrapper
    
    @dec_test_propertiname
    @dec_filters_literal_opts 
    def filter_comp_equal_to(self, **kwargs):
        return PropertyIsEqualTo(**kwargs)

    @dec_test_propertiname
    @dec_filters_literal_opts 
    def filter_comp_not_equal_to(self, **kwargs):
        return PropertyIsNotEqualTo(**kwargs)

    @dec_test_propertiname
    @dec_filters_literal_opts 
    def filter_comp_greater_than(self, **kwargs):
        return PropertyIsGreaterThan(**kwargs)

    @dec_test_propertiname
    @dec_filters_literal_opts 
    def filter_comp_graater_than_or_equal_to(self, **kwargs):
        return PropertyIsGreaterThanOrEqualTo(**kwargs)

    @dec_test_propertiname
    @dec_filters_literal_opts 
    def filter_comp_less_than(self, **kwargs):
        return PropertyIsLessThan(**kwargs)

    @dec_test_propertiname
    @dec_filters_literal_opts 
    def filter_comp_less_than_or_equal_to(self, **kwargs):
        return PropertyIsLessThanOrEqualTo(**kwargs)

    @dec_test_propertiname
    def filter_comp_beetwen(self, propertyname=None, lower=None, upper=None):
        if propertyname and lower and upper:
            tag = PropertyIsBetween(
                propertyname=self.data2literal(propertyname), 
                lower=self.data2literal(lower), 
                upper=self.data2literal(upper), 
            )
            return etree.tostring(tag.toXML()).decode("utf-8")
        elif not propertyname and not lower and not upper:
            return [
                "lower value", 
                "upper value", 
            ]
        else:
            raise Exception("Filter error")

    @dec_test_propertiname
    def filter_comp_null(self, propertyname=None):
        if propertyname:
            tag = PropertyIsNull(
                propertyname=self.data2literal(propertyname), 
            )
            return etree.tostring(tag.toXML()).decode("utf-8")
        else:
            return None

    @dec_test_propertiname
    def filter_comp_like(self, propertyname=None, literal=None):
        if propertyname and literal:
            tag = PropertyIsLike(
                propertyname=self.data2literal(propertyname), 
                literal=self.data2literal(literal), 
                wildCard="*", 
                #singleChar=".", 
                singleChar="?", 
                escapeChar="!", 
            )
            return etree.tostring(tag.toXML()).decode("utf-8")
        elif not propertyname and not literal:
            return "value"
        else:
            raise Exception("Filter error")
        
    def dec_test_epsg_code(method):
        def wrapper(self, propertyname=None, **kwargs):
            if kwargs.get("epsg_code", False):
                epsg_code_cap = [self.data2literal(my) for my in self.epsg_code_cap] 
                if self.data2literal(kwargs["epsg_code"]) not in epsg_code_cap:
                    raise Exception(
                        "Filter: error 'epsg_code'='{}' not in capabilites".format(
                            kwargs["epsg_code"]
                        )
                    )
            else:
                kwargs["epsg_code"] = self.epsg_code_use
            return method(self, propertyname=None, **kwargs)
        return wrapper
    
    def dec_epsg_code_gjon(method):
        def wrapper(self, propertyname=None, **kwargs):
            kwargs["epsg_code"] = {
                "crs": {
                    "type": "EPSG",
                    "properties": {
                            "code": kwargs["epsg_code"], 
                        },
                    }
                }
            return method(self, propertyname=None, **kwargs)
        return wrapper

    @dec_test_epsg_code
    def filter_spat_bbox(self, propertyname=None, coord=None, epsg_code=None):
        if coord:
            tag = BBox(
                bbox=coord, 
                crs="EPSG:{}".format(epsg_code), 
            )
            return etree.tostring(tag.toXML()).decode("utf-8")
        elif not propertyname and not coord:
            return {
                "coord": [
                    "Latitude down left", 
                    "Longitude down left", 
                    "Latitude up right", 
                    "Longitude up right", 
                    ],
                "epsg_code": "epsg code projection",
            }
        else:
            raise Exception("Filter bbox: error")

    @dec_test_epsg_code
    @dec_epsg_code_gjon
    def filter_spat_buffer(self, 
                           propertyname=None, 
                           coord=None, 
                           radius=None, 
                           epsg_code=None, 
                           epsg_code_measure=3857):
        if isinstance(coord, (list, tuple)) and isinstance(radius, (int, float)):
            # lat <-> lon
            coord = [
                coord[-1], 
                coord[0]
            ]
            in_srs = osr.SpatialReference()
            in_srs.ImportFromEPSG(int(epsg_code["crs"]["properties"]["code"]))
            out_srs = osr.SpatialReference()
            out_srs.ImportFromEPSG(int(epsg_code_measure))
            # detect type coordinate system
            if out_srs.ExportToPCI()[1] != "METRE":
                raise Exception("'epsg_code_measure' is not geometric coordinate system")
            json_geom = {
                "type": "Point",
                "coordinates": coord
            }
            json_geom.update(epsg_code)
            # transform to measure epsg code 
            transform = osr.CoordinateTransformation(in_srs, out_srs)
            ogr_geom = ogr.CreateGeometryFromJson(
                json.dumps(
                    json_geom, 
                    ensure_ascii=False
                )
            )
            ogr_geom.Transform(transform)
            # create buffer
            gml_geom = ogr_geom.Buffer(radius*2).ExportToGML()
            prop_name = u"<ogc:PropertyName>{}</ogc:PropertyName>".format(
                self.geom_property_cap
            )
            return u"<ogc:Intersects>{0}{1}</ogc:Intersects>".format(
                prop_name, 
                gml_geom
            )
        elif not propertyname and not coord and not radius:
            return {
                "coord": [
                    "Latitude point", 
                    "Longitude point", 
                    ],
                "radius": "radius in meters",
                "epsg_code_measure": "epsg code for radius measuring, default 3857",
                "epsg_code": "epsg code projection",
            }
        else:
            raise Exception("Filter buffer: error")