from pymongo import MongoClient
from pyexcel import get_sheet
from os import path as path
from datetime import datetime, date
import time
from progress.bar import IncrementalBar
import re, yaml
from isodate import parse_duration

################################################################################
################################################################################
################################################################################

def pgx_populate_callset_info( **kwargs ):

    """podmd
 
    ### Denormalizing Progenetix data

    While the Progenetix data schema is highly flexible, the majority of
    database content can be expressed with a limited set of parameters.

    The `pgx_populate_callset_info` method denormalizes the main information
    from the `biosamples` collection into the corresponding `callsets`, using
    the schema-free `info` object.

    podmd"""

    mongo_client = MongoClient( )
    mongo_db = mongo_client[ kwargs[ "dataset_id" ] ]
    bios_coll = mongo_db[ "biosamples" ]
    inds_coll = mongo_db[ "individuals" ]
    cs_coll = mongo_db[ "callsets" ]

    filter_defs = kwargs[ "filter_defs" ]

    cs_query = { }
    cs_count = cs_coll.estimated_document_count()

    bar = IncrementalBar('callsets', max = cs_count)

    for cs in cs_coll.find( { } ):

        update_flag = 0
        if not "info" in cs.keys():
            cs[ "info" ] = { }

        bios = bios_coll.find_one({"id": cs["biosample_id"] })
        inds = inds_coll.find_one({"id": bios["individual_id"] })

        if not "biocharacteristics" in inds:
            inds[ "biocharacteristics" ] = [ ]

        prefixed = [ *bios[ "biocharacteristics" ], *bios[ "external_references" ], *inds[ "biocharacteristics" ]  ]

        for mapped in prefixed:
            for pre in kwargs[ "filter_defs" ]:
                try:
                    if re.compile( filter_defs[ pre ][ "pattern" ] ).match( mapped[ "type" ][ "id" ] ):
                        cs[ "info" ][ pre ] = mapped[ "type" ]
                        # print(cs[ "info" ][ pre ][ "id" ])
                        update_flag = 1
                        break
                except Exception:
                    pass

        if "followup_months" in bios[ "info" ]:
            try:
                if bios[ "info" ][ "followup_months" ]:
                    cs[ "info" ][ "followup_months" ] = float("%.1f" %  bios[ "info" ][ "followup_months" ])
                    update_flag = 1
            except ValueError:
                return False            

        if "death" in bios[ "info" ]:
            if bios[ "info" ][ "death" ]:
                if str(bios[ "info" ][ "death" ]) == "1":
                    cs[ "info" ][ "death" ] = "dead"
                    update_flag = 1
                elif str(bios[ "info" ][ "death" ]) == "0":
                    cs[ "info" ][ "death" ] = "alive"
                    update_flag = 1

        if "age_at_collection" in bios:
            try:
                if bios[ "age_at_collection" ][ "age" ]:    
                    if re.compile( r"P\d" ).match( bios[ "age_at_collection" ][ "age" ] ):
                        cs[ "info" ][ "age_iso" ] = bios[ "age_at_collection" ][ "age" ]
                        cs[ "info" ][ "age_years" ] = _isoage_to_decimal_years(bios[ "age_at_collection" ][ "age" ])
                        # print(cs[ "info" ][ "age_iso" ])
                        # print(cs[ "info" ][ "age_years" ])
                        update_flag = 1
            except Exception:
                pass


        if update_flag == 1:
                cs_coll.update_one( { "_id" : cs[ "_id" ] }, { "$set": { "info": cs[ "info" ], "updated": datetime.now() } } )

        bar.next()

    bar.finish()
    mongo_client.close()

################################################################################
################################################################################
################################################################################

def pgx_read_mappings(**kwargs):

    equivmaps = [ ]
    equiv_keys = ["icdom::id", "icdom::label", "icdot::id", "icdot::label", "NCIT::id", "NCIT::label"]
