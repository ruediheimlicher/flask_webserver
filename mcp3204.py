#! /usr/bin/python3

# http://robsraspberrypi.blogspot.ch/2016/01/raspberry-pi-adding-analogue-inputs.html
import spidev
import time
import math
from time import strftime

import string
spi = spidev.SpiDev()
spi.open(0, 0)
spi.max_speed_hz=(10000)
# https://bitbucket.org/pschow/rpiadctherm/src/dbfe8101eeb4/basiclogmcp.py?at=master&fileviewer=file-view-default

def readadc(adcnum):
    r = spi.xfer2([1,(8+adcnum)<<4,0])
    print("r: ",r)
    adcount = ((r[1] & 3) << 8) + r[2]
    return r
    
#while True:
#    try:
print('a0:',readadc(0), 'a1: ',readadc(1))
time.sleep(1)
code = 
r = spi.xfer2([1,(8+adcnum)<<4,0])
print(' r: ', r)
 #   except KeyboardInterrupt: 
spi.close()  