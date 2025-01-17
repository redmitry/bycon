#!/usr/local/bin/python3

import cgi, cgitb
import re
from os import environ, path, pardir
import csv
import sys
from uuid import uuid4

# local
dir_path = path.dirname( path.abspath(__file__) )
pkg_path = path.join( dir_path, pardir )
sys.path.append( pkg_path )

from beaconServer import *

################################################################################
################################################################################
################################################################################

def main():

    uploader()

################################################################################
################################################################################
################################################################################

def uploader():

    # print('Content-Type: text/plain\r\n\r\n', end='')

    cgitb.enable()
    accessid = str(uuid4())
    form = cgi.FieldStorage()

    response = {
        "error": {},
        "rel_path": "/tmp/"+accessid,
        "loc_path": path.join( *config[ "paths" ][ "web_temp_dir_abs" ], accessid ),
        "accessid": accessid,
        "plot_link": '/services/samplePlots/?accessid='+accessid,
        "host": "http://"+str(environ.get('HTTP_HOST'))
    }

    if not "upload_file" in form:
        response.update({"error": "ERROR: No `upload_file` parameter in POST..." })
        print_json_response(response)

    file_item = form['upload_file']
    file_name = path.basename(file_item.filename)
    file_type = file_name.split('.')[-1]
    data = file_item.file.read()

    response.update({
        "file_name": file_name,
        "file_type": file_type
    })

    with open(response["loc_path"], 'wb') as f:
        f.write(data)

    print_json_response(response)

################################################################################
################################################################################
################################################################################
################################################################################

if __name__ == '__main__':
    main()
