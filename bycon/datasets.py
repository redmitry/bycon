#!/usr/local/bin/python3

import cgi, cgitb
import re, json, yaml
from os import environ, pardir, path
import sys, os, datetime

# local
dir_path = path.dirname(path.abspath(__file__))
pkg_path = path.join( dir_path, pardir )
sys.path.append( pkg_path )
from bycon.lib.cgi_utils import cgi_parse_query,cgi_print_json_response,cgi_break_on_errors
from bycon.lib.read_specs import dbstats_return_latest
from bycon.lib.parse_filters import select_dataset_ids, check_dataset_ids

service_lib_path = path.join( pkg_path, "services", "lib" )
sys.path.append( service_lib_path )

from service_utils import initialize_service, create_empty_service_response, populate_service_response, response_add_error,response_add_parameter,response_collect_errors,response_map_results

from byconeer.lib.schemas_parser import *


"""podmd

* <https://beacon.progenetix.org/datasets/>

podmd"""

################################################################################
################################################################################
################################################################################

def main():

    datasets()
    
################################################################################

def datasets():

    byc = initialize_service()

    parse_beacon_schema(byc)

    select_dataset_ids(byc)
    check_dataset_ids(byc)
    _get_history_depth(byc)

    r = create_empty_service_response(byc)

    r["meta"].update({
        "api_version": byc["beacon"]["info"]["version"],
    })

    ds_stats = dbstats_return_latest( byc["stats_number"], **byc )

    results = [ ]
    for stat in ds_stats:
        r["response"]["info"].update({ "date": stat["date"] })
        for ds_id, ds_vs in stat["datasets"].items():
            if len(byc[ "dataset_ids" ]) > 0:
                if not ds_id in byc[ "dataset_ids" ]:
                    continue
            if not ds_id in byc[ "dataset_definitions" ].keys():
                continue

            bds = byc["dataset_definitions"][ds_id]
            bds.update( {
                "updateDateTime": stat["date"],
                "version": stat["date"],
                "variantCount": ds_vs["counts"]["variants_distinct"],
                "callCount": ds_vs["counts"]["variants"],
                "sampleCount": ds_vs["counts"]["biosamples"]
            } )

            results.append( bds )

    populate_service_response( r, results )
    cgi_print_json_response( byc[ "form_data" ], r, 200 )

################################################################################

def _get_history_depth(byc):

    if "statsNumber" in byc["form_data"]:
        s_n = byc["form_data"].getvalue("statsNumber")
        try:
            s_n = int(s_n)
        except:
            pass
        if type(s_n) == int:
            if s_n > 0:
                byc.update({"stats_number": s_n})
    return byc

################################################################################
################################################################################

if __name__ == '__main__':
    main()
