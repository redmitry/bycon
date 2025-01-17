#!/usr/local/bin/python3

import cgi, cgitb
import re, json, yaml
from os import environ, pardir, path, scandir
import sys, datetime
from humps import camelize

# local
dir_path = path.dirname(path.abspath(__file__))
pkg_path = path.join( dir_path, pardir )
sys.path.append( pkg_path )

from beaconServer import *

"""podmd

* <https://progenetix.org/services/schemas/biosample>

podmd"""

################################################################################
################################################################################
################################################################################

def main():

    schemas()
    
################################################################################

def schemas():

    initialize_service(byc)
    create_empty_service_response(byc)

    schema_name = rest_path_value("schemas")
    comps = schema_name.split('.')
    schema_name = comps.pop(0)

    # if "empty_value" in schema_name:
    #     schema_name = "biosample"

    if not "empty_value" in schema_name:

        j = rest_path_value(schema_name)
        if "json" in j:
            s = read_schema_file(schema_name, "", byc, "json")
        else:
            s = read_schema_file(schema_name, "", byc)

        if not s is False:

            print('Content-Type: application/json')
            print('status:200')
            print()
            print(json.dumps(camelize(s), indent=4, sort_keys=True, default=str)+"\n")
            exit()
    
    response_add_error(byc, 422, "No correct schema name provided!")
    cgi_print_response( byc, 422 )

################################################################################
################################################################################

if __name__ == '__main__':
    main()
