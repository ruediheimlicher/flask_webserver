''' Code created by Matt Richardson for details, visit: 
http://mattrichardson.com/Raspberry-Pi-Flask/inde... ''' 

import threading

import requests
import RPi.GPIO as GPIO 
from flask import Flask, render_template, request, Blueprint
from time import sleep
from ctypes import c_uint8
from array import array
from time import time
from os import environ

#from apcheduler.scheduler import Scheduler

# https://stackoverflow.com/questions/33837717/systemerror-parent-module-not-loaded-cannot-perform-relative-import
from tasks.spi_task import spi_task

import datetime
app = Flask(__name__)

app.register_blueprint(spi_task)

delay_pulse = sleep(0.0000001)

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

spi_delay = 0.0001


# soft_SPI	
hbyte = 0
lbyte = 0
status = 0

BUFFERSIZE = 8

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
in_data = [0 for i in range(BUFFERSIZE)]


GPIO.setup(soft_MOSI, GPIO.OUT)

GPIO.setup(soft_MISO, GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(soft_CS, GPIO.OUT)
GPIO.setup(soft_SCK, GPIO.OUT)

GPIO.output(soft_SCK, GPIO.HIGH)
GPIO.output(soft_MOSI, GPIO.HIGH)
GPIO.output(soft_CS, GPIO.HIGH)



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
	return '%x' % zahl

def pi_atoi(astr):

    num = 0
    for c in astr:
        if '0' <= c <= '9':
            num  = num * 10 + ord(c) - ord('0')
        else:
            raise ValueError('atoi argument (%s) contains non-digit(s)' % astr)
    return num


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
			in_byte |= (1<<(7-pos));
		else:
			in_byte &= ~(1<<(7-pos));
		sleep(spi_delay)
		# Vorgang beendet: Takt HI, Data ist in in_byte 
	
		GPIO.output(soft_SCK, GPIO.HIGH) # SCK LO
		GPIO.output(soft_MOSI, GPIO.HIGH)
		sleep(spi_delay)
	
		out_byte = out_byte << 1;									#	Byte um eine Stelle nach links
	return in_byte

def spi_shift_data():
	GPIO.output(soft_CS, GPIO.LOW) # CS lo
	delay_pulse
	in_startdaten = spi_shift_out_byte(out_startdaten)

	delay_pulse
	in_lbdaten = spi_shift_out_byte(out_lbdaten)
	delay_pulse
	in_hbdaten = spi_shift_out_byte(out_hbdaten)
	delay_pulse
	summe = 0
	for index in  (0,BUFFERSIZE-1):
		summe += out_data[index]
		in_data[index] = spi_shift_out_byte(out_data[index])
		delay_pulse
	GPIO.output(soft_CS, GPIO.HIGH)# cs hi
	return summe


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
		'title' : 'GPIO output Status!',
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
        'pw': 'Ideur0047',
        'd1' :  0,
        'd2' : 0,
        'buttontitle' : 'GPIO Input',
        'button'  : buttonSts,
        'senPIR'  : senPIRSts


	}
	
	
	return render_template('data.html', **templateData)
	
@app.route('/twi', methods=['GET', 'POST'])
def parse_request():

	now = datetime.datetime.now()
	timeString = now.strftime("%Y-%m-%d %H:%M")

	data = request.args.get('twi')  # 
	twistatus = request.args.get('twi')
	pw =  request.args.get('pw')
	
#	in_data = []
#	out_data = []
	dataindex=0
	
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
	
	count = len(out_data)
	
	# spi out
	summe = 0
	shiftindex=0
	
	summe = spi_shift_data()
	
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
	
	res = requests.get("http://www.ruediheimlicher.ch/Data/TimePrefs.txt")
	if not (res.text == None):
		print('TimePrefs: ',res.text)
	
	res = requests.get("http://www.ruediheimlicher.ch/cgi-bin/experiment.pl?d0=27")
	if not (res == None):
		antwort = res.text.split('<br>')
	a = 'x'
	if not (antwort == None):
		print('experiment pl antwort count: ',len(antwort), 'antwort: ',antwort)
		print('experiment pl data 2: ',antwort[2])
		a = antwort[2]
	a = 'abc'
	if "200" in res.text:
		print("experiment pl http 200")
	
    # need posted data here
	templateData = {
		'time': timeString,
        'pw': 'Ideur0047',

        'twi'	: twistatus,
        'pw' : pw,
        'd0' : d0,
        'd1' : d1,
        'd2' : d2,
        'd3' : d3,
		'antwort' : a

	}

	return render_template('index.html', **templateData)

#	requests

@app.route('/',methods=['POST', 'GET'])
def get_data():
    print('Recieved from client: {}'.format(request.args))
    return Response('We recieved something')
    
 
@app.route("/data")

def data():
	now = datetime.datetime.now()
	timeString = now.strftime("%Y-%m-%d %H:%M")

	#spi_shift_out("17")
	masterok = 10
	#rep(masterok)
	
	#threading.Timer(10, callMaster).start()
	
	templateData = {
	'title' : 'Data',
	'time': timeString,
	'pw': 'Ideur0047',
	'd0' : out_data[0],
	'd2' : out_data[1],
	'd2' : out_data[2],
    'd3' : out_data[3],

	'out_data': out_data

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
   app.run(host='0.0.0.0', port=5000, debug=True)

