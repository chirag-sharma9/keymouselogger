from hadrian.lmdb_database.lmdb_dataset import LmdbDatabase
import numpy as np
import pandas as pd
import subprocess
from datetime import datetime, timedelta
import slack, requests


# aws s3 rm s3://truu-keyboard-mouse/ --dryrun --recursive --exclude "*" --include "*/spott/C02X207BHTD7/03022020/UTC-7_10_36_55_389420.csv"

slack_token = 'xoxp-200067492325-529467118193-582074584801-dee591f1f9ff656c9b1551f07b7085a8'
key_lmdb_path = '/data/datasets/truu_keyboard_mouse/lmdb_truu_keyboard_data'
keylogger_deletion_log_id = 'CUW76NQ8N'
keylogger_deletion_request_id = 'GUHTSUAL9'

# functions to construct s3_keys, lmdb_keys, and local keys for delection
def getKeyDf(ld):
    
    lmdb_keys = []
    timestamps = []
    users = []
    s3_keys = []
    local_keys = []
    
    for k in ld.get_keys_from_lmdb():

        # get datetime timestamp
        lmdb_key, timestamp = k.split(':')
        user, machineId = lmdb_key.split('_')
        timetamp, _ = timestamp.split('.') #get rid of '.csv'
        timezone, datestr = timetamp.split('_', 1)
        timestampstr = datetime.strptime(datestr, '%m%d%Y_%H_%M_%S_%f')

        # get s3 key path
        day, time = datestr.split('_',1)
        csv_path = timezone + '_' + time + '.csv'
        s3_key = '/'.join(['*', user, machineId, day, csv_path])
        local_key = '/'.join(['/data/datasets/truu_keyboard_mouse/keyboard', user, machineId, day, csv_path])
        
        lmdb_keys.append(k)
        users.append(user)
        timestamps.append(timestampstr)
        s3_keys.append(s3_key)
        local_keys.append(local_key) 
        
    df_dict = {
        'lmdb_keys':lmdb_keys,
        'timestamps':timestamps, 
        'users':users,
        's3_keys':s3_keys,
        'local_keys':local_keys
    }

    return pd.DataFrame(df_dict)

# delete from s3 bucket
def deleteS3(s3_keys):
    print('[S3 BUCKET] Deleting data from s3...')
    for k in s3_keys:
        cmd = ['aws', 's3', 'rm', 's3://truu-keyboard-mouse/', '--recursive', 
               '--exclude' '"*"', '--include', '"'+k+'"']
        try:
            subprocess.run(cmd)
            print(f'[S3 BUCKET] Deleted {k}')
        except:
            print(f'[S3 BUCKET] Did not find file for {k}')
    print('Finished deleteing from s3!!!!')
    
# delete from local 
def deleteLocal(local_keys):
    print('[LOCAL] Deleting data from local folder...')
    for k in local_keys:
        cmd = ['rm', k]
        try:
            subprocess.run(cmd)
            print(f'[LOCAL]Deleted {k}')
        except:
            print(f'[LOCAL] Did not find file for {k}')
    print('Finished deleteing from local folder!!!!')

# delete from lmdb
def deleteLMDB(ld, lmdb_keys):
    
    print('[LMDB]Deleting data from LMDB...')
    for k in lmdb_keys:
        try:
            ld.delete_keys(k)
            print(f'[LMDB]Deleted {k}')
        except:
            print(f'[LMDB]Did not find file for {k}')
    
    print('Finished deleteing from LMDB!!!!')    


## slack interaction functions    
# invite a user to channel
def inviteUser(user_id, slack_token):
    requests.post('https://slack.com/api/channels.invite',
                  {
                      'channel':keylogger_deletion_log_id, #keylogger-deletion-msg
                      'token': slack_token,
                      'user':user_id,
                })
    
# post private msg to each user in the channel    
def postPrivateMsgHelper(user_id, text, slack_token):
    post_msg = requests.post('https://slack.com/api/chat.postEphemeral',
              {
                  'token': slack_token,
                  'username': 'Python Deletion', # app user name
                  'channel':keylogger_deletion_log_id,
                  'text': text,
                  'user':user_id,
            }).json()
    
    return post_msg

def postPrivateMsg(user_id, text, slack_token):
    post_msg = postPrivateMsgHelper(user_id, text, slack_token)
    # if not in channel, invite and post again
    if not post_msg['ok']:
        inviteUser(user_id, slack_token)
        postPrivateMsgHelper(user_id, text, slack_token)   
        
