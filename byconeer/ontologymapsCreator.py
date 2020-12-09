#!/usr/local/bin/python3

import re, json, yaml
from os import path, environ, pardir
import sys, datetime
from isodate import date_isoformat
from pymongo import MongoClient
import argparse
from progress.bar import Bar
from pyexcel import get_sheet


# local
dir_path = path.dirname( path.abspath(__file__) )
pkg_path = path.join( dir_path, pardir )
sys.path.append( pkg_path )
from bycon.lib.read_specs import *
"""

## `ontologymapsCreator`

"""

################################################################################
################################################################################
################################################################################

def _get_args():

    parser = argparse.ArgumentParser()
    parser.add_argument("-t", "--test", help="test setting")
    args = parser.parse_args()

    return(args)

################################################################################

def main():

    service = "ontologymaps"

    byc = {
        "pkg_path": pkg_path,
        "config": read_bycon_configs_by_name( "defaults" ),
        "args": _get_args(),
        "errors": [ ],
        "warnings": [ ]
    }

    for d in [
        "dataset_definitions",
        "filter_definitions"
    ]:
        byc.update( { d: read_bycon_configs_by_name( d ) } )

    # first pre-population w/ defaults
    these_prefs = read_local_prefs( service, dir_path )
    for d_k, d_v in these_prefs.items():
        byc.update( { d_k: d_v } )

################################################################################

    if byc["args"].test:
        print( "¡¡¡ TEST MODE - no db update !!!")


    mongo_client = MongoClient( )
    o_m = { }

    for map_type in byc["map_types"]:

        o_l_max = len(byc["map_types"][ map_type ]["prefixes"])

        for ds_id in byc["dataset_ids"]:
            data_db = mongo_client[ ds_id ]
            for coll in byc["data_collections"]:
                no =  data_db[ coll ].estimated_document_count()
                if not byc["args"].test:
                    bar = Bar("Analyzing samples", max = no, suffix="%(percent)d%%"+" of "+str(no) )
                for s in data_db[ coll ].find({}):
                    o_l_c = 0
                    k_l = [ ]
                    o_l = [ ]
                    d = ""
                    if "description" in s:
                        d = s["description"].strip()

                    for pre in byc["map_types"][ map_type ]["prefixes"]:
                        data_key = byc["filter_definitions"][ pre ]["db_key"]
                        list_key = re.sub(".type.id", "", data_key)
                        data_re = re.compile( byc["filter_definitions"][ pre ]["pattern_strict"] )

                        for o in s[ list_key ]:
                            if data_re.match( o["type"]["id"] ):
                                k_l.append( o["type"]["id"] )
                                o_l.append( o["type"] )
                                o_l_c += 1
                                if o_l_max > o_l_c:
                                    break

                                k = "::".join(k_l)

                    if byc["args"].test:
                        print(k)
                    # if k == 'NCIT:C3372::icdom-80003::icdot-C44.9':
                    #     print(d, o_l)
                    if k in o_m:
                        if len(o_m[k]["examples"]) < byc["example_length"]:
                            o_m[k]["examples"].update([d])

                    else:
                        o_m[k]={
                                "id": k,
                                "examples": set([d]),
                                "code_group": o_l
                                }

                    if not byc["args"].test:
                        bar.next()
                if not byc["args"].test:
                    bar.finish()

        print("{} code combinations for {}".format(len(o_m.keys()), map_type))

        def_m = _read_mapping_defaults(dir_path, map_type, **byc)

        for def_k in def_m:
            if not def_k in o_m.keys():
                o_m.update( { def_k: def_m[def_k] } )
        print("Now {} code combinations after defaults ...".format(len(o_m.keys())))
        _export_ontologymaps(dir_path, service, map_type, o_m)

    if not byc["args"].test:
        om_coll = mongo_client[ byc["config"]["info_db"] ][ byc["config"]["ontologymaps_coll"] ]
        om_coll.drop()
        om_coll.insert_many( o_m.values() )
        print("==> Rewrote {}.{} collection".format(byc["config"]["info_db"], byc["config"]["ontologymaps_coll"]))

################################################################################
################################################################################
################################################################################

def _export_ontologymaps(dir_path, service, map_type, o_m):
    for k, content in o_m.items():
        if "examples" in content:
            content["examples"] = sorted(content["examples"])
    export = [ ]
    for o_k in sorted(o_m.keys()):
        export.append(o_m[o_k])
    yaml.dump(export, open(path.join(dir_path, "exports", service, "{}.yaml".format(map_type)),"w"))

################################################################################
################################################################################
################################################################################

def _read_mapping_defaults(dir_path, map_type, **byc):

    if not "mappingfile" in byc["map_types"][ map_type ]:
        return {}

    mf = path.join( dir_path, *byc["map_types"][ map_type ]["mappingfile"] )
    o_m_r = { }
    equiv_keys = [ ]
    pre_fs = byc["map_types"][ map_type ]["prefixes"]
    o_l_max = len(pre_fs)

    for pre in pre_fs:
        equiv_keys.append( pre+"::id" )
        equiv_keys.append( pre+"::label" )

    sheet_name = "__".join(pre_fs)+"__matched"

    try:
        table = get_sheet(file_name=mf, sheet_name=sheet_name)
    except Exception as e:
        print(e)
        print("No matching mapping file could be found!")
        exit()

    header = table[0]
    col_inds = { }
    hi = 0
    fi = 0
    for col_name in header:
        if col_name in equiv_keys:
            col_inds[ col_name ] = hi

        hi += 1

    for i in range(1, len(table)):
        id_s = [ ]
        bioc_s = [ ]
        bioc = { }
        col_match_count = 0
        for col_name in equiv_keys:
            try:
                cell_val = table[ i, col_inds[ col_name ] ]
                if "id" in col_name:
                    pre, code = re.split("[:-]", cell_val)
                    data_re = re.compile( byc["filter_definitions"][ pre ]["pattern_strict"] )
                    if data_re.match( cell_val ):
                        bioc = { "id": cell_val }
                        id_s.append( cell_val )
                else:
                    bioc.update( { "label": cell_val } )
                    bioc_s.append(bioc)
                    if len(id_s) == o_l_max:
                        o_k = "::".join(id_s)
                        o_m_r.update(
                            { o_k:
                                {
                                    "id": o_k,
                                    "code_group": bioc_s
                                }
                            }
                        )
                        fi += 1
            except:
                continue

    print("default mappings: "+str(fi))
    return o_m_r

################################################################################
################################################################################
################################################################################

if __name__ == "__main__":
    main()