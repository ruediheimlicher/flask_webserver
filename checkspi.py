#!/usr/bin/python3

from time import sleep
 
SPIDEV = '/dev/spidev0.0'
ADDRESS = 0x40
DELAY = 0.1

def write(DEV, Addr, Register, Byte):
#       SPI-Device, Adresse, Register, Daten
  handle = open(DEV, 'w+')
  try:
    data = chr(Addr)+chr(Register)+chr(Byte)
    handle.write(data)
    handle.close
    return True
  except:
    print("Error writing to SPI Bus")
    return False
  
 
# MCP23S17-Register GPIOB auf Output schalten
write(SPIDEV,ADDRESS,0x01,0x00)
while True:
  write(SPIDEV,ADDRESS,0x13,0xff)
  sleep(DELAY)
  write(SPIDEV,ADDRESS,0x13,0)
  sleep(DELAY)

