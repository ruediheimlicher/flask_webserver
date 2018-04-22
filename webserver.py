''' Code created by Matt Richardson for details, visit: 
http://mattrichardson.com/Raspberry-Pi-Flask/inde... ''' 
import os
import sys
import threading

import requests
import RPi.GPIO as GPIO 
from flask import Flask, render_template, request, Blueprint

from tasks import spi_lcd

from time import sleep
from ctypes import c_uint8
from array import array
from time import time
from os import environ
from math import *

import daten

#def before_request():
#    app.jinja_env.cache = {}


#from apcheduler.scheduler import Scheduler

# https://stackoverflow.com/questions/33837717/systemerror-parent-module-not-loaded-cannot-perform-relative-import
from tasks.spi_task import spi_task

import datetime
app = Flask(__name__)



app.register_blueprint(spi_task)
#app.before_request(before_request)

APP_ROOT = os.path.dirname(os.path.abspath(__file__))   # refers to application_top
APP_STATIC = os.path.join(APP_ROOT, 'static')

GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)


# https://randomnerdtutorials.com/raspberry-pi-web-server-using-flask-to-control-gpios/
#GPIO.setmode(GPIO.BCM)
# Create a dictionary called pins to store the pin number, name, and pin state:
#pins = {
 #  23 : {'name' : 'GPIO 23', 'state' : GPIO.LOW},
 #  24 : {'name' : 'GPIO 24', 'state' : GPIO.LOW}
 #  }

# Set each pin as an output and make it low:
#for pin in pins:
 #  GPIO.setup(pin, GPIO.OUT)
 #  GPIO.output(pin, GPIO.LOW)


# http://www.instructables.com/id/Python-WebServer-With-Flask-and-Raspberry-Pi/

#define actuators GPIOs

ledYlw = 24
ledGrn = 23
button = 25
senPIR = 18


#initialize GPIO status variables

ledYlwSts = 1
ledGrnSts = 0

buttonSts = GPIO.LOW
senPIRSts = GPIO.LOW
# Define led pins as output
GPIO.setup(ledYlw, GPIO.OUT) 
GPIO.setup(ledGrn, GPIO.OUT) 


# turn leds OFF 
GPIO.output(ledYlw, GPIO.HIGH)
GPIO.output(ledGrn, GPIO.LOW)

# button, sens
# Set button and PIR sensor pins as an input
GPIO.setup(button, GPIO.IN, pull_up_down=GPIO.PUD_UP)   
GPIO.setup(senPIR, GPIO.IN)

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

# tasks
NULLTASK			=	0xB0	# Nichts tun
ERRTASK				=	0xA0	# F
STATUSTASK			=	0xB1	# Status des TWI aendern
STATUSCONFIRMTASK	=	0xB2	# Statusaenderung des TWI bestaetigen
EEPROMREADTASK		=	0xB8	# von EEPROM lesen
EEPROMSENDTASK		=	0xB9	# Daten vom HomeServer an HomeCentral senden
EEPROMRECEIVETASK	=	0xB6	# Adresse fuer EEPROM-Write empfangen
EEPROMWRITETASK		=	0xB7	# auf EEPROM schreiben

RAMWRITEDAYTASK     =   0xD7  	# Daten ins RAM schreiben, nur an einem tag gueltig
EEPROMCONFIRMTASK	=	0xB5	# Quittung an HomeCentral senden
EEPROMREPORTTASK	=	0xB4	# Daten vom EEPROM an HomeServer senden
EEPROMREADWOCHEATASK =	0xBA
EEPROMREADWOCHEBTASK =	0xBB
EEPROMREADPWMTASK   =   0xBC  	# Daten fuer PWM-Array im EEPROM holen
EEPROMWAITTASK      = 	0xBE   # auf schreiben von EEPROM warten
RESETTASK			=	0xBF	# HomeCentral reseten
DATATASK			=	0xC0	# Normale Loop im Webserver
SOLARTASK			=	0xC1	# Daten von solar
MASTERERRTASK		=	0xC7	# Fehlermeldung vom Master senden



EventCounter = 0
statuscallcounter = 0	# test: counter der Aufrufe von 
maxAnzahl = 3			# maximale Anzahl Aufrufe bei status
GPIO.setup(soft_MOSI, GPIO.OUT)

