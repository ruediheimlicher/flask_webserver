# /tasks/spi_task.py
from flask import Blueprint, render_template
import RPi.GPIO as GPIO 
from time import sleep
from ctypes import c_uint8
from array import array
from time import time

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

spi_delay = 0.001

delay20 = sleep(0.00002)
delay_pulse = sleep(0.000005)

spi_task = Blueprint('spi_task', __name__)

def spi_shift_out_byte(out_data):
	in_byte=0
	# atoi war notwendig wenn der Array mit append gefuellt wurde
	#out_byte = pi_atoi(out_data)
#	out_byte = int(out_data,16)
	out_byte = out_data
	sleep(spi_delay)

	for pos in range(0,8):

		sleep(spi_delay)
		
		# Vorbereiten: Master legt Data auf MOSI
		if (out_byte & 0x80):
			# this bit is high 
			GPIO.output(soft_MOSI, GPIO.HIGH) # MOSI HI 
	
		else:
	
			# this bit is low 
			GPIO.output(soft_MOSI, GPIO.LOW) # MOSI LO						
		delay_pulse
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
	#GPIO.output(soft_CS, GPIO.HIGH)
	return in_byte


def shift_master(hbyte, lbyte, out_data, in_data):
	
	
	GPIO.output(soft_CS, GPIO.LOW)
	
	for zeile in out_data:
		summe += zeile
		if not zeile is None:
			in_zeile = spi_shift_out(zeile)
			in_data.append(in_zeile)
			
		display_in_data[shiftindex] = str(in_zeile)
		shiftindex = shiftindex + 1
		sleep(0.05)
	GPIO.output(soft_CS, GPIO.HIGH)
	
	
	return 0
