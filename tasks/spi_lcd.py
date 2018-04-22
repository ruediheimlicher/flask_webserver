import spidev
import time
import string
from time import sleep
from flask import Blueprint, render_template, abort 
from jinja2 import TemplateNotFound

from tasks import spi_task

spi = spidev.SpiDev()
#spi.open(0, 0)
#spi.max_speed_hz=(10000)

# SPI-commands
CHAR_TASK    =    0x01 # char senden, 2 bytes hex

GOTO_TASK     =  0x02 # goto senden, 2 bytes hex (col, line kombiniert)
STRING_TASK  =   0x03 # string senden bis \0
START_TASK    =    0x0D # CR, neues Paket
UINT8_TASK    =  4
UINT16_TASK   =  5
CLEAR_LCD     =  0x0A

DATA_TASK     =  0x06  # data an display senden
CMD_TASK      =  0x07  # cmd an display senden
END_TASK    =	6
NEW_TASK   =	 0x07

SPEED = 100000
#number of columns on the display 
#define LCD_COLS        20

_trans = None	

SLEEP = 0.000001

def int2hex(zahl):
	#https://stackoverflow.com/questions/14678132/python-hexadecimal
	return '%x' % zahl


def set_LCD(data):
	global spi
	spi.open(0, 0)
	spi.max_speed_hz=(SPEED)

	antwort = 0
	
	antwort = spi.xfer([data, data +1, data + 2])
	spi.close()  
	return antwort


def puthex(data): # 2bytes
	spi.open(0, 0)
	spi.max_speed_hz=(SPEED)
	#datastring = str(data)
	#datalist = [int(x,16) for x in datastring]
	hb = data & 0xF0
	lb = data & 0x0F
	antwort = spi.xfer([hb,lb])
	spi.close()  
	return antwort
	
def set_task(task): # 1 byte
	spi.open(0, 0)
	spi.max_speed_hz=(SPEED)
	antwort = spi.xfer([task])
	spi.close() 
	


def putc(char):
	#astr = int2hex(ord(char))
	#data = [0x0D,0x02,ord(astr[0]),ord(astr[1])]
	#antwort = spi.xfer(data)
	#return
	set_task(START_TASK) # CR
	#sleep(SLEEP)
	set_task(CHAR_TASK)
	#sleep(SLEEP)
	astr = int2hex(ord(char))
	set_task(ord(astr[0]))
	set_task(ord(astr[1]))

	#puthex(ord(char)) # 2 byte
	
def gotoxy(x,y):
	
	returnval = []
	returnval.append(x)
	
	set_task(START_TASK) # CR
	#sleep(SLEEP)
	set_task(GOTO_TASK)
	#sleep(SLEEP)
	astrx = int2hex(x)
	returnval.append(astrx)
	returnval.append(y)
	astry = int2hex(y)
	returnval.append(astry)
	#sleep(SLEEP)
	#set_task(ord(astr[0]))
	#if x < 16:
	#	set_task(ord('0'))
	#else:
	#	set_task(ord(astr[1]))
	returnval.append(x + ord('0'))
	set_task(x + ord('0'))
	sleep(SLEEP)
	returnval.append(y + ord('0'))
	set_task(y + ord('0'))
	
	#set_task(ord(astr[0]))
#	if (y < 16):
#		set_task(ord('0'))
#	else:
#		set_task(ord(astr[1]))
	
	set_task(0)
	
	return returnval
	
def checkint(x):
	astr = x + ord('0')
	return astr
	
	