GPIO.setup(soft_MISO, GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(soft_CS, GPIO.OUT)
GPIO.setup(soft_SCK, GPIO.OUT)

GPIO.output(soft_SCK, GPIO.HIGH)
GPIO.output(soft_MOSI, GPIO.HIGH)
GPIO.output(soft_CS, GPIO.HIGH)

def insert_str(string, str_to_insert, index):
    return string[:index] + str_to_insert + string[index:]

def twos_comp(val, bits):
    """compute the 2's complement of int value val"""
    if (val & (1 << (bits - 1))) != 0: # if sign bit is set e.g., 8bit: 128-255
        val = val - (1 << bits)        # compute negative value
    return val                         # return positive value as is

def rep(anz):
    # Check 
	masterindex=anz
	while (masterindex > 0):
         # run trigger
		spi_shift_out("17")
		masterindex -= 1
		sleep(10) #  sleep and repeat
		
    #return 'fertig' # CloseCheck is False, return 
	
	
def int2hex(zahl):
	#https://stackoverflow.com/questions/14678132/python-hexadecimal
	return '%02X' % zahl

def pi_atoi(astr):

  num = 0
  for c in astr:
    if '0' <= c <= '9':
      num  = num * 10 + ord(c) - ord('0')
    elif 'A' <= c <= 'F':
      num = 10 + ord(c) - ord('A')
    else:
      raise ValueError('atoi argument (%s) contains non-digit(s)' % astr)
  return num
    
def join(l, sep):
    out_str = ''
    for i, el in enumerate(l):
        out_str += '{}{}'.format(el, sep)
    return out_str[:-len(sep)]

def checkpw(pwarray):
#	komponenten = pwstring.split("&") # ['b0=0C', 'b1=55', 'b2=2A', 'b3=62']
	# pw 1
#	pos1 = komponenten[0].split('=') # Position von pw1, zeile, kolonne
#	zeile1 = int(pos1[1],16) % PWTIEFE
#	kolonne1 = int(pos1[1],16) // PWTIEFE # ganzzahldiv
#	passwort1 = pos1[0]
	
	# pw 2
#	pos2 = komponenten[2].split('=') # Position von pw1, zeile, kolonne
#	zeile2 = int(pos2[1],16) % PWTIEFE
#	kolonne2 = int(pos2[1],16) // PWTIEFE # ganzzahldiv
#	passwort2 = pos2[0]
	terminalda = sys.__stdin__.isatty()
#	if terminalda  is True:
#		print('terminalda: ',terminalda)
	l = len(pwarray)
	
#	print('checkpw l: ',l)
	pos1 = pwarray[0]
	zeile1 = pos1 % PWTIEFE
	kolonne1 = pos1 // PWTIEFE # ganzzahldiv
	passwort1 = pwarray[1]
#	if terminalda:
#		print('pos1: ',pos1,' zeile1: ',zeile1, ' kolonne1: ',kolonne1)
	
	pos2 = pwarray[2]
	zeile2 = pos2 % PWTIEFE
	kolonne2 = pos2 // PWTIEFE # ganzzahldiv
	passwort2 = pwarray[3]
#	if terminalda:
#		print('pos2: ',pos2,' zeile2: ',zeile2, ' kolonne2: ',kolonne2)
	#with open(os.path.join(APP_STATIC, 'passwort.txt')) as f:
	
	
	path = os.path.join(APP_STATIC, 'passwort.txt')
	#print(path)
	pwtabhandle  = open(path,"r")
	#pwtab = pwtabhandle.read()
	
	pwtabelle = []
	pwtabelle.append(pwtabhandle.readline())
	pwtabelle.append(pwtabhandle.readline())
	pwtabelle.append(pwtabhandle.readline())
	pwtabelle.append(pwtabhandle.readline())
	pwtabelle.append(pwtabhandle.readline())
	pwtabelle.append(pwtabhandle.readline())
	pwtabelle.append(pwtabhandle.readline())
	pwtabelle.append(pwtabhandle.readline())
	
#	print('linie 0',pwtabelle[0])
#	print('linie 1',pwtabelle[1])
#	print('linie 2',pwtabelle[2])
#	print('linie 3',pwtabelle[3])
#	print('linie 4',pwtabelle[4])
#	print('linie 5',pwtabelle[5])
#	print('linie 6',pwtabelle[6])
#	print('linie 7',pwtabelle[7])
	
	
	
	
	passwortlinie1 = pwtabelle[zeile1]
	homepasswort1 = passwortlinie1.split(',')[kolonne1]
	passwortlinie2 = pwtabelle[zeile2]
	homepasswort2 = passwortlinie2.split(',')[kolonne2]
#	if terminalda  is True:
#		print('passwortlinie1: ',passwortlinie1, 'kolonne1', kolonne1, 'passwort1 in: ',passwort1 )
#		print('homepasswort1: ',int(homepasswort1,16), 'a ',homepasswort1)

#		print('passwortlinie2: ',passwortlinie2,' kolonne2: ',kolonne2,' passwort2 in: ',passwort2)
#		print('homepasswort2: ',int(homepasswort2,16), 'a: ',homepasswort2)

	linie = sys.getsizeof(pwtabelle)
#	print(linie)
#	print('*\n')
#	print(pwtabelle)
#	print('*\n')
	pwtabhandle.close()
	
	
	return ((passwort1 == int(homepasswort1,16)) and (passwort2 == int(homepasswort2,16)))
	
#	return (homepasswort1 , ' ', passwort1, ' | ' ,homepasswort2, ' ',passwort2)
#	return passwortlinie1
	
	#return pos1

	#return komponentenarray

def spi_shift_out_byte(out_data):
	in_byte=0
	# atoi war notwendig wenn der Array mit append gefuellt wurde
	#out_byte = pi_atoi(out_data)
	out_byte = out_data
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
		#sleep(spi_delay)								#	Byte um eine Stelle nach links
	return in_byte

def spi_shift_data():
	global out_startdaten
	global out_lbdaten
	global out_hbdaten
	global out_data
	global in_data
	global BUFFERSIZE
	global in_startdaten
	global in_lbdaten
	global in_hbdaten
	
	
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
	sleep(pulse_delay)
	in_startdaten = spi_shift_out_byte(out_startdaten)

	sleep(pulse_delay)
	in_lbdaten = spi_shift_out_byte(out_lbdaten)
	sleep(pulse_delay)
	in_hbdaten = spi_shift_out_byte(out_hbdaten)
	sleep(3*pulse_delay)
	summe = 0
	for index in  range(0,BUFFERSIZE):
		#summe += out_data[index]
		in_data[index] = spi_shift_out_byte(out_data[index])
		sleep(pulse_delay)
	
	sleep(3*pulse_delay)
	
	
	complement = in_startdaten ^0xFF # https://stackoverflow.com/questions/7278779/bit-wise-operation-unary-invert
	in_enddaten = spi_shift_out_byte(complement)
	sleep(pulse_delay)
	
	
	GPIO.output(soft_CS, GPIO.HIGH)# cs hi
	kontrolle = out_startdaten + in_enddaten
	if terminalda is True:
		#print('spi shift in_startdaten: ',in_startdaten,'complement von in_startdaten: ',complement, 'in_enddaten: ',in_enddaten)
		print('spi shift out_startdaten: ',out_startdaten, ' in_startdaten: ',in_startdaten,' complement  von in_startdaten: ',complement, 'in_enddaten: ',in_enddaten,' kontrolle: ',kontrolle)
	
	
	
	return in_startdaten


@app.route("/")

def index():
	now = datetime.datetime.now()
	timeString = now.strftime("%Y-%m-%d %H:%M")
	# Read Sensors Status
	ledYlwSts = GPIO.input(ledYlw)
	ledGrnSts = GPIO.input(ledGrn)

	buttonSts = GPIO.input(button)
	senPIRSts = GPIO.input(senPIR)


	templateData = {
		'title' : 'Webserver',
		'time': timeString,
        		'pw': 'Ideur0047',
                'd1' :  '123',
                'd2' :  '456',
		'title' : 'HomeCentral',
		'ledYlw'  : ledYlwSts,
		'ledGrn'  : ledGrnSts,
		'buttontitle' : 'GPIO Input',
		'button'  : buttonSts,
		'senPIR'  : senPIRSts


	}
	#callMaster()
	return render_template('index.html', **templateData)


# Aktionen von Buttons: Bsp /ledYlw/off
@app.route("/<deviceName>/<action>")
def action(deviceName, action):

	now = datetime.datetime.now()
	timeString = now.strftime("%Y-%m-%d %H:%M")

	if deviceName == 'ledYlw':
		actuator = ledYlw
	if deviceName == 'ledGrn':
		actuator = ledGrn
   
	if action == "on":
		GPIO.output(actuator, GPIO.HIGH)
	if action == "off":
		GPIO.output(actuator, GPIO.LOW)
		     
	ledYlwSts = GPIO.input(ledYlw)
	ledGrnSts = GPIO.input(ledGrn)

	buttonSts = GPIO.input(button)
	senPIRSts = GPIO.input(senPIR)

	templateData = {
		'ledYlw'  : ledYlwSts,
		'ledGrn'  : ledGrnSts,
		'time': timeString,
		'out_data' : out_data,
        'pw': 'Ideur0047',
        'd1' :  0,
        'd2' : 0,
        'buttontitle' : 'GPIO Input',
        'button'  : buttonSts,
        'senPIR'  : senPIRSts,
	}
	
	
	return render_template('data.html', **templateData)


	


@app.route('/twi', methods=['GET', 'POST'])
def parse_request():
	global pendenzstatus
	global resetstatus
	global webspistatus
	global statuscallcounter
	global maxAnzahl
	global masterinput
	
	global charcounter
	
	global SEND_STATUS0_BIT
	global	SPI_SHIFT_BIT 		# SPI einleiten
	global SPI_STATUS0_BIT	
	global TWI_WAIT_BIT 		# TWI soll warten
	global DATA_RECEIVE_BIT 
	global TWI_STOP_REQUEST_BIT	# TWI Stop  anmelden
	global WRITE_CONFIRM_BIT	# Meldung von HomeCentral, dass EEPROM-Write OK ist
	global STATUS_CONFIRM_BIT	# Status 0 ist n Master geschickt
	global SPI_DATA_READY_BIT	# EEPROM-Daten fuer HomeServer sind bereit
	global TimeoutCounter
	global EventCounter
	global out_startdaten
	global out_data
	global in_data
	global out_lbdaten
	global out_hbdaten
	
	global in_startdaten
	global in_lbdaten
	global in_hbdaten

	
	global SEND_STATUS0_BIT 	# Ankuendigen, dass in web-Schlaufe die Confirm-Status0-page geschickt wird
	global RESETDELAY_BIT	# Anzeige, dass ein Hardware-Reset im Gang ist.
	global RESETREPORT	
	global 	NULLTASK			# Nichts tun
	global ERRTASK					# F
	global STATUSTASK				# Status des TWI aendern
	global STATUSCONFIRMTASK		# Statusaenderung des TWI bestaetigen
	
	global EEPROMREADTASK			# von EEPROM lesen
	global EEPROMSENDTASK			# Daten vom HomeServer an HomeCentral senden
	global EEPROMRECEIVETASK		# Adresse fuer EEPROM-Write empfangen
	global EEPROMWRITETASK			# auf EEPROM schreiben

	global RAMWRITEDAYTASK      	# Daten ins RAM schreiben, nur an einem tag gueltig
	global EEPROMCONFIRMTASK		# Quittung an HomeCentral senden
	global EEPROMREPORTTASK		# Daten vom EEPROM an HomeServer senden
	global EEPROMREADWOCHEATASK 
	global EEPROMREADWOCHEBTASK 
	global EEPROMREADPWMTASK     	# Daten fuer PWM-Array im EEPROM holen
	global RESETTASK				# HomeCentral reseten
	global DATATASK				# Normale Loop im Webserver
	global SOLARTASK				# Daten von solar
	global MASTERERRTASK			# Fehlermeldung vom Master senden
	
	global daten
	
	# test
	terminalda = sys.__stdin__.isatty()

	
#	if statuscallcounter == 0: # beim Start setzen
#		pendenzstatus |= (1<<SEND_STATUS0_BIT)
	# end test

	
	now = datetime.datetime.now()
	timeString = now.strftime("%d.%m.%Y %H:%M")
	minute = now.strftime("%M")
	stunde = now.strftime("%H")
	#print("stunde: ",stunde)
	data = request.args.get('twi')  # 
	twistatus = request.args.get('status')
	pw =  request.args.get('pw')
	#aaa = app.spi_hallo.from_object(spi_task)()
	#pwip = 'b0=0C&b1=55&b2=2A&b3=62'
	pwvonIP = '&b0=26&b1=0&b2=9&B3=52'
	
	pwIP = []
	err=0;
	b0 = request.args.get('b0')
	if (b0 == None):
		err += 1
		#pwIP.append(0)
	else:
		pwIP.append(int(b0,16))

	b1 = request.args.get('b1')
	if (b1 == None):
		err += 1	
		#pwIP.append(0)
	else:
		pwIP.append(int(b1,16))

	b2 = request.args.get('b2')
	if (b2 == None):
		err += 1	
		#pwIP.append(0)
	else:
		pwIP.append(int(b2,16))

	b3 = request.args.get('b3')
	if (b3 == None):
		err += 1	
		#pwIP.append(0)
	else:
		pwIP.append(int(b3,16))
		
#	if err == 0:
#		if terminalda  is True:
#			print('pwIP: ',pwIP,'err: ',err)
	
	pwok = 0
	if len(pwIP) == 4:
		pwok = checkpw(pwIP)
		if terminalda  is True:
			print('pwok: ',pwok)
		if pwok is False:
			templateData = {
		
			}
			return render_template('ciao.html', **templateData)

	else:
		templateData = {
		
		}
		return render_template('ciao.html', **templateData)


# *******************************************************************
#	Takt bearbeiten
# *******************************************************************

	# twitakt bearbeiten: Aufruf von timer
	twitakt = request.args.get('twitakt')
	
	#a = spi_lcd.set_LCD(1)
#	a = 0xAF
	#b = spi_lcd.puthex(0xB2)
#	ret = spi_lcd.gotoxy(0,0)
#	sleep(0.5)
#	spi_lcd.putc('y') 
	#ret = spi_lcd.checkint(8)
	#spi_lcd.puthex(11)
	if terminalda  is True:
		#a = spi_lcd.gotoxy(0,0)
		#spi_lcd.putc(chr(ord('a')+1))
		#spi_lcd.gotoxy(1,1)
		#spi_lcd.putc('c')
		#ret = spi_lcd.gotoxy(11,1)	
		#print(ret)
		#c = chr(ord('a')+ charcounter)
		
		#spi_lcd.putc(c)
		charcounter += 1
		print('charcounter: ',charcounter)
		#if (ord(c) > 121):
		#	charcounter = 0
		#for i in range(0,8):
		#	y = i & 0x03
		#	a = spi_lcd.gotoxy(i,0)
		#	x = chr(48 + i)
		#	print(x)
		#	spi_lcd.putc(x)
			#print('ret: ',a, 'orig: ',a-ord('0'))
		#	b = pi_atoi(str(7+i))
		#	print('b: ',b)

	if twitakt is not None:
		if terminalda  is True:
			print('twitakt: ',twitakt)
			#print('*** webserver indata von global: ',daten.indaten, 'outdaten: ',daten.outdaten)
		#daten.indaten += 1	
		check = webspistatus & (1<<TWI_STOP_REQUEST_BIT)
		if terminalda  is True:
			print('twitakt webspistatus: ',webspistatus, check)
			
		
		if (webspistatus & (1<<TWI_STOP_REQUEST_BIT) == 0):
			if terminalda  is True:
				print('twitakt webspistatus nach if not 0: ',webspistatus)

		
			dstring = "d0=27&d1="+ str(stunde) + "&d2="+ str(minute)
			#print("dstring: ",dstring)
			ipstring = "http://www.ruediheimlicher.ch/cgi-bin/experiment.pl?d0=27&d1="+ str(stunde) + "&d2="+ str(minute)
			#print("ipstring: ",ipstring)
			#res = requests.get("http://www.ruediheimlicher.ch/cgi-bin/experiment.pl?d0=27&d1="+ str(minute) + "&d2="+ str(stunde))
		
			plres = requests.get(ipstring)
		
		
			# file-operationen
	#		outdatafile = open('outfile.txt','r')
	#		outdata = outdatafile.readlines() # list
	#		outdatazahl = int(outdata[0],10)
	#		if terminalda  is True:
	#			print('outdata read: ',outdata, outdata[0],outdatazahl,'\n')
		
	#		outdatastring = outdata[3].split(" ")
	#		if terminalda  is True:
	#			print('outdatastring : ',outdatastring, '\n3: ',outdatastring[3])	

	#		outdatastring = str(outdatazahl + 15) + '\n'
	#		if terminalda  is True:
	#			print('outdatastring + : ',outdatastring)
	#		
	#		indatafile = open('outfile.txt','w')
		

		
			
			
			out_startdaten = DATATASK
			out_lbdaten= 0x13
			out_hbdaten= 0xA4
			out_data[0] = 1
			out_data[1] = 0x02
			out_data[2] = 0x03
			out_data[3] = 0x04

			masterinput = spi_shift_data()
		
			#if terminalda  is True:
				#print('l: ',len(out_data))
		
			# https://stackoverflow.com/questions/663171/is-there-a-way-to-substring-a-string-in-python
			outdatastring = ' '.join([str(x) for x in out_data])
			outdatastringA = ' '.join([str(x) for x in out_data[:24]])
			outdatastringB = ' '.join([str(x) for x in out_data[24:]])
			outdatastring = '*'.join((outdatastringA,outdatastringB))
		
			indexlist = list(range(24))
			outdatenlist = [indexlist,out_data[:24],out_data[24:]]

			indatenlist = [indexlist,in_data[:24],in_data[24:]]
		
			l1 = len(outdatastring)
			#outdatastring = insert_str(outdatastring,'|', 48)
			l2 = len(outdatastring)
			#if terminalda  is True:
				#print('l: ',len(out_data),' l1: ',l1,' l2: ',l2)
				#print('outdatastringA:\n',outdatastringA,'\noutdatastringB:\n',outdatastringB)
				#print('indexlist:\n',indexlist)
	#		indatafile.write(str(out_startdaten) + '\n')
	#		indatafile.write(str(out_lbdaten) + '\n')
	#		indatafile.write(str(out_hbdaten) + '\n')
	#		indatafile.write(outdatastring)


	#		indatafile.close()
	#		outdatafile.close()
	
			#hexinstartdaten = hex(in_startdaten)
		#	print('in_startdaten: ',in_startdaten,' hex ',hexinstartdaten, ' in_lbdaten: ', in_lbdaten, 'in_hbdaten: ',in_hbdaten)
			templateData = {
			'title' : 'Takt',
			
			'twitakt' : twitakt,
			'time' : timeString,
			'pwok' : pwok,
			'terminalda' : terminalda,
			'webspistatus': webspistatus,
			'masterinput' : masterinput,
			'in_startdaten': int2hex(in_startdaten),
			'in_lbdaten' : int2hex(in_lbdaten),
			'in_hbdaten' : int2hex(in_hbdaten),
			'indatenlist' : indatenlist,
		
			'out_startdaten': int2hex(out_startdaten),
			'out_lbdaten' : int2hex(out_lbdaten),
			'out_hbdaten' : int2hex(out_hbdaten),
		
		
			'outdatastring': outdatastring,
			'outdatastringA': outdatastringA,
			'outdatastringB': outdatastringB,
			'outdatenlist' : outdatenlist,
			'out_data' : out_data
			}
			#if terminalda  is True:
				#print('twitakt vor if : ', twitakt,'masterinput: ',masterinput)
				#print('outdatenlist:\n',outdatenlist)
		
			if twitakt == '2': # von mastertakt
				if terminalda  is True:
					print('twitakt ist: ',twitakt)
	
				return render_template('homedata.html', **templateData) # data anzeigen
		
			if terminalda  is True:
				print('twitakt ist: ',twitakt)
		
			return render_template('takt.html', **templateData)
			#return render_template('homedata.html', **templateData)
		
	
# *******************************************************************
	# status bearbeiten
# *******************************************************************

	twistatus = request.args.get('status')
	if not twistatus == None: # status vorhanden
		if terminalda  is True:
			print('status twistatus: ',twistatus)
		
		#webtaskflag = STATUSTASK
		out_startdaten = STATUSTASK
		#out_startdaten = 177
		
		
		

		if twistatus == '0': # TWI soll off werden
			if terminalda  is True:
				print('twistatus -> OFF')
			pendenzstatus |= (1<<SEND_STATUS0_BIT) # Warten auf statusconfirm vom Master
			
			webspistatus |= (1<<TWI_STOP_REQUEST_BIT)
			if terminalda  is True:
				print('status webspistatus: ',webspistatus)
			
			
			TimeoutCounter = 0
			EventCounter = 0x2FFF
			
			
			
			out_lbdaten=0
			out_hbdaten=0
			out_data[0] = 0
			out_data[1] = 0x13
			out_data[2] = 20
			out_data[3] = 0xBB

		
		elif twistatus == '1':
			if terminalda  is True:
				print('twistatus -> ON')
			webspistatus &= ~(1<<TWI_WAIT_BIT)
			
			webspistatus &= ~(1<<TWI_STOP_REQUEST_BIT) # parallel zu SEND_STATUS0_BIT (?)
			
			
			EventCounter=0x2FFF				# Eventuell laufende TWI-Vorgaenge noch beenden lassen
			out_lbdaten=0x00
			out_hbdaten=0x01
			out_data[0] = 1
			out_data[1] = 0x06
			out_data[2] = 0x07
			out_data[3] = 0xBE

		if terminalda  is True:
			print('parse out_startdaten: ',out_startdaten)
			#print('parse out_lbdaten: ',out_lbdaten)
			#print('parse out_hbdaten: ',out_hbdaten)
			#print('parse out_data 0: ',out_data[0])
			#print('parse out_data 1: ',out_data[1])
			#print('parse out_data 2: ',out_data[2])
			print('parse out_data 3: ',out_data[3])

	#	kontrollsumme = spi_shift_data()
		if terminalda  is True:
			print('parse out_startdaten in_data[3]: ',in_data[3])
		
				# confirm checken: Master meldet B2 (178) wenn TWI OFF 
		masterinput = spi_shift_data()  


		templateData = {
			'title' : 'Status',
			'twistatus' : 'status' + twistatus,
			'time' : timeString,
			'pwok' : pwok,
			'terminalda' : terminalda
		}
		
		return render_template('status.html', **templateData)
		
		
# *******************************************************************		
# 	Nachfragen ob TWI schon OFF
# *******************************************************************

	isstat0ok = request.args.get('isstat0ok')
	if not isstat0ok == None:
		
		statuscallcounter += 1 # Aufrufe zaehlen
		if terminalda  is True:
			print('isstat0ok: ',isstat0ok)
			print('statuscallcounter: ',statuscallcounter)
			
		# test
		if (statuscallcounter > maxAnzahl):
			if terminalda  is True:
				print('end statuscallcounter')
			pendenzstatus &= ~(1<<SEND_STATUS0_BIT) # aufhoeren
					
		# end test
		
		# confirm checken: Master meldet B2 (178) wenn TWI OFF 
		masterinput = spi_shift_data()  
		
		if terminalda  is True:
			print('masterinput: ',masterinput, ' statuscallcounter: ',statuscallcounter)
		
		if masterinput is 0xB2:
			pendenzstatus &= ~(1<<SEND_STATUS0_BIT) # TWI ist OFF
			#webspistatus &= ~(1<<TWI_STOP_REQUEST_BIT) # parallel zu SEND_STATUS0_BIT (?)
			
		if pendenzstatus & (1<<SEND_STATUS0_BIT):
			
			templateData = {
			'title' : 'Status',
			'twistatus' :  'status0-',
			'time' : timeString,
			'pwok' : pwok,
			'in_startdaten': int2hex(in_startdaten),
			'in_lbdaten' : int2hex(in_lbdaten),
			'in_hbdaten' : int2hex(in_hbdaten),

			'terminalda' : terminalda
			}
			# status0 an Master senden

			return render_template('status.html', **templateData)
		
		else:
			statuscallcounter = 0
			templateData = {
			'title' : 'Status',
			'twistatus' :  'status0+',
			'time' : timeString,
			'pwok' : pwok,
			'in_startdaten': int2hex(in_startdaten),
			'in_lbdaten' : int2hex(in_lbdaten),
			'in_hbdaten' : int2hex(in_hbdaten),

			'terminalda' : terminalda
			}

			return render_template('status.html', **templateData)

# *******************************************************************
# *******************************************************************
# EEPROM lesen
# *******************************************************************
# *******************************************************************

# *******************************************************************
# Adresse empfangen radr
# *******************************************************************
	
	radr = request.args.get('radr')
	if radr is not None:
		out_data[0] = int(radr,16)
		out_startdaten = EEPROMREADTASK 	# B8 Task an HomeCentral senden
		webspistatus |= (1<<SPI_SHIFT_BIT)
		
		TimeoutCounter = 0
		
		hb = request.args.get('hb')
		if hb is not None:
			out_hbdaten = int(hb,16)

		lb = request.args.get('lb')
		if lb is not None:
			out_lbdaten = int(lb,16)
		
		templateData = {
		'title' : 'readEEPROM adr',
		'twistatus' :  'radr',
		'time' : timeString,
		'pwok' : pwok,
		'in_startdaten': int2hex(in_startdaten),
		'in_lbdaten' : int2hex(in_lbdaten),
		'in_hbdaten' : int2hex(in_hbdaten),	
		
		'out_startdaten': int2hex(out_startdaten),
		'out_lbdaten' : int2hex(out_lbdaten),
		'out_hbdaten' : int2hex(out_hbdaten),
	
		'terminalda' : terminalda
		}
		summe = spi_shift_data()
		
#		out_startdaten = EEPROMREADTASK
		
		return render_template('status.html', **templateData)
# end radr

# Adresse bestaetigen rdata
	rdata = request.args.get('rdata')
	if rdata is not None:
		
		# Master abfragen
		out_startdaten = EEPROMREADTASK
		
		erfolg = spi_shift_data()
		
		if (in_startdaten == EEPROMREPORTTASK):
			webspistatus |= (1<<SPI_DATA_READY_BIT) # Daten bereit
			
		if webspistatus &(1<<SPI_DATA_READY_BIT) > 0: # Daten bereit
			

			indexlist = list(range(24))
			outdatenlist = [indexlist,out_data[:24],out_data[24:]]
			outdatastring = ' '.join([str(x) for x in out_data])
			
			indatenlist = [indexlist,in_data[:24],in_data[24:]]
			indatastring = '+'.join([str(x) for x in in_data[:8]])
			
			templateData = {
			'title' : 'readEEPROM',
			'twistatus' :  'eeprom+',
			'EEPROM_String' : indatastring,
			'rdata' : rdata,
			'time' : timeString,
			'pwok' : pwok,
			'in_startdaten': int2hex(in_startdaten),
			'in_lbdaten' : int2hex(in_lbdaten),
			'in_hbdaten' : int2hex(in_hbdaten),
			'indatenlist' : indatenlist,
			'indatastring': indatastring,
			'out_startdaten': int2hex(out_startdaten),
			'out_lbdaten' : int2hex(out_lbdaten),
			'out_hbdaten' : int2hex(out_hbdaten),
			'outdatastring': outdatenlist,
		
			'outdatenlist' : outdatenlist,
			'out_data' : out_data,



			'terminalda' : terminalda
			}
			
			
			
			return render_template('EEPROM_Data.html', **templateData)
		
		else: # noch nicht bereit
			templateData = {
			'title' : 'readEEPROM wait',
			'twistatus' :  'eeprom-',
			'rdata' : rdata,
			'time' : timeString,
			'pwok' : pwok,
			'terminalda' : terminalda
			}
			if terminalda  is True:
				print('rdata: ',rdata)

			return render_template('status.html', **templateData)
		
        # end rdata	

			
	# end EEPROM lesen
# *******************************************************************

	
# *******************************************************************	
# *******************************************************************
#	EEPROM schreiben
# *******************************************************************
# *******************************************************************
	wadr = request.args.get('wadr')
	if wadr is not None:
		if terminalda  is True:
			print('wadr:',wadr)
		out_startdaten = EEPROMWRITETASK # B7
		writecontrol = 0 # Vollstaendigkeit prüfen
		lb = request.args.get('lbyte')
		if lb is not None:
			out_lbdaten = int(lb,16)
			writecontrol += 1
		else:
			out_lbdaten = 0
		
		hb = request.args.get('hbyte')
		if hb is not None:
			out_hbdaten = int(hb,16)
			writecontrol += 1
		if terminalda  is True:
			print('wadr out_lbdaten: ',out_lbdaten, 'out_hbdaten: ',out_hbdaten)
	
		data = request.args.get('data') # daten ankuendigen: 
		if data is not None:
			if terminalda  is True:
				print('data=1:',data)
		# bytes in out_data
			d0 = request.args.get('d0')
			if d0 is not None:
				writecontrol += 1
				out_data[0] = int(d0,16)
			else:
				out_data[0] = 0
			
			if terminalda  is True:
				print('out_data[0]:',out_data[0])
			d1 = request.args.get('d1')
			if d1 is not None:
				writecontrol += 1
				out_data[1] = int(d1,16)
			else:
				out_data[1] = 0
			
			d2 = request.args.get('d2')
			if d2 is not None:
				writecontrol += 1
				out_data[2] = int(d2,16)
			else:
				dout_data[2] = 0
			
			d3 = request.args.get('d3')
			if d3 is not None:
				writecontrol += 1
				out_data[3] = int(d3,16)
			else:
				out_data[3] = 0
			
			d4 = request.args.get('d4')
			if d4 is not None:
				writecontrol += 1
				out_data[4] = int(d4,16)
			else:
				out_data[4] = 0
			
			d5 = request.args.get('d5')
			if d5 is not None:
				writecontrol += 1
				out_data[5] = int(d5,16)
			else:
				out_data[5] = 0
			
			d6 = request.args.get('d6')
			if d6 is not None:
				writecontrol += 1
				out_data[6] = int(d6,16)
			else:
				out_data[6] = 0
			
			d7 = request.args.get('d7')
			if d7 is not None:
				writecontrol += 1
				out_data[7] = int(d7,16)
			else:
				out_data[7] = 0
			
		
		indata = spi_shift_data()
		
		if terminalda  is True:
			print('outdata: ',out_data, 'writecontrol: ',writecontrol)
			print('shift in: ',indata, 'in_data: ',in_data)

		indexlist = list(range(24))
		outdatenlist = [indexlist,out_data[:24],out_data[24:]]
		outdatastring = ' '.join([str(x) for x in out_data])
			
		indatenlist = [indexlist,in_data[:24],in_data[24:]]
		indatastring = '+'.join([str(x) for x in in_data[:8]])
		
		
		templateData = {
			'title' : 'writeEEPROM',
			'twistatus' :  'wadr',
			'EEPROM_String' : indatastring,
			'rdata' : rdata,
			'time' : timeString,
			'pwok' : pwok,
			'in_startdaten': int2hex(in_startdaten),
			'in_lbdaten' : int2hex(in_lbdaten),
			'in_hbdaten' : int2hex(in_hbdaten),
			'indatenlist' : indatenlist,
			'indatastring': indatastring,
			'out_startdaten': int2hex(out_startdaten),
			'out_lbdaten' : int2hex(out_lbdaten),
			'out_hbdaten' : int2hex(out_hbdaten),
			'outdatastring': outdatenlist,
		
			'outdatenlist' : outdatenlist,
			'out_data' : out_data,



			'terminalda' : terminalda
		}
		return render_template('status.html', **templateData)	
		#return render_template('EEPROM_Data.html', **templateData)

	# end wadr
	
	iswriteok = request.args.get('iswriteok')
	if iswriteok is not None:
		if terminalda  is True:
			print('iswriteok:',iswriteok)
		
		# EEPROMCONFIRMTASK (B5) von Master abfragen
		out_startdaten = EEPROMCONFIRMTASK
		indata = spi_shift_data()
		
		if terminalda  is True:
			
			print('EEPROMCONFIRMTASK shift in: ',indata, 'in_data: ',in_data)
				
		templateData = {
			'title' : 'writeEEPROM iswriteok',
			'out_startdaten': int2hex(out_startdaten)
		
			}
	
		if indata == EEPROMCONFIRMTASK: # Master hat EEPROM geschrieben	
			templateData['twistatus'] = 'write+'
		
		else:
			templateData['twistatus'] = 'write-'
		
		return render_template('status.html', **templateData)
		
		# end iswriteok
			
# *******************************************************************
# end EEPROM schreiben



	
#	in_data = []
#	out_data = []
	dataindex=0
	
	#out_startdaten = 0xC0
	
	out_startdaten = 0xC0
	out_lbdaten = 23
	out_hbdaten = 56
	
	
	
	
	d0 = request.args.get('d0')
	if (d0 != None):
		out_data[0] = int(d0,16)
		

	display_out_data[0] = str(d0)
	d1 = request.args.get('d1')
	# http://www.i-programmer.info/programming/python/3942-arrays-in-python.html?start=1
	if (d1 != None):
		out_data[1] = int(d1,16)
	display_out_data[1] = str(d1)
		
	dataindex += 1
	d2 = request.args.get('d2')
	if (d2 != None):
		out_data[2] = int(d2,16)
	display_out_data[2] = str(d2)
	
	d3 = request.args.get('d3')
	if (d3 != None):
		out_data[3] = int(d3,16)
	display_out_data[3] = str(d3)
	
	out_data[4] = 122
	out_data[BUFFERSIZE-1] = 222
	count = len(out_data)
	
	
	outdatastring = join(out_data,'+')
	# spi out
	summe = 0
	shiftindex=0
	
#	summe = spi_shift_data()
	
#	GPIO.output(soft_CS, GPIO.LOW)
#	for zeile in out_data:
#		summe += zeile
#		if not zeile is None:
#			in_zeile = spi_shift_out_byte(zeile)
			#in_data.append(in_zeile)
			
#		display_in_data[shiftindex] = str(in_zeile)
#		shiftindex = shiftindex + 1
#		sleep(0.05)
#	GPIO.output(soft_CS, GPIO.HIGH)
	

	# send data in in_data
	#https://stackoverflow.com/questions/35661526/how-to-send-and-receive-data-from-flask
	#res = requests.get("http://www.ruediheimlicher.ch/Data/TimePrefs.txt")
	
	#print('res',' text')
	#print('res',res.text)
	
#	res = requests.get("http://www.ruediheimlicher.ch/Data/TimePrefs.txt")
#	try:
#		if not (res.text == None):
			#pass
#			if terminalda  is True:
#				print('TimePrefs: ',res.text)
#	except:
		#pass
#		if terminalda  is True:
#				print('Fehler mit TimePrefs')
	
	res = requests.get("http://www.ruediheimlicher.ch/cgi-bin/experiment.pl?d0=27")
	sleep(0.5)
	if not (res == None):
		antwort = res.text.split('<br>')
	a = 'x'
	if not (antwort == None):
		if terminalda  is True:
			print('experiment pl antwort count: ',len(antwort), 'antwort: ',antwort)
			print('experiment pl data 2: ',antwort[2])
		a = antwort[2]
	a = 'abc'
	if "200" in res.text:
		if terminalda  is True:
			print("experiment pl http 200")
	
    # need posted data here
	templateData = {
		'time': timeString,
        'pw': 'Ideur0047',

        'twi'	: twistatus,
       
        'out_startdaten' : out_startdaten,
        'out_lbdaten' : out_lbdaten,
        'out_hbdaten' : out_hbdaten,
        'out_data' : out_data,
        'outdatastring' : outdatastring,
        'pwok': pwok,
        'pw' : pw,
        'd0' : d0,
        'd1' : d1,
        'd2' : d2,
        'd3' : d3,
		'antwort' : a,
		'summe' : summe,
		'approot': APP_ROOT,
		'appstatic' : APP_STATIC,
		'pwIP' : pwIP


	}
	
		
	if (out_startdaten == 0):

		return render_template('index.html', **templateData)
		
	else:
	
		return render_template('data.html', **templateData)
	
#	requests

@app.route('/',methods=['POST', 'GET'])
def get_data():
	if terminalda  is True:
		print('Recieved from client: {}'.format(request.args))
	return Response('We recieved something')
    
 
@app.route("/data")

def data():
	global out_startdaten
	global out_data
	global in_data
	global out_lbdaten
	global out_hbdaten
	
	global in_startdaten
	global in_lbdaten
	global in_hbdaten

	now = datetime.datetime.now()
	timeString = now.strftime("%Y-%m-%d %H:%M")

	#spi_shift_out("17")
	masterok = 10
	#rep(masterok)
	
	#threading.Timer(10, callMaster).start()
	#out_data[7] = 33
	#out_lbdaten = 33
	outdatastring = ' '.join([str(x) for x in out_data])
	indatastring = ' '.join([str(x) for x in in_data])
	
	templateData = {
	'title' : 'Data',
	'time': timeString,
	'pw': 'Ideur0047',
	'd0' : out_data[0],
	'd2' : out_data[1],
	'd2' : out_data[2],
    'd3' : out_data[3],
    
    
    'out_startdaten' : int2hex(out_startdaten),
    'out_lbdaten' : int2hex(out_lbdaten),
    'out_hbdaten' : int2hex(out_hbdaten),
    'in_startdaten' : int2hex(in_startdaten),
    'in_lbdaten' : int2hex(in_lbdaten),
    'in_hbdaten' : int2hex(in_hbdaten),
	'outdatastring': outdatastring,
	'indatastring': indatastring,
	
	}
	
	return render_template('data.html', **templateData)

    
    
@app.route("/callMaster")

def callMaster():
	now = datetime.datetime.now()
	timeString = now.strftime("%Y-%m-%d %H:%M")

	#spi_shift_out("17")
	masterok = 10
	#rep(masterok)
	
	#threading.Timer(10, callMaster).start()
	
	templateData = {
	'title' : 'HELLO!',
	'time': timeString,
	'pw': 'Ideur0047',
	'd0' : out_data[0],
	'd2' : out_data[1],
	'd2' : out_data[2],
    'd3' : out_data[3],

	'out_data': out_data

	}
	
	return render_template('callMaster.html', **templateData)



if __name__ == "__main__":
	app.jinja_env.auto_reload = True
	app.config['TEMPLATES_AUTO_RELOAD'] = True
	app.run(host='0.0.0.0', port=5000, debug=True, extra_files=['infile.txt'])

