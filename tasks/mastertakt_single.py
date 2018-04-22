#!/usr/bin/python3
import os
import sys 

import threading
import importlib
import psutil

import RPi.GPIO as GPIO

import time as TIME
from time import sleep
import subprocess
import flask
import requests

import webserver

GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)

# hardware SPI-Pins

spi_MOSI = 10
spi_MISO = 9
spi_SCK = 11
spi_CS0 = 8
spi_CS1 = 7

# soft SPI Pins
soft_MOSI = 6
soft_MISO = 13
soft_CS = 19
soft_SCK = 26

spi_delay = 0.00001
pulse_delay = 0.0002 # Pause zwischen zwei bytes

# soft_SPI	
hbyte = 0
lbyte = 0
status = 0

BUFFERSIZE = 48

PWTIEFE = 8

display_out_data = [0 for i in range(BUFFERSIZE)]
display_in_data = [0 for i in range(BUFFERSIZE)]

#out_data = []
out_startdaten = 0
in_startdaten = 0
out_lbdaten = 0
in_lbdaten = 0
out_hbdaten = 0
in_hbdaten = 0
out_data = [0 for i in range(BUFFERSIZE)]
outdatastring = ""
in_data = [0 for i in range(BUFFERSIZE)]
TimeoutCounter = 0
masterinput = 0 # out_startdaten vom Master nach shift
pendenzstatus = 0 		# status bei TWI off/on

webspistatus = 0
resetstatus = 0

charcounter = 0

SEND_STATUS0_BIT =	0	# Ankuendigen, dass in web-Schlaufe die Confirm-Status0-page geschickt wird
RESETDELAY_BIT	 =	7	# Anzeige, dass ein Hardware-Reset im Gang ist.
RESETREPORT		=	6	# Anzeige, dass ein reset erfolgte. Meldung an homecentral schicken

# defines fuer webspistatus
SPI_SHIFT_BIT =			0	# SPI einleiten
SPI_STATUS0_BIT	 =		1	
TWI_WAIT_BIT =			2	# TWI soll warten
DATA_RECEIVE_BIT =		3
TWI_STOP_REQUEST_BIT =	4	# TWI Stop  anmelden
WRITE_CONFIRM_BIT =		5	# Meldung von HomeCentral, dass EEPROM-Write OK ist
STATUS_CONFIRM_BIT =	6	# Status 0 ist n Master geschickt
SPI_DATA_READY_BIT =	7	# EEPROM-Daten fuer HomeServer sind bereit



# end SPI

# Wird in gpio.sh aufgerufen (beim Start in rc.local)
# Setzt GPIO23 (Port16) als Eingang fuer Taste. 
# Laeuft im Hintergrund.


# neu GPIO17 als Eingang fuer Start-Taste
GPIO.setup(17,GPIO.IN,pull_up_down=GPIO.PUD_UP)

GPIO.setup(27, GPIO.OUT) # Ausgng fuer LED
# zaehler fuer falling edge
edgecount=0

# aktuelle Zeit lesen
last_counttime=TIME.time()
global last_clicktime
last_clicktime=TIME.time()
ip_error = 0
mastercount = 0

#print("last: ",int(last_clicktime))
def running():
#https://stackoverflow.com/questions/43834075/check-if-a-particular-python-script-is-already-running
    for q in psutil.process_iter():
    
        if q.name() == 'python3':
            #print('cmdline: ', q.cmdline())
            prozesslinie = q.cmdline() # 
            if len(prozesslinie)>1 and 'webserver.py' in q.cmdline()[1]:
                return True

    return False
    
    
def on_off_callback(channels):
	print("Falling Edge")
	import time as TIME
	global edgecount
	global last_clicktime
	
	clicktime=TIME.time()
	#print("clicktime: ",int(clicktime), " last: ",int(last_clicktime), "diff: ",int(clicktime-last_clicktime))

	if ((clicktime-last_clicktime)>5):      # timeout, edgecount reset
		print("edgecount reset",edgecount, "last: ",int(last_clicktime))

		#print("edgecount reset",edgecount, "last: ",int(last_clicktime))
		edgecount=0
		last_clicktime=clicktime # last auf aktuelle Zeit setzen

	if (edgecount<2): # edgecount incrementieren
		print("Anzahl: ",edgecount)
		exit()
		edgecount=edgecount+1
	else: # ernst gemeint, 3 Clicks, ausschalten einleiten
		print("Dritter Click")

		# Anzeige Camera reset
		GPIO.setup(15, GPIO.OUT) # Port 10
		GPIO.output(15,0)

		# Anzeige Camera an Monitor OFF
		GPIO.setup(25,GPIO.OUT)
		GPIO.output(25,0)

		# Camera off
		subprocess.call(['pkill','raspivid'])

		# kurz warten
		TIME.sleep(3)


		# Anzeige Status reset
		i = 3
		while (i > 0):
			GPIO.output(17,0)
			TIME.sleep(1)
			GPIO.output(17,1)
			TIME.sleep(1)
			i = i - 1
		GPIO.output(27,0)


#print("add event detect")

# neu GPIO23 als Eingang fuer ON/OFF
GPIO.add_event_detect(17,GPIO.FALLING, callback=on_off_callback, bouncetime=200)

