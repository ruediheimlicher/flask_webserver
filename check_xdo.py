#!/usr/bin/python3

import os,sys
import xdo
from time import sleep
import subprocess

subprocess.check_call(['export', 'DISPLAY=:0','DISPLAY=:0','xdotool', 'key', 'ctrl+F5'])
#subprocess.call(['xdotool', 'mousemove', '80', '90'])
#subprocess.call(['./refresh.sh'])

#os.system(" refresh.sh")