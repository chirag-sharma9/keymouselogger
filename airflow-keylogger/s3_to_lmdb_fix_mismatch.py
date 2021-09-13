import boto3, glob, json, csv, os
import pandas as pd
import numpy as np 
from tqdm.auto import tqdm

import cangjie.preprocess as cp
from hadrian.lmdb_database.lmdb_dataset import LmdbDatabase

## aws command to sync up s3 bucket and local folder
# aws s3 sync s3://truu-keyboard-mouse /data/datasets/truu_keyboard_mouse/ > /data/airflow/airflow-keylogger/s3_log.txt


# s3 bucket url
s3_bucket_address = 's3://truu-keyboard-mouse'

# luts for keys and apps
# key_dict_path = '/data/airflow/airflow-keylogger/keyDict.json'
app_dict_path = '/data/airflow/airflow-keylogger/appDict.json'

# path for local synced up s3 data format for glob path
keyboard_folder_path = '/data/datasets/truu_keyboard_mouse/keyboard/*/*/*/*'
keyboard_csv_path = '/data/datasets/truu_keyboard_mouse/keyboard_match/*/*/*/*/*.csv'

# path for keyboard data lmdb save path 
key_lmdb_path = '/data/datasets/truu_keyboard_mouse/lmdb_truu_keyboard_data_fix_mismatch'

# path for local synced up s3 data (keyboard only)
key_root_path = '/data/datasets/truu_keyboard_mouse/'

# s3 sync terminal command output file path
s3_terminal_output_path = '/data/airflow/airflow-keylogger/s3_log.txt'

lookup = {

    '~':'`', '!':'1',
    '@':'2', '#':'3',
    '$':'4', '%':'5',
    '^':'6', '&':'7',
    '*':'8', '(':'9',
    ')':'0', '_':'-',
    '+':'=', '{':'[',
    '}':']', ':':';',
    '\"':'\'', '<':',',
    '>':'.', '?':'/',
    '\|':'\\',
}

nonprint_dict = {
     '\x01': 'a',
     '\x02': 'b',
     '\x03': 'c',
     '\x04': 'd',
     '\x05': 'e',
     '\x06': 'f',
     '\x07': 'g',
     '\x08': 'h',
     '\t': 'i',
     '\n': 'j',
     '\x0b': 'k',
     '\x0c': 'l',
     '\r': 'm',
     '\x0e': 'n',
     '\x0f': 'o',
     '\x10': 'p',
     '\x11': 'q',
     '\x12': 'r',
     '\x13': 's',
     '\x14': 't',
     '\x15': 'u',
     '\x16': 'v',
     '\x17': 'w',
     '\x18': 'x',
     '\x19': 'y',
     '\x1a': 'z',
     '\x1b': '[',
     '\x1c': '\\',
     '\x1d': ']',
     '\x1f': '-',
}

key_dict = {

    'a':0, 'b':1, 'c':2,
    'd':3, 'e':4, 'f':5,
    'g':6, 'h':7, 'i':8,
    'j':9, 'k':10, 'l':11,
    'm':12, 'n':13, 'o':14,
    'p':15, 'q':16, 'r':17,
    's':18, 't':19, 'u':20,
    'v':21, 'w':22, 'x':23,
    'y':24, 'z':25, 'comma':26,
    '.':27, '/':28, ';':29,
    '\'':30, '[':31, ']':32,
    '\\':33, '1':34, '2':35,
    '3':36, '4':37, '5':38,
    '6':39, '7':40, '8':41,
    '9':42, '0':43, '-':44,
    '=':45, 'backspace':46, 'delete':46, 'enter':47,
    'space':48, 'tab':49, 'caps_lock':50,
    'cmd':51, 'left':52, 'right':53, 'up':54, 'down':55,
    'ctrl':56, 'ctrl_r':57, 'alt':58, 'alt_r':59,
    'shift':60, 'shift_r':61,
    'esc':62, '`':63, 'cmd_r': 64,
}    


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
    
    
def encodeApp(col, dict_path):
    
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

def encodeKey(col):
    
    codes = []
    for k in col.tolist():
        
        # 'upper case' to 'lower case' for special chars
        if k in lookup:
            k = lookup[k]
        # nonprintables
        if k in nonprint_dict:
            k = nonprint_dict[k] 
            
        if k in key_dict:
            codes.append(key_dict[k])
        else:
            codes.append(65)
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
    # app encoding
    key_df['app'] = encodeApp(key_df['app'], app_dict_path)
    # key encoding
    key_df['key'] = encodeKey(key_df['key'])
    lmdb_val = key_df.values.astype(np.float64)
    
    return lmdb_key, lmdb_val
    

# this part for fixing mismatch due to logging bug
def getCsvDataAsList(csv_path):
    out_lst = []
    with open(csv_path, 'r') as f:
        key_reader = csv.reader(f, delimiter='\n')
        for row in key_reader:
            out_lst.append(row[0])
    return out_lst

def writeToNewCsv(csv_path, out_lst):
    
    # check if folder exists
    folder_path = csv_path.rsplit('/', 1)[0]
    if not (os.path.exists(folder_path)):
        os.makedirs(folder_path)
    
    # check if file extis    
    with open(csv_path, 'w') as f:
        f_writer = csv.writer(f, delimiter='\n')
        f_writer.writerow(out_lst)
        
def fixMismatch():
    folders = [x for x in glob.glob(keyboard_folder_path) if not x.endswith('.csv')]
    for f in tqdm(folders):
        # sort the csv files in time order
        csv_lst = sorted(glob.glob(f+'/*.csv'))
        
        for i in range(len(csv_lst)):
            csv_cur = csv_lst[i]
            csv_cur_new = csv_cur.replace('keyboard/', 'keyboard_match/') # new path
            print(csv_cur_new)
            # check if new mathced data already existed
            if not (os.path.isfile(csv_cur_new)):
                if i == 0: # just get rid of the last line for the fist file of a folder
                    out_lst = getCsvDataAsList(csv_cur)[:-1]
                else:
                    # concat the last of the prev & anything before last of cur
                    out_lst_cur = getCsvDataAsList(csv_cur)
                    csv_prev = csv_lst[i - 1]
                    out_lst_prev = getCsvDataAsList(csv_prev)
                    out_lst = [out_lst_prev[-1]] + out_lst_cur[:-1]
                # write to new file    
                writeToNewCsv(csv_cur_new, out_lst)    
    
    
if __name__== "__main__":
    
    # fix mismatch
    fixMismatch()
    
    # reading all data from s3 local sync up folder
    csv_file_lst = glob.glob(keyboard_csv_path)
    # or only read updated data since last sync
    #csv_file_lst = getUpdateCsvFiles(s3_terminal_output_path)
    
    # parse the data and save to a dict for lmdb
    lmdb_dict = {}
    for csv_file_path in csv_file_lst:
        print(csv_file_path)
        try:
            lmdb_key, lmdb_val = getLmdbEntry(csv_file_path)
            if len(lmdb_val) > 0:
                lmdb_dict[lmdb_key] = lmdb_val
        except:
            print('Failed to generate')
    # Save to lmdb
    ld = LmdbDatabase(key_lmdb_path, dim = 4, dtype=np.float64)
    ld.write_lmdb(lmdb_dict)