#     equiv_keys.extend( [ ( "query::"+ek ) for ek in equiv_keys ] )

    # relevant sheet is the first one...
    print(kwargs[ "config" ][ "paths" ][ "mapping_file" ])       
    try:
        table = get_sheet(file_name=kwargs[ "config" ][ "paths" ][ "mapping_file" ])
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
            print(col_name+": "+str(hi))
            col_inds[ col_name ] = hi
            
        hi += 1
        
    for i in range(1, len(table)):
        equiv_line = { }
        col_match_count = 0
        for col_name in col_inds:
            try:
                cell_val = table[ i, col_inds[ col_name ] ]
                equiv_line[ col_name ] = cell_val
            except:
                continue
        if equiv_line.get("NCIT::id"):
            equivmaps.append(equiv_line)
            fi += 1
    
    print("mappings: "+str(fi))
    return(equiv_keys, equivmaps)

################################################################################
################################################################################
################################################################################

def pgx_write_mappings_to_yaml(**kwargs):
    
    example_max = 4
        
    if not kwargs[ "config" ][ "paths" ].get("icdomappath"):
        print("No existing icd YAML output path was provided with -y ...")
        return()
        
 
    if not path.isdir(kwargs[ "config" ][ "paths" ][ "icdomappath" ]):
        print("No existing icd YAML output path was provided with -y ...")
        return()
        
    equivmaps = kwargs["equivmaps"]

    for dataset_id in kwargs["config"]["dataset_ids"]:

        mongo_client = MongoClient( )
        mongo_db = mongo_client[ dataset_id ]
        mongo_coll = mongo_db[ "biosamples" ]

        for equivmap in equivmaps:

            if not _check_equivmap_data(equivmap, kwargs["equiv_keys"], kwargs["filter_defs"]):
                print("\nWrong format for mapping code(s):")
                print(equivmap)
                continue

            if not equivmap.get( "examples" ):
                equivmap["examples"] = [ ]
            if len(equivmap["examples"]) < example_max:

                query = { "$and": [ {"biocharacteristics.type.id": equivmap["icdom::id"]}, {"biocharacteristics.type.id": equivmap["icdot::id"]} ] }
 
                for item in mongo_coll.find( query ):

                    if item[ "description" ] not in equivmap["examples"]:
                        if len(equivmap["examples"]) < example_max:
                            equivmap["examples"].append( item[ "description" ] )
                        else:
                            continue            
        mongo_client.close()
        
    for equivmap in equivmaps:
    
        if not _check_equivmap_data(equivmap, kwargs["equiv_keys"], kwargs["filter_defs"]):
            continue
            
        if equivmap["icdom::id"] == 'icdom-99999':
            continue
        elif equivmap["icdot::id"] == 'icdot-C99.9':
            continue

        re_map = {
            'input':[
                { 'id': equivmap["icdom::id"], 'label' : equivmap["icdom::label"] },
                { 'id': equivmap["icdot::id"], 'label' : equivmap["icdot::label"] }
            ],
            'equivalents':[
                { 'id' : equivmap["NCIT::id"], 'label' : equivmap["NCIT::label"] }
            ],
            'examples': equivmap.get("examples"),
            'updated': date.today().isoformat()
        }
                
        yaml_name = equivmap["icdom::id"]+','+equivmap["icdot::id"]+'.yaml'
        
        with open(path.join( kwargs[ "config" ][ "paths" ][ "icdomappath" ], yaml_name ), 'w') as yf:
            yaml.safe_dump(re_map, yf, default_flow_style=False)
    

################################################################################
################################################################################
################################################################################

