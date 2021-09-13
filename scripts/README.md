# Plotting with KeyMouseLogger

The realtime plotting utility is run as a separate script from the keymouselogger. This plotting utility reads raw score from a txt file which is populated by the DeepkeyActor class within Actors.py. Each time the keymouselogger is started and a keystroke is gathered, the DeepkeyActor class within Actors.py is instantiated and wipes the txt file clean, allowing for a fresh plot to be made. If you wish to preserve your scores, please make a copy of the output file (currently it defaults to scores_out.txt)

## Instructions to Plot
1. First start keystroke collection by runnning Collector.py from the terminal.
2. After keystroke collection has started, in a new terminal window run realtime_plot_sample.py, a separate interactive Matplotlib plotting window should pop up and automatically populate as you type.
    a. If the order of these steps is reversed, the scores from the previous instantiation of the keymouselogger will persist - being overlayed with new scores as they flow in. It is necessary to start realtime_plot_sample.py with a clean score txt file in order to only see the new, realtime scores.

## Altering the plot outputs
The realtime_plot_sample.py script uses matplotlib to generate plots, so all the usual functionality of matplotlib is available to customize the plots. A series of global variables are defined at the top of the script to easily tweak some basic settings, otherwise the plots can be altered manually within the script itself.