import boto3, glob, json, csv, os
import pandas as pd
import numpy as np 

import cangjie.preprocess as cp
from hadrian.lmdb_database.lmdb_dataset import LmdbDatabase

## aws command to sync up s3 bucket and local folder
# aws s3 sync s3://truu-keyboard-mouse /data/datasets/truu_keyboard_mouse/ > /data/airflow/airflow-keylogger/s3_log.txt


# s3 bucket url
s3_bucket_address = 's3://truu-keyboard-mouse'

# luts for keys and apps
key_dict_path = '/data/airflow/airflow-keylogger/keyDict.json'
app_dict_path = '/data/airflow/airflow-keylogger/appDict.json'

# path for local synced up s3 data format for glob path
keyboard_csv_path = '/data/datasets/truu_keyboard_mouse/keyboard/*/*/*/*/*.csv'

# path for keyboard data lmdb save path 
key_lmdb_path = '/data/datasets/truu_keyboard_mouse/lmdb_truu_keyboard_data'

# path for local synced up s3 data (keyboard only)
key_root_path = '/data/datasets/truu_keyboard_mouse/'

# s3 sync terminal command output file path
s3_terminal_output_path = '/data/airflow/airflow-keylogger/s3_log.txt'



def getUpdateCsvFiles(output_path):
    
    # '/home/pzhang/cangjie/s3_log.txt'
    with open(output_path, 'r') as o:
        rows = o.read()
        # parse the output to get the address
        rows = rows.split('\n')
        outs = [row for row in rows if row.startswith('download')]
        csv_file_lst = ['/'.join(o.split('/')[-6:]) for o in outs]
        # construct the full path and keep only keyboard data
        csv_file_lst_keyboard = [key_root_path+csv for csv in csv_file_lst if csv.startswith('keyboard')]

    return csv_file_lst_keyboard
    
    
def getKeyDataFromCsv(csv_file_path):
    
    # extract s3 key
    s3_key = '/'.join(csv_file_path.split('/')[4:])
    # parse the data to get key seq data
    key_seq = []
    with open(csv_file_path, 'r') as f:
        key_reader = csv.reader(f, delimiter='\n')
        for row in key_reader:
            key_seq.append(row[0].split(','))    
            
    return s3_key, key_seq
    
    
def getLmbdKey(s3_key):
    
    # construct lmdb key from s3_key string
    _, version, user, machineid, date, timestamp = s3_key.split('/')
    timezone, time = timestamp.split('_', 1)
    timestamp = '_'.join([timezone, date, time])
    lmdb_key = ':'.join([user + "_" + machineid,timestamp])
    
    return lmdb_key
    
    
def encodewithDict(col, dict_path):
    
    with open(dict_path, 'r') as d:
        dic = json.load(d)   
    
    codes = []
    for v in col.tolist():
        if v in dic: # look up code in the dict
            code = dic[v]
        else: # if not in the dict, add the new code in
            code = max(dic.values()) + 1
            dic[v] = code
            with open(dict_path, 'w') as d:
                json.dump(dic, d)
        codes.append(code)
        
    return codes
    
    
def getLmdbEntry(csv_file_path):
    
    s3_key, key_seq = getKeyDataFromCsv(csv_file_path)
    # construct lmdb keys(format user:machineid:timestamp)
    lmdb_key = getLmbdKey(s3_key)
    
    # remove extra keys from the seq
    key_seq = cp.popExtraKeys(key_seq)
    
    ## clean up key seq
    ghost_key_lst = cp.findGhostKeysS3(key_seq)
    key_seq = cp.deleteGhostKeyS3(key_seq, ghost_key_lst)
    
    # construct lmdb values
    key_df = cp.getKeyStrokeDfS3(key_seq)
    key_df['key'] = encodewithDict(key_df['key'], key_dict_path)
    key_df['app'] = encodewithDict(key_df['app'], app_dict_path)
    lmdb_val = key_df.values.astype(np.float64)
    
    return lmdb_key, lmdb_val
    
    
if __name__== "__main__":
    
    # reading all data from s3 local sync up folder
#     csv_file_lst = glob.glob(keyboard_csv_path)
    # or only read updated data since last sync
    csv_file_lst = getUpdateCsvFiles(s3_terminal_output_path)
    
    # parse the data and save to a dict for lmdb
    lmdb_dict = {}
    for csv_file_path in csv_file_lst:
        print(csv_file_path)
        lmdb_key, lmdb_val = getLmdbEntry(csv_file_path)
        if len(lmdb_val) > 0:
            lmdb_dict[lmdb_key] = lmdb_val
            
    # Save to lmdb
    ld = LmdbDatabase(key_lmdb_path, dim = 4, dtype=np.float64)
    ld.write_lmdb(lmdb_dict)

    
    
