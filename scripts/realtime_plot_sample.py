import time
import matplotlib
from torch import threshold
matplotlib.use('TkAgg')
import matplotlib.pyplot as plt
from matplotlib import cm
import numpy as np
from pathlib import Path

'''
Interactive matplotlib plot that reads realtime output scores from DeepkeyActors module

:param THRESH: controls the threshold for genuine vs. impostor based on the raw scores
:param COLOR_OFFSET: will control the color of points plotted near the threshold line,
  for COLOR_OFFSET=0 points on (or very near) this line will be faint, larger
  values of COLOR_OFFSET push these points' colors away from the mid-point of the
  divergent colormap
:param COLOR_MAP: sets the matplotlib color map to be used. 
  see: https://matplotlib.org/stable/tutorials/colors/colormaps.html
:param SLEEP_TIME: controls the number of seconds to wait before accessing the scores text
  file to check for newly added values
:param SCORES_FNAME: is the file which contains the raw scores, see the bottom of DeepkeyActor
  class inside Actors.py for re-nameing the filename output
:param N_SCORES: controls the number of scores to display at any time. 
  '''
THRESH = 0.6
COLOR_OFFSET = 0.15
COLOR_MAP = cm.RdYlGn
SLEEP_TIME = 3
SCORES_FNAME = 'scores_out.txt'
N_SCORES = 5

# intiailize plot
plt.ion()
fig, ax = plt.subplots(1,1, figsize=(15,30))

ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)
ax.spines['bottom'].set_visible(False)
ax.set_xticks([])
ax.set_yticks([])
ax.set_ylabel('Likely Imposter                             Likely Genuine', fontsize=22)
ax.set_ylim([-0.05,1.05])
ax.set_xlim([0,N_SCORES+1])

# check for updates to the scores file periodically
fpath = Path(__file__).parent.resolve()
while True:
    # access file and get all scores
    yvals = []
    with open(fpath / SCORES_FNAME, 'r') as f:
        for score in f:
            assert(score[-1] == '\n')
            yvals.append(float(score.rstrip()))
    print('Number of scores: ', len(yvals))

    xmax = min(N_SCORES, len(yvals))
    xvals = list(range(1,xmax+1,1))

    def map_score(y, thresh=THRESH):
        if y <= thresh:
            new_y = (0.5/thresh)*y
            return new_y
        else:
            new_y = 0.5 + ((1-0.5)/(1-thresh))*(y-thresh)
            return new_y
    scaled_yvals = [map_score(y) for y in yvals]

    def map_for_color(y, thresh=THRESH, color_offset=COLOR_OFFSET):
        maxval=0.5-color_offset
        minval=0.5+color_offset
        if y <= thresh:
            # switch commented/uncommented code if color map is reversed
            #new_y = 0.5 - (thresh - y)*0.5/(0-thresh)
            #return minval + ((1-minval)/(1-0.5))*(new_y - 0.5)
            return (maxval/0.5)*y
        else:
            # switch commented/uncommented code if color map is reversed
            #new_y = 0.5 - (y-thresh)*0.5/(1-thresh)
            #return (maxval/0.5)*new_y
            return minval + ((1-minval)/(1-0.5))*(y - 0.5)    
    colors = [COLOR_MAP(map_for_color(y)) for y in yvals]

    # make plot
    #    if we do not want the horizontal line to be centered, but instead to align with the 
    #       threshold value, replace "scaled_yvals" with "yvals" in the line immediately below
    #       and replace "y=0.5" with "y=THRESH" two lines below.
    points = ax.scatter(xvals[-N_SCORES:], scaled_yvals[-N_SCORES:], c=colors[-N_SCORES:], s=100)
    ax.axhline(y=0.5, linestyle='--', c='k', alpha=0.3)

    #ax.relim()
    #ax.autoscale_view()
    fig.canvas.draw()
    fig.canvas.flush_events()
    plt.show()
    points.remove()

    time.sleep(SLEEP_TIME)