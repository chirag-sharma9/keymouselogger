Right now the airflow pipeline is in path = /data/airflow/airflow-keylogger

Step 1: sync data from s3 to local by calling bash command -- s3 cmd
Step 2: update lmdb -- s3_to_lmdb.py
Step 3: delete keydata -- delete_keydata.py

The whole process concludes the airflow pipeline right now. However, this is an old pipeline that 
    (1) does not fix the mismatch problem
    (2) has an unlimited amount of key code 
    
Solutions and To-Dos
To solve this problem, we developed a script 's3_to_lmdb_fix_mismatch.py' that is run on command to build to a new lmdb path.
This script eventually needs to replace the 's3_to_lmdb.py' file in the airflow pipeline.

____________________________________________________
Note:
    There are some .json and .txt file used in the pipeline did not get copied over into this repo dude to confidentiality.