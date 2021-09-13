# pykeycollect 
* A python framework for collecting keystroke biometrics

# Available Features

* Tri-Graph Hold Times - This is the hold time of a given key when preceeded by one key and followed by another
* Full KeyStroke Log

# Requirements
* Conda or MiniConda
* Python 3+
* https://github.com/boppreh/keyboard -- Installed by conda environment, see below

# Setting up the Environment and Building the Executable
Included in the repo are several .yml files which specify different conda environments. It is safe to simply use the keys_win_build.yml environment for all development purposes (unless you require an MKL backed numpy), but it is necessary to use it for deployment when using pyinstaller otherwise the final executable will be 200+ MB. 

To setup the environment simply execute the following command in an anaconda prompt
## Windows
```
~/pykeycollect> conda env create -f keys_win_build.yml
```
## OSX
```
~/pykeycollect> conda config --add channels conda-forge
~/pykeycollect> conda env create -f keys_osx_build.yml
```

## Activate the Environment and build
After installation completes, activate the environment and run pyinstaller with the included .spec file
```
~/pykeycollect> conda activate keys_build
(keys_build) ~/pykeycollect> pyinstaller Collector.spec
```
This will build an executable called Collector.exe in the dist folder. 


# Running the Logger
If you built the executeable, simply run the output file in the dist folder to start the logging process. Alternatively you can run the script directly as 
```
(keys_build) ~/pykeycollect> python Collector.py
```

Depending on your security policies you may need to run the executable as an administrator (sudo) for it to capture keyboard events. 

If running on OSX you may get the following error message upon start
```
... is calling TIS/TSM in non-main thread environment, ERROR : This is NOT allowed. Please call TIS/TSM in main thread!!!
```

This can be safely ignored for the time being, it is a known bug but it does not interfere with keystroke collection. 

## IMPORTANT NOTES FOR OSX
1. Do not close the terminal while running! If you close the terminal while running the collector, it will kill the main thread and will not push updates to the log. 

2. When Closing the app, do not close the terminal, but instead use the tray icon and select quit. This will do a clean shutdown of all actors and save any data that is still in the buffer to the appropriate output files.

## Tray Icon
Once the logger is started, a tray icon with a green/black checkered icon will show up in your system tray (windows) or in the upper right corner status tray (OSX). Clicking this icon (right click on windows) will bring up a context menu which allows you to enable/disable the logger, or quit the logger. 

## Output file
The current HEAD version of the repo has only the full keystroke logger enabled. This will generate a csv file with the following structure:
```
ScanCode, KeyName, Action, Time
```

* Scancode is the code returned by the operating system
* KeyName is the name of the key
* Action is U or D for up or down
* Time is the micro-second resolution result of time.perf_counter() indicating the time since the app started when the keystroke event occured.

The output file will appear in the same directory as the executable, so make sure you have write permissions to that directory... if running as an administrator then be aware that the output file will be owned by the admin account and permissions may need to be changed later.


# Using the Keylog Cleaner
If using the full keystroke logger actor, the output log may contain sensitive information that you want to filter out. For this purpose there is an included script ```cleaner.py``` which will help make this process easier. 

## Setup the conda environment
Using the keyclean.yml file you can setup a conda environment for this script. Since we don't want to include pandas in the main key logger executable, but we do use it in the cleaner we have to use a different environment

```
~/pykeycollect> conda env create -f keyclean.yml
```

Then activate the environment and run the script 
```
~/pykeycollect> conda activate keyclean
(keyclean) ~/pykeycollect> python cleaner.py
```

You will be prompted for the path to the log file you want to clean, and then be asked for a particular phrase that you want to remove. Note that the removal is not intelligent. E.g. if you are removing a password, and you have mistyped a character, it will not remove the mistyped password. Therefore it is suggested that you try (in addition to the entire phrase you want to remove) parts of a phrase you want to remove as well. So if your password were apple123 you might want to try removing appel, apple, 132, etc... in addition to the password to ensure that you remove all traces of the phrase.

## Known Bug with Key Cleaner

Currently the key cleaner will hang if you attempt to remove a key sequence that begins with a special character, this is due to the way that the shift key is handled. It is a known bug and it is recommended that if you need to remove a sequence that starts with a special character then the best solution is to simply drop the special characters and remove part of the sequence. Not ideal but until someone fixes the issue it is better than leaving in the entire sequence intact.

# Filtering Apps
* Currently this feature is only supported on OSX

If you want to prevent the key logger from registering keystrokes from certain apps (i.e. chat clients/email programs etc...) you can use the filters.ini file to specify a list of apps to filter on. If you do not know the name of the app you can simply use the Collector to determine it by running the program and typing some keys with the app you want to filter as the active application. The collector terminal will display the name of the app that it is receiving keystrokes on each line it gets an event from

```
[Safari] 46 m U 167.222946055
```

Then to filter on this app you just need to add a filters.ini file in the same directory as the exectuable with the following structure
```filters.ini
[Filters]
apps = Safari,Slack,Mail
```

Note: App Names are case sensitive

When the app first loads you should see a line like the following for each app in the list
```
Added Filter for app Safari
Added Filter for app Slack
Added Filter for app Mail
```

When typing in a filtered app, instead of seeing the keystroke data you will instead see
```
Filtered App [Slack]
Filtered App [Slack]
Filtered App [Slack]
Filtered App [Slack]
```

This indicates that the keystroke data is not being collected.

