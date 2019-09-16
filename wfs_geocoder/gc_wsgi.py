# -*- coding: utf-8 -*-
# encoding: utf-8

import os
import json
import urllib
from wsgiref.simple_server import make_server

from gc_core import GeoCoder


########################################################################
class GeoCoderWSGI(GeoCoder):
    """
    Tiny gcoder server
    """
    MAPSERV_ENV = [
        'CONTENT_LENGTH',
        'CONTENT_TYPE', 
        'CURL_CA_BUNDLE', 
        'HTTP_COOKIE',
        'HTTP_HOST', 
        'HTTPS', 
        'HTTP_X_FORWARDED_HOST', 
        'HTTP_X_FORWARDED_PORT',
        'HTTP_X_FORWARDED_PROTO', 
        'PROJ_LIB', 
        'QUERY_STRING', 
        'REMOTE_ADDR',
        'REQUEST_METHOD', 
        'SCRIPT_NAME', 
        'SERVER_NAME', 
        'SERVER_PORT'
    ]
    #----------------------------------------------------------------------
    def __init__(self, port=3008, host='0.0.0.0', **kwargs):
        self.gk_commands = {
            "GetCapabilites": self.get_capabilities, 
            "GetInfo": self.get_info, 
            "GetHelp": self.get_help, 
            "GetPropperties": self.get_properties,
        }
        self.wsgi_host = host
        self.wsgi_port = port
        GeoCoder.__init__(self, **kwargs)
    
    def application(self, env, start_response):
        print "-" * 30
        for key in self.MAPSERV_ENV:
            if key in env:
                os.environ[key] = env[key]
                print "{0}='{1}'".format(key, env[key])
            else:
                os.unsetenv(key)
        print "-" * 30
   
        status = '200 OK'
        if not env["QUERY_STRING"]:
            gk_comm_list = [my for my in self.gk_commands]
            gk_comm_list.append({})
            resp = json.dumps(
                gk_comm_list,
                ensure_ascii=False
            )
        elif self.gk_commands.has_key(env["QUERY_STRING"]):
            resp = json.dumps(
                self.gk_commands[env["QUERY_STRING"]](), 
                ensure_ascii=False
            )
        else:
            try:
                req = json.loads(urllib.unquote(env["QUERY_STRING"]))
                resp = json.dumps(
                    self.get_response(req), 
                    ensure_ascii=False
                )
            except Exception as err:
                status = '500 Server Error'
                resp = json.dumps(
                    {
                        "ERROR": u"{}".format(err),
                    }, 
                    ensure_ascii=False
                )
    
        result = b'{}'.format(resp.encode('utf-8'))
        start_response(status, [('Content-type', 'application/json')])
        return [result]
    
    def wsgi(self):
        httpd = make_server(
            self.wsgi_host,
            self.wsgi_port,
            self.application
        )
        print('Serving on port %d...' % self.wsgi_port)
        httpd.serve_forever()
        
    def __call__(self):
        self.wsgi()


def json_format(cont):
    print json.dumps(
        cont,
        sort_keys=True,
        indent=4,
        separators=(',', ': '), 
        ensure_ascii=False, 
    )


if __name__ == "__main__":
    gc = GeoCoderWSGI
    gc.out_geom = "gml"
    #gc.out_geom = "wkt"
    wsgi = gc()
    wsgi()