def spi_shift_out_byte(out_data):
	in_byte=0
	# atoi war notwendig wenn der Array mit append gefuellt wurde
	#out_byte = pi_atoi(out_data)
	out_byte = out_data
	#spi_delay = 0
	sleep(spi_delay)
	for pos in range(0,8):

		sleep(spi_delay)
		# Vorbereiten: Master legt Data auf MOSI
		if (out_byte & 0x80):# this bit is high
			GPIO.output(soft_MOSI, GPIO.HIGH) # MOSI HI 
		else:# this bit is low
			GPIO.output(soft_MOSI, GPIO.LOW) # MOSI LO						
		sleep(spi_delay) # kurz warten
	
		# Vorgang beginnt: Takt LO, Slave legt Data auf MISO
		GPIO.output(soft_SCK, GPIO.LOW) # SCK LO
		sleep(spi_delay)# kurz warten
	
		# Slave lesen von MISO
		if (GPIO.input(soft_MISO)):	# Bit vom Slave ist HI
			in_byte |= (1<<(7-pos))
		else:
			in_byte &= ~(1<<(7-pos))
		sleep(spi_delay)
		# Vorgang beendet: Takt HI, Data ist in in_byte 
	
		GPIO.output(soft_SCK, GPIO.HIGH) # SCK LO
		GPIO.output(soft_MOSI, GPIO.HIGH)
		sleep(spi_delay)
	
		out_byte = out_byte << 1	
		sleep(spi_delay)								#	Byte um eine Stelle nach links
	return in_byte


# funktionen Master
def spi_shift_data():
	global BUFFERSIZE
	# daten ZUM master
	global out_startdaten
	global out_lbdaten
	global out_hbdaten
	global out_data
	
	# daten VOM master	
	global in_startdaten
	global in_lbdaten
	global in_hbdaten
	global in_data
	
	terminalda = sys.__stdin__.isatty()
	
#	if terminalda is True:
#		print('spi shift data out_startdaten: ',out_startdaten)
#		print('spi shift data out_lbdaten 0: ',out_lbdaten)
#		print('spi shift data out_hbdaten 0: ',out_hbdaten)
#		print('spi shift data out_data 0: ',out_data[0])
#		print('spi shift data out_data 1: ',out_data[1])
#		print('spi shift data out_data 2: ',out_data[2])
#		print('spi shift data out_data 3: ',out_data[3])
	GPIO.output(soft_CS, GPIO.LOW) # CS lo
	#sleep(pulse_delay)
	in_startdaten = spi_shift_out_byte(out_startdaten)

	#sleep(pulse_delay)
	in_lbdaten = spi_shift_out_byte(out_lbdaten)
	#sleep(pulse_delay)
	in_hbdaten = spi_shift_out_byte(out_hbdaten)
	#sleep(3*pulse_delay)
	summe = 0
	for index in  range(0,BUFFERSIZE):
		#summe += out_data[index]
		in_data[index] = spi_shift_out_byte(out_data[index])
		#sleep(pulse_delay)
	
	#sleep(3*pulse_delay)
	
	
	complement = in_startdaten ^0xFF # https://stackoverflow.com/questions/7278779/bit-wise-operation-unary-invert
	in_enddaten = spi_shift_out_byte(complement)
	#sleep(pulse_delay)
	
	
	GPIO.output(soft_CS, GPIO.HIGH)# cs hi
	kontrolle = out_startdaten + in_enddaten
	if terminalda is True:
		#print('spi shift in_startdaten: ',in_startdaten,'complement von in_startdaten: ',complement, 'in_enddaten: ',in_enddaten)
		print('spi shift out_startdaten: ',out_startdaten, ' in_startdaten: ',in_startdaten,' complement  von in_startdaten: ',complement, 'in_enddaten: ',in_enddaten,' kontrolle: ',kontrolle)
	
	
	
	return in_startdaten



# end funktionen Master

		
akttime=TIME.time()
#if ((akttime-last_counttime)>10): # 
terminalda = sys.__stdin__.isatty()
GPIO.setmode(GPIO.BCM)
#outdaten = webserver.out_startdaten
#indaten = webserver.in_startdaten
#if terminalda is True:
	#print('mastertakt out_startdaten von webserver: ',outdaten, 'in_startdaten: ',indaten)
	#print('+++ mastertakt indaten von daten: ',daten.indaten, 'outdaten: ',daten.outdaten)
#daten.outdaten += 2	
# neu GPIO17 als Eingang fuer Start-Taste
GPIO.setup(17,GPIO.IN,pull_up_down=GPIO.PUD_UP)

GPIO.setup(27, GPIO.OUT) # Ausgng fuer LED


if terminalda is not None:
	print('running: ',running())

last_counttime=akttime
i = 1
while (i > 0):
	GPIO.output(27,1)
	TIME.sleep(0.5)
	GPIO.output(27,0)
	
	try:
		if terminalda is not None:
			print('start request twitakt')
		r = requests.get('http://192.168.1.212:5000/twi?pw=ideur00&twitakt=1&b0=24&b1=91&b2=24&b3=91')
		
		mastercount = mastercount + 1 # anz Aufrufe von master
		#print(type(r))
		if terminalda is not None:
			print('status: ',r.status_code, ' mastercount: ',mastercount)
		#print(r.headers)
		#print(r.headers['content-type'])
		
		ip_error = 0
		
		#TIME.sleep(1)
	except IOError:
		ip_error = (ip_error + 1)
		print('error mit requests. anz: ',ip_error)
		if (ip_error > 3):
			subprocess.call("python3 webserver.py", shell=True)
			print("cleanup")
			GPIO.cleanup()
			#exit()
		#pass
		
	except ValueError:
		print('Non-numeric data found in the file.')

	except ImportError:
		print ("NO module found")

	except EOFError:
		print('Why did you do an EOF on me?')

	
	except KeyboardInterrupt:
		#	
		print("cleanup in try request")
		GPIO.cleanup()
		sys.exit()
	except:
		print('An error occured.')
	
	i = i - 1
		
			
	#GPIO.cleanup()