import pandas as pd
import numpy as np
import os
import sys

#res = downdf['keycode'].rolling(window=len(s1)).apply(lambda x: True if np.all(x == s1) else False,raw=True)
#res2=list(map(lambda x: True if x == 1.0 else False,res))

def remove_sequences(seq:str,keymap):
    count = 0
    #We will sweep a rolling window over the name column
    #searching for the sequence of characters that we are looking for
    ss = list(seq)
    kSeq = seqToKeySeq(ss)
    for k in kSeq:
        if k not in keymap:
            print(f"Key {k} not present in file, no occurance of this sequence is present")
            return

    s1 = list(map(lambda x: keymap[x],kSeq))

    keymap[float('nan')] = 54

    downdf = keydata[keydata['Action'] == 'U'].copy()
    def shift_map(x):
        xp = x.Name
        try:
            return 'shift' if 'shift' in xp else xp
        except TypeError:
            print(x)
            if xp != xp:
                return 'command'

    downdf['PName'] = list(map(shift_map,downdf.itertuples()))

    #for the sake of this simple filter, we will ignore all command keys
    downdf = downdf[list(map(lambda x: x not in ['shift','command','esc','tab','up','down','right','left','enter','delete'],downdf['PName']))]
    downdf['keycode']=list(map(lambda x: keymap[x],downdf['Name']))

    res = downdf['keycode'].rolling(window=len(s1)).apply(lambda x: True if np.all(x==s1) else False,raw=True)
    res = list(map(lambda x: True if x == 1.0 else False, res))
    idx = downdf[res].index
    for i in idx:
        print(f"Occurence found ending on line {i}")
        end = i
        while (keydata.loc[i].Name != ss[0]) | (keydata.loc[i].Action != 'D'):
            #print(keydata.loc[i].Name,keydata.loc[i].Action)
            i -= 1
        
        start = i
        for j in range(start,end+1):
            #Remove all the data associated with this sequence
            data = keydata.loc[j].copy()
            data[0] = -1
            data[1] = '00'
            data[2] = '00'
            keydata.loc[j] = data 
        count += 1

    print(f"Removed {count} instances of sequence")


#Converts a string to a sequence of keys
def seqToKeySeq(iseq:str):
    seq = list(iseq)
    key_seq = []
    for i in range(len(seq)):
        ch = seq[i]

        if ch in specialKeyMap:
     #       key_seq.append('shift')
            ch = specialKeyMap[ch]
        elif ch.isupper():
            ch = ch.lower()
        key_seq.append(ch)

    return key_seq


if __name__ == "__main__":
    if len(sys.argv) > 1:
        path = sys.argv[1]
    else:
        print("Enter the path to the log file you wish to filter")
        path = input(">")
    
    if not os.path.isfile(path):
        print(f"ERROR: Unable to locate log at {path}!")
        exit(0)


    #We need to do one preprocessing step where we search for scancode 43 and replace the second comma in the line with the word 'comma'
    contents = []
    with open(path,'r') as file:
        contents = file.readlines()

    def fix_43(line):
        retval = line
        if retval.startswith('43,,'):
            sl = list(line)
            sl[3] = 'comma'
            retval = ''.join(sl)
        return retval

    lines = list(map(fix_43,contents))

    with open('temp.csv','w') as file:
        file.writelines(lines)


    keydata = pd.read_csv('temp.csv',header=None,names=['ScanCode','Name','Action','Time'])
    os.remove('temp.csv')
    unique_keys = keydata['Name'].unique()

    #The typical rolling window in pandas doesn't work on strings
    #so we lets make an inplace map of key names to integers
    keymap = {unique_keys[i]:i for i in range(len(unique_keys))}

    specialChars = list('!@#$%^&*()_+{}|:"<>?')
    specialCharsKey = list('1234567890-=[]\\;\',./')
    specialKeyMap = {specialChars[i]:specialCharsKey[i] for i in range(len(specialChars))}

    print(f"found {len(keydata)} keystrokes")
    run = True
    while run:
        print("Enter a sequence of characters you wish to filter from the logs, or type <<% to stop")
        seq = input(">")
        if seq == '<<%':
            print("Enter the output file path to save the modified logs to")
            opath = input(">")
            keydata.to_csv(opath,header=False,index=False)
            print("Done!")
            exit(0)
        else:
           remove_sequences(seq,keymap)