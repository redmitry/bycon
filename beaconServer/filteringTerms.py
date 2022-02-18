#!/usr/local/bin/python3

import cgi, cgitb
import re, json, yaml
from os import environ, pardir, path
import sys, os, datetime

# local
# local
dir_path = path.dirname( path.abspath(__file__) )
pkg_path = path.join( dir_path, pardir )
sys.path.append( pkg_path )

from beaconServer import *

"""podmd

* <https://beacon.progenetix.org/beacon/filteringTerms

podmd"""

################################################################################
################################################################################
################################################################################

def main():

    filtering_terms()
    
################################################################################

def filteringTerms():
    
    filtering_terms()

################################################################################

def filtering_terms():

    initialize_service(byc)

    select_dataset_ids(byc)
    check_dataset_ids(byc)
    update_datasets_from_dbstats(byc)
    create_empty_beacon_response(byc)

    return_filtering_terms_response( byc )

    cgi_print_response( byc, 200 )

################################################################################
################################################################################
################################################################################

if __name__ == '__main__':
    main()