def pgx_normalize_prefixed_ids(**kwargs):

    mongo_client = MongoClient( )
    mongo_db = mongo_client[ kwargs[ "dataset_id" ] ]
    mongo_coll = mongo_db[ kwargs["update_collection"] ]

    query = { }

    # TODO:
    # * make those part of the prefix definitions in the config file
    
    fixes = { 
                "biocharacteristics": { "NCIT": "ncit" },
                "external_references": { "PMID": "pubmed" }
            }

    for item in mongo_coll.find( query ):
        for para in fixes:
            update_flag = 0
            new_para_is = [ ]
            for para_i in item[ para ]:
                for fix, old in fixes[ para ].items():
                    if old in para_i["type"]["id"]:         
                        para_i["type"]["id"] = re.sub(old, fix, para_i["type"]["id"])
                        update_flag = 1

                new_para_is.append( para_i )

            if update_flag == 1:
                mongo_coll.update_one( { "_id" : item[ "_id" ] }, { "$set": { para: new_para_is, "updated": datetime.now() } } )

    mongo_client.close()

################################################################################
################################################################################
################################################################################

def pgx_update_biocharacteristics(**kwargs):

    update_report = [ [ "id" ] ]
    update_report[0].extend( kwargs["equiv_keys"] )
    update_report[0].extend( [ "replaced_ncit::id", "replaced_ncit::label" ] )
        
    mongo_client = MongoClient( )
    mongo_db = mongo_client[ kwargs[ "dataset_id" ] ]
    mongo_coll = mongo_db[ kwargs["update_collection"] ]
    
    db_key = kwargs["filter_defs"]["icdom"][ "scopes" ][ kwargs["update_collection"] ][ "db_key" ]
    
    sample_no = 0
    for equivmap in kwargs["equivmaps"]:

        if not _check_equivmap_data(equivmap, kwargs["equiv_keys"], kwargs["filter_defs"]):
            print("\nWrong format for mapping code(s):")
            print(equivmap)
            continue
        
        query = { "$and": [ {db_key: equivmap["icdom::id"]}, {db_key: equivmap["icdot::id"]} ] }
        if equivmap["icdom::id"] == 'icdom-99999':
            query = { db_key: equivmap["icdot::id"] }
        elif equivmap["icdom::id"] == 'icdot-C99.9':
            query = { db_key: equivmap["icdom::id"] }
        
        for item in mongo_coll.find( query ):
            update_flag = 0
            new_biocs = [ ]
            for bioc in item[ "biocharacteristics" ]:               
                if re.compile( "NCIT" ).match(bioc["type"]["id"]):
                    if bioc["type"]["id"] != equivmap["NCIT::id"] or bioc["type"]["label"] != equivmap["NCIT::label"]:

                        report = [ item[ "id" ] ]
                        report.extend( str(equivmap[x]) for x in kwargs["equiv_keys"] )
                        report.extend( [ str(bioc["type"]["id"]), str(bioc["type"]["label"]) ] )
                        update_report.append(report)
            
                        bioc["type"]["id"] = equivmap["NCIT::id"]
                        bioc["type"]["label"] = equivmap["NCIT::label"]
                        update_flag = 1

                new_biocs.append( bioc )

            if update_flag == 1:
                mongo_coll.update_one( { "_id" : item[ "_id" ] }, { "$set": { "biocharacteristics": new_biocs, "updated": datetime.now() } } )
                sample_no +=1

    mongo_client.close()
    print(kwargs[ "dataset_id" ]+": "+str(sample_no))
    return(update_report)

################################################################################
################################################################################
################################################################################

def _check_equivmap_data(equivmap, equiv_keys, filter_defs):

    status = True

    for f_key in equiv_keys:
        if not equivmap.get( f_key ):
            status = False
        else:
            pre, kind = f_key.split("::")
            if kind == "id":
                if not re.compile( filter_defs[ pre ]["pattern"] ).match(equivmap[ f_key ]):
                    status = False

    return status

################################################################################
################################################################################
################################################################################

def _isoage_to_decimal_years(isoage):

    years, months = [ 0, 0 ]
    age_match = re.compile(r"^P(?:(\d+?)Y)?(?:(\d+?))?")
    if age_match.match(isoage):
        y, m = age_match.match(isoage).group(1,2)
        if y:
            years = y * 1
        if m:
            months = m * 1
        dec_age = float(years) + float(months) / 12
        return float("%.1f" % dec_age)

    return

