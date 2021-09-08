#!/bin/bash

apt-get install python3-pip cmake libraspberrypi-bin sudo apt-get install python3-h5py -y
apt-get install libhdf5-dev libhdf5-serial-dev libatlas-base-dev libjasper-dev libqtgui4 libqt4-test -y
python3 -m pip install -r requirements.txt
python3 -m pip install -U numpy
python3 webstreaming.py
