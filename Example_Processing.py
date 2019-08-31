#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r""" Processing with robust estimators

@author: Jordan W Bishop

Date Last Modified: 8/27/19
version 1.0

Args, Exceptions:
  NA

Returns:
  Plots the results of robust estimates of velocity and back-azimuth.

"""

# Loading modules
from collections import Counter
import copy as cp
import numpy as np
import matplotlib.pyplot as plt
from matplotlib import dates
import sys
import os  # noqa

from obspy import read
from ltsva import ltsva
import flts_helper_array as fltsh

# A Bogoslof Explosion recorded at the AVO Adak Infrasound Array
st = read('Bogoslof_Data.mseed')
st.plot()

# Array Parameters
arr = 'Adak Infrasound Array'
sta = 'ADKI',
chan = 'BDF'
loc = ['01', '02', '03', '04', '05', '06']
calib = 4.7733e-05

# Array Coordinates Projected into XY
rij = np.array([[0.0892929, 0.10716529, 0.03494914,
                 -0.043063, -0.0662987, -0.1220462],
                [-0.0608855, 0.0874639, -0.020600412169657,
                 0.00124259, 0.09052575, -0.09774634]])
rij[0, :] = rij[0, :] - rij[0, 0]
rij[1, :] = rij[1, :] - rij[1, 0]

# Filtering the data [Hz]
fmin = 0.5
fmax = 2.0
stf = st.copy()
stf.filter("bandpass", freqmin=fmin, freqmax=fmax, corners=6, zerophase=True)
stf.taper
stf.plot()

# Parameters from the stream file
nchans = len(stf)
# Construct the time vector
tvec = dates.date2num(stf[0].stats.starttime.datetime) + np.arange(0, stf[0].stats.npts / stf[0].stats.sampling_rate, stf[0].stats.delta)/float(86400) # noqa
npts = stf[0].stats.npts
dt = stf[0].stats.delta
fs = 1/dt

# Plot array coords as a check
plotarray = 1
if plotarray:
    fig10 = plt.figure(10)
    plt.clf()
    plt.plot(rij[0, :], rij[1, :], 'ro')
    plt.axis('equal')
    plt.ylabel('km')
    plt.xlabel('km')
    plt.title(arr)
    for i in range(nchans):
        # Stn lables
        plt.text(rij[0, i], rij[1, i], loc[i])


# Apply calibration value and format in a data matrix
calval = [4.01571568627451e-06, 4.086743142144638e-06,
          4.180744897959184e-06, 4.025542997542998e-06]
data = np.empty((npts, nchans))
for ii, tr in enumerate(stf):
    data[:, ii] = tr.data*calib

# Window length (sec)
winlen = 30
# Overlap between windows
winover = 0.50
# Converting to samples
winlensamp = int(winlen*fs)
sampinc = int((1-winover)*winlensamp)
its = np.arange(0, npts, sampinc)
nits = len(its)-1

# Pre-allocating Data Arrays
vel = np.zeros(nits)
vel.fill(np.nan)
az = np.zeros(nits)
az.fill(np.nan)
mdccm = np.zeros(nits)
mdccm.fill(np.nan)
t = np.zeros(nits)
t.fill(np.nan)
LTSvel = np.zeros(nits)
LTSvel.fill(np.nan)
LTSbaz = np.zeros(nits)
LTSbaz.fill(np.nan)
# Station Dictionary for Dropped LTS Stations
stdict = {}

print('Running wlsqva for %d windows' % nits)
for jj in range(nits):

    # Get time from middle of window, except for the end
    ptr = int(its[jj]), int(its[jj] + winlensamp)
    try:
        t[jj] = tvec[ptr[0]+int(winlensamp/2)]
    except:
        t[jj] = np.nanmax(t, axis=0)

    # LTS-Estimation alpha = 0.50
    # try:
    #     LTS_estimate = fastlts(X, tdelay, alpha=0.50)
    # except ValueError:
    #     # 0 vector cases (e.g. data spikes) currently
    #     # crash the program. This on the list will be fixed.
    #     pass

    try:
        LTSbaz[jj], LTSvel[jj], flagged, ccmax, idx, _ = ltsva(
                    data[ptr[0]:ptr[1], :], rij, fs, 0.50)
    except ValueError:
        pass

    mdccm[jj] = np.median(ccmax)
    stns = fltsh.arrayfromweights(flagged, idx)

    # Stash some metadata for plotting
    if len(stns) > 0:
        tval = str(t[jj])
        stdict[tval] = stns
    if jj == (nits-1):
        stdict['size'] = nchans

    tmp = int(jj/nits*100)
    sys.stdout.write("\r%d%% \n" % tmp)
    sys.stdout.flush()

print('Done\n')


# Now to plot. The Bogoslof back-azimuth is denoted
# with a dotted line.
# Plotting the Least Trimmed Squares Solution
cm = 'RdYlBu_r'   # colormap
cax = 0.2, 1          # colorbar/y-axis for mdccm
# The waveform subplot
fig1, axarr1 = plt.subplots(4, 1, sharex='col')
fig1.set_size_inches(9, 12)
axs1 = axarr1.ravel()
axs1[0].plot(tvec, data[:, 0], 'k')
axs1[0].axis('tight')
axs1[0].set_ylabel('Pressure [Pa]')
s = 'f = '+str(np.around(fmin, 4))+' - '+str(np.around(fmax, 4))+' Hz'
axs1[0].text(0.90, 0.93, s, horizontalalignment='center',
             verticalalignment='center', transform=axs1[0].transAxes)
axs1[0].text(0.15, 0.93, arr, horizontalalignment='center',
             verticalalignment='center', transform=axs1[0].transAxes)
cbot = 0.1
ctop = axs1[1].get_position().y1
cbaxes = fig1.add_axes([0.92, cbot, 0.02, ctop-cbot])
# The trace velocity subplot
sc = axs1[1].scatter(t, LTSvel, c=mdccm, edgecolors='gray', lw=0.1, cmap=cm)
axs1[1].set_ylim(0.15, 0.60)
axs1[1].set_xlim(t[0], t[-1])
axs1[1].plot([t[0], t[-1]], [0.25, 0.25], '-', color='grey')
axs1[1].plot([t[0], t[-1]], [0.44, 0.44], '-', color='grey')
sc.set_clim(cax)
axs1[1].set_ylabel('Trace Velocity\n [km/s]')
axs1[1].grid(b=1, which='major', color='gray', linestyle=':', alpha=0.5)
# The back-azimuth subplot
sc = axs1[2].scatter(t, LTSbaz, c=mdccm, edgecolors='gray', lw=0.1, cmap=cm)
axs1[2].set_ylim(0, 360)
axs1[2].set_xlim(t[0], t[-1])
axs1[2].plot([t[0], t[-1]], [65, 65], '--', color='grey')
sc.set_clim(cax)
axs1[2].set_ylabel('Back-azimuth\n [deg]')
axs1[2].grid(b=1, which='major', color='gray', linestyle=':', alpha=0.5)
hc = plt.colorbar(sc, cax=cbaxes, ax=[axs1[1], axs1[2]])
hc.set_label('MdCCM')
# The sausage plot of weights
timevec = t
t1 = timevec[0]
t2 = timevec[-1]
ndict = cp.deepcopy(stdict)
n = ndict['size']
ndict.pop('size', None)
tstamps = list(ndict.keys())
tstampsfloat = [float(ii) for ii in tstamps]
# set the second colormap
cm2 = plt.get_cmap('binary', (n-1))
initplot = np.empty(len(timevec))
initplot.fill(1)
axs1[3].scatter(np.array([t1, t2]), np.array([0.01, 0.01]), c='w')
axs1[3].axis('tight')
axs1[3].set_ylabel('Station [H#]')
axs1[3].set_xlabel('UTC Time')
axs1[3].set_xlim(t1, t2)
axs1[3].set_ylim(0.5, n+0.5)
# Loop through the stdict
for jj in range(len(tstamps)):
    z = Counter(list(ndict[tstamps[jj]]))
    keys, vals = z.keys(), z.values()
    keys, vals = np.array(list(keys)), np.array(list(vals))
    pts = np.tile(tstampsfloat[jj], len(keys))
    sc = axs1[3].scatter(pts, keys, c=vals, edgecolors='k',
                         lw=0.1, cmap=cm2, vmin=1-0.5, vmax=n-1+0.5)
axs1[3].xaxis_date()
axs1[3].tick_params(axis='x', labelbottom='on')
axs1[3].fmt_xdata = dates.DateFormatter('%HH:%MM:%SS')
axs1[3].xaxis.set_major_formatter(dates.DateFormatter("%H:%M:%S"))
p0 = axs1[0].get_position().get_points().flatten()
p1 = axs1[1].get_position().get_points().flatten()
p2 = axs1[2].get_position().get_points().flatten()
p3 = axs1[3].get_position().get_points().flatten()
cbaxes2 = fig1.add_axes([p3[0], 0.05, p3[2]-p3[0], 0.02])
hc = plt.colorbar(sc, orientation="horizontal", cax=cbaxes2, ax=axs1[3])
hc.set_label('Number of Flagged Station Pairs')
plt.subplots_adjust(right=0.87, hspace=0.12)