# get a dictionary with content 'truu_user_name: truu_slack_user_id'
def getSlackUserID(slack_token):
    res = requests.get('https://slack.com/api/users.list',
                  {'token': slack_token}
    ).json()
    
    truu_slack_id_dict = {}
    for m in res['members']:
        truu_slack_id_dict[m['name']] = m['id'] 
        
    return truu_slack_id_dict


# construct a tuple of (user_lst, ts_lst, te_lst) for deletion
def getDeleteInfo(slack_token):
    
    # construct timestamps for now and now-24 hrs
    now = datetime.now()
    yesterday = datetime.now() -timedelta(hours = 24)
    now_ts = datetime.timestamp(now)
    yesterday_ts = datetime.timestamp(yesterday)
    
    res = requests.get("https://slack.com/api/conversations.history",
                         {'token': slack_token,
                          #channel: keylogger-deletion-request
                          'channel': keylogger_deletion_request_id,
                          'latest': now_ts,
                          'oldest': yesterday_ts,
                         }
                      ).json()
    
    # extract the texts
    msg_lst = []
    for m in res['messages']:
        # only grant access to pzhang and jwelch
        if (m['text'].startswith('[REQUEST]')) and (m['user'] == 'UJNQRBC1X' or m['user'] == 'UFKDR3G5P'):
            msg_lst.append(m['text'])

    users = []
    timestarts = []
    timeends = []
    
    #parse the texts and construct lists
    for msg in msg_lst:
        u,ts,te = msg.replace('[REQUEST] ', '').split('|')
        users.append(u)
        timestarts.append(ts)
        timeends.append(te)
        
    return users, timestarts, timeends



if __name__== "__main__":
    
    # construct lmdb keys, local keys and s3 keys for delection
    ld = LmdbDatabase(key_lmdb_path, dim = 4, dtype=np.float64)
    keydf = getKeyDf(ld)
    
    # get truu slack user id
    truu_slack_id_dict = getSlackUserID(slack_token)
    
    # read in delete csv
    users, timestarts, timeends = getDeleteInfo(slack_token)
    
    # get a df that contains entries need to be deleted, and get 
    # the lists of lmdb keys and s3 keys to delete
    df_to_delete_lst = []
    for u, ts, te in zip(users, timestarts, timeends):
        # grab user id
        user_id = truu_slack_id_dict[u]
        
        # make sure 'timeend' is later than 'timestart'
        # maybe some other time interval check policies later.
        ts_dt = datetime.strptime(ts, "%Y-%m-%d %H:%M:%S")
        te_dt = datetime.strptime(te, "%Y-%m-%d %H:%M:%S")
        
        # if timeend is earlier than timestart, post failure msg
        if ts_dt > te_dt: 
            # post failure warning to slack channel
            text = f'[DELETION FAILED] Time end {te} is earlier \
                     than time start {ts}.Please double check the entry.'
            
        # if timeend - timestart > 2 hrs, post failure msg
        elif (te_dt - ts_dt).total_seconds() > 60 * 60 * 2:
            text = f'[DELETION FAILED] Time interval {ts} and {te} \
                     exceeded 2 hours.'
        else:
            subdf = keydf[
                (keydf.users == u) &
                (keydf.timestamps >= ts) &
                (keydf.timestamps <= te)       
            ]
            df_to_delete_lst.append(subdf)
            # post success log to slack channel
            text = f'[DELECTION SUCCEEDED] Your key logger data \
                     from {ts} to {te} has been deleted'
        
        postPrivateMsg(user_id, text, slack_token)
        
    if len(df_to_delete_lst) > 0:
        # execute batch deletion
        delete_df = pd.concat(df_to_delete_lst)
        if len(delete_df) > 0:
            lmdb_keys_delete = delete_df['lmdb_keys'].tolist()
            s3_keys_delete = delete_df['s3_keys'].tolist()
            local_keys_delete = delete_df['local_keys'].tolist()

            print(s3_keys_delete)
            print(local_keys_delete)
            print(lmdb_keys_delete)

            # delete lmdb keys
            if len(s3_keys_delete) > 0:
                deleteS3(s3_keys_delete)
            if len(local_keys_delete) > 0:  
                deleteLocal(local_keys_delete)
            if len(lmdb_keys_delete) > 0:
                deleteLMDB(ld, lmdb_keys_delete)

# test case 1: time end earlier than time start
# test case 2: user not in the channel
