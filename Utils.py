import os
import subprocess
import sys

# aws configs for data uploading
import base64
import json
import tzlocal
from datetime import datetime
import time

import urllib3

basic_auth_token = 'dHJ1dTpTdXBlckMwMGxQNHNzVzByZCE='
url = 'https://qzeh93i750.execute-api.us-west-2.amazonaws.com/v1'
headers = {
    'Authorization': f'Basic {basic_auth_token}'
}


def darwin_select_file_action(apath, cmd):
    ascript = '''
    -- apath - default path for dialogs to open too
    -- cmd   - "Select", "Save"
    on run argv
        set userCanceled to false
        if (count of argv) = 0 then
            tell application "System Events" to display dialog "argv is 0" ¬
                giving up after 10
        else
            set apath to POSIX file (item 1 of argv) as alias
            set action to (item 2 of argv) as text
        end if
        try
        if action contains "Select" then
            set fpath to POSIX path of (choose file default location apath ¬
                     without invisibles, multiple selections allowed and ¬
                     showing package contents)
            # return fpath as text
        else if action contains "Save" then
            set fpath to POSIX path of (choose file name default location apath)
        end if
        return fpath as text
        on error number -128
            set userCanceled to true
        end try
        if userCanceled then
            return "Cancel"
        else
            return fpath
        end if
    end run
    '''
    try:
        proc = subprocess.check_output(['osascript', '-e', ascript,
                                       apath, cmd])
        if 'Cancel' in proc.decode('utf-8'):  # User pressed Cancel button
            sys.exit('User Canceled')
        return proc.decode('utf-8')
    except subprocess.CalledProcessError as e:
            print('Python error: [%d]\n%s\n' % e.returncode, e.output)


def darwin_get_machine_serial_number():
    cmd = "system_profiler SPHardwareDataType | grep 'Serial Number' | awk '{print $4}'"
    result = subprocess.run(cmd, stdout=subprocess.PIPE, shell=True, check=True)
    return result.stdout.strip().decode('utf-8')


def darwin_get_username():
    cmd = "id -un"
    result = subprocess.run(cmd, stdout=subprocess.PIPE, shell=True, check=True)
    return result.stdout.strip().decode('utf-8')


def get_tz_offset():
    ts = time.time()
    utc_offset_sec = (datetime.fromtimestamp(ts) - datetime.utcfromtimestamp(ts)).total_seconds()
    utc_offset_hr = utc_offset_sec / 3600
    tz_offset = str(int(utc_offset_hr)) if utc_offset_hr <=0 else '+' + str(int(utc_offset_hr))

    return 'UTC' + tz_offset


def get_file_name(event):
    """ event should only be 'Keyboard' or 'Mouse' """
    username = darwin_get_username()
    MID = darwin_get_machine_serial_number()
    timenow = datetime.now()
    date = timenow.strftime('%m%d%Y')
    #tz_offset = tzlocal.get_localzone().zone.split('/')[-1] + '_' + timenow.strftime('%H_%M_%S_%f')
    tz_offset = get_tz_offset() + '_' + timenow.strftime('%H_%M_%S_%f')
    #print(f'local time zone long: {tzlocal.get_localzone()}')
    #print(f'local time zone short : {tzlocal.get_localzone().zone}')
    fname = '/'.join([username, MID, date, tz_offset]) + '.csv'
    print(f"Saving to {fname}")

    return fname


def upload_mouse(message):
    http = urllib3.PoolManager(cert_reqs='CERT_NONE',assert_hostname=False)
    try:
        r = http.request('POST',url,headers=headers,body=json.dumps(message).encode('utf-8'),timeout=5.0)
        print(r.data)
        print(r.status)
    except Exception as e1:
        print("Timeout 1")
        try:
            r = http.request('POST',url,headers=headers,body=json.dumps(message).encode('utf-8'),timeout=15.0)
            print(r.data)
            print(r.status)
        except Exception as e2:
            print("Timeout 2")
            try:
                r = http.request('POST',url,headers=headers,body=json.dumps(message).encode('utf-8'),timeout=30.0)
                print(r.data)
                print(r.status)
            except Exception as e3:
                print("Final Timeout Failed")
                print(e3)


def upload_keyboard(message):
    http = urllib3.PoolManager(cert_reqs='CERT_NONE',assert_hostname=False)
    try:
        r = http.request('POST',url,headers=headers,body=json.dumps(message).encode('utf-8'),timeout=5.0)
        print(r.data)
        print(r.status)
    except Exception as e1:
        print("Timeout 1")
        try:
            r = http.request('POST',url,headers=headers,body=json.dumps(message).encode('utf-8'),timeout=15.0)
            print(r.data)
            print(r.status)
        except Exception as e2:
            print("Timeout 2")
            try:
                r = http.request('POST',url,headers=headers,body=json.dumps(message).encode('utf-8'),timeout=30.0)
                print(r.data)
                print(r.status)
            except Exception as e3:
                print("Final Timeout Failed")
                print(e3)