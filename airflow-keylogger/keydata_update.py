from airflow import DAG
from airflow.operators.bash_operator import BashOperator
from airflow.operators.slack_operator import SlackAPIPostOperator
from datetime import datetime, timedelta
## Local file paths
# s3 bucket url
s3_bucket_address = 's3://truu-keyboard-mouse'

# path for keyboard data lmdb save path 
key_lmdb_path = '/data/datasets/truu_keyboard_mouse/lmdb_truu_keyboard_data'

# path for local synced up s3 data (keyboard only)
key_root_path = '/data/datasets/truu_keyboard_mouse/'

# s3 sync terminal command output file path
s3_terminal_output_path = '/data/airflow/airflow-keylogger/s3_log.txt'

#update lmdb script path
update_lmdb_script_path = '/data/airflow/airflow-keylogger/s3_to_lmdb_fix_mismatch.py'

# deletion script
delete_keydata_script_path = '/data/airflow/airflow-keylogger/delete_keydata.py'

## Bash commands to run
# bash code to sync s3 to local
s3_to_local_cmd = """
    aws s3 sync {{ params.s3_bucket_address }} {{ params.key_root_path }} > {{ params.s3_terminal_output_path }}
"""

# bash code to call the python script to update 
update_lmdb_cmd = """
    python {{ params.update_lmdb_path }}
"""

# bash code to call the python script to update 
delete_keydata_cmd = """
    python {{ params.delete_keydata_path }}
"""

## args for DAG
default_args = {
    'owner': "Pinn Zhang",
    'depends_on_past':False,
    'start_date': datetime(2020,2,27),
    'email' : ['pzhang@truu.ai'],
    'email_on_failure':False,
    'email_on_retry':False,
    'retries':1,
    'retry_delay':timedelta(minutes=5),
    'provide_context':True
}


## The DAG
with DAG('keydata_update', default_args=default_args, schedule_interval=timedelta(days=1)) as dag:

    # Task Init: Slack start message
    t_slack_s = SlackAPIPostOperator(
        task_id='slack_start',
        token = 'xoxp-200067492325-529467118193-582074584801-dee591f1f9ff656c9b1551f07b7085a8',
        text = '[pzhang:KEYBOARD LOGGER] Starting updating keyboard data LMDB...',
        channel='#airflow_msgs',
        username='Airflow Status'
    )

    # Task 1: sync data from s3 to local by calling bash command
    t_sync = BashOperator(
        task_id = 'sync_s3_data',
        bash_command = s3_to_local_cmd,
        params = {
            's3_bucket_address': s3_bucket_address,
            'key_root_path': key_root_path,
            's3_terminal_output_path': s3_terminal_output_path,
        }
    )

    # Task 2: update lmdb 
    t_update = BashOperator(
        task_id = 'update_lmdb',
        bash_command = update_lmdb_cmd,
        params = {
            'update_lmdb_path': update_lmdb_script_path,
        }    
    )
    
    # Task 3: delete keydata 
    t_delete = BashOperator(
        task_id = 'delete_keydata',
        bash_command = delete_keydata_cmd,
        params = {
            'delete_keydata_path': delete_keydata_script_path,
        }    
    )    
    
    # Task End: Slack end message
    t_slack_e = SlackAPIPostOperator(
        task_id='slack_complete',
        token = 'xoxp-200067492325-529467118193-582074584801-dee591f1f9ff656c9b1551f07b7085a8',
        text = '[pzhang:KEYBOARD LOGGER] Updating keyboard data LMDB completed!!!',
        channel='#airflow_msgs',
        username='Airflow Status'
    )
    
    t_slack_s >> t_sync >> t_update >> t_delete >> t_slack_e
    
