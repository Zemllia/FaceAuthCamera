#!/bin/bash

apt-get install python3-pip cmake -y
python3 -m pip install -r requirements.txt
python3 webstraming.py
