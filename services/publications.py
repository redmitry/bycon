#!/usr/local/bin/python3

import cgi, cgitb
import re, json, yaml
from os import environ, path, pardir
import sys, datetime, argparse
from pymongo import MongoClient
from operator import itemgetter

# local
dir_path = path.dirname( path.abspath(__file__) )
pkg_path = path.join( dir_path, pardir )
sys.path.append( pkg_path )
from bycon.lib.cgi_utils import *
from bycon.lib.parse_filters import *
from bycon.lib.read_specs import *
from bycon.lib.query_generation import geo_query
from lib.service_utils import *

"""podmd

podmd"""

################################################################################
################################################################################
################################################################################

def main():

    publications("publications")
    
################################################################################

def publications(service):

    byc = initialize_service(service)
    read_bycon_configs_by_name( "geoloc_definitions", byc )

    # the method keys can be overriden with "deliveryKeys"
    d_k = form_return_listvalue( byc["form_data"], "deliveryKeys" )
    if len(d_k) < 1:
        if not "all" in byc["method"]:
            d_k = byc["these_prefs"]["methods"][ byc["method"] ]

    byc.update( { "filter_definitions": byc["these_prefs"]["filter_definitions"] } )
    get_filter_flags(byc)
    parse_filters(byc)

    # response prototype
    r = byc[ "config" ]["response_object_schema"]
    r.update( { "errors": byc["errors"], "warnings": byc["warnings"] } )
    r["response_type"] = service

    # saving the parameters to the response
    for p in ["method", "filters"]:
        r["parameters"].update( { p: byc[ p ] } )

    # data retrieval & response population
    query, error = _create_filters_query( **byc )
    if len(error) > 1:
        r["errors"].append( error )

    geo_q, geo_pars = geo_query( **byc )

    if geo_q:
        for g_k, g_v in geo_pars.items():
            r["parameters"].update( { g_k: g_v })
        if len(query.keys()) < 1:
            query = geo_q
        else:
            query = { '$and': [ geo_q, query ] }

    if len(query.keys()) < 1:
        r["errors"].append( "No query could be constructed from the parameters provided." )
        cgi_print_json_response( byc["form_data"], r, 422 )

    mongo_client = MongoClient( )
    pub_db = byc["config"]["info_db"]
    mongo_coll = mongo_client[ pub_db ][ "publications" ]

    p_re = re.compile( byc["filter_definitions"]["PMID"]["pattern"] )

    p_l = [ ]
    for pub in mongo_coll.find( query, { "_id": 0 } ):
        s = { }
        if len(d_k) < 1:
            s = pub
        else:
            for k in d_k:
                # TODO: harmless hack
                if k in pub.keys():
                    if k == "counts":
                        s[ k ] = { }
                        for c in pub[ k ]:
                            if pub[ k ][ c ]:
                                try:
                                    s[ k ][ c ] = int(float(pub[ k ][ c ]))
                                except:
                                    s[ k ][ c ] = 0
                            else:
                                s[ k ][ c ] = 0
                    else:
                        s[ k ] = pub[ k ]
                else:
                    s[ k ] = None
        try:
            s_v = p_re.match(s[ "id" ]).group(2)
            s[ "sortid" ] = int(s_v)
        except:
            s[ "sortid" ] = -1

        p_l.append( s )

    mongo_client.close( )
 
    r["data"] = sorted(p_l, key=itemgetter('sortid'), reverse = True)
    r[service+"_count"] = len(r["data"])

    # response
    cgi_print_json_response( byc["form_data"], r, 200 )

################################################################################
################################################################################

def _create_filters_query( **byc ):

    query = { }
    error = ""

    query_list = [ ]
    count_pat = re.compile( r'^(\w+?)\:([>=<])(\d+?)$' )

    for f in byc[ "filters" ]:
        pre_code = re.split('-|:', f)
        pre = pre_code[0]
        if count_pat.match( f ):
            pre, op, no = count_pat.match(f).group(1,2,3)
            dbk = byc[ "filter_definitions" ][ pre ][ "db_key" ]
            if op == ">":
                op = '$gt'
            elif op == "<":
                op = '$lt'
            elif op == "=":
                op = '$eq'
            else:
                error = "uncaught filter error: {}".format(f)
                continue
            query_list.append( { dbk: { op: int(no) } } )
        elif "start" in byc[ "filter_flags" ][ "precision" ] or len(pre_code) == 1:
            query_list.append( { "id": re.compile(r'^'+f ) } )
        else:
            query_list.append( { "id": f } )            

    if len(query_list) > 1:
        query = { '$and': query_list }
    else:
        query = query_list[0]

    return query, error

################################################################################
################################################################################

if __name__ == '__main__':
    main()
