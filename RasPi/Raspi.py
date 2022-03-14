#!/usr/bin/env python3

# Raspi.py
# Sends remote sensor data (temp, humidity, pressure, etc) to
#   remote collecting systems via ISM radio messages (e.g., 433MHz band)
# Packet has 80 bits with byte format TI DD DD DD DD DD DD DD DD CC
#   where
#      T:  Type of message (4-bit nibble)
#      I:  Device ID (4-bit nibble)
#      D:  Data bytes (8 total)
#      C:  1-byte CRC8 checksum (poly 0x97, init 0)
#          See http://users.ece.cmu.edu/~koopman/crc/index.html 
# Sends 5 identical packets for each message
# Sends a new sample every 60 sec
#
#  HDTodd, 2022.02

# uses _433.py to control 433MHz RX/TX
#   which in turn uses pigpio for the actual GPIO control/timing
# See abyz.me.uk/rpi/pigpio/code/_433_py.zip
# 2022-02-01
# Public Domain

import sys
import time
import pigpio
import _433
import libcrc8 as crc

# GPIO pins on the Pi to use for transmit/receive
TX=16
RX=22
GAP=1500        #was 2000
SHORT=500      #was 1050
LONG=1000        #was 525
MSGLEN = 80    # Raspi msgs are 80 bits
MSG_RPT = 3     # Send 5 times
SLPTIME= 5      # Sleep 60 sec between beacons

# Create a byte array for the message itself & compute checksum
def make_msg(T, I, D):
  msg = bytearray([
     ( (T&0x0f)<<4 | (I&0xf) ),
     ( D[0] ),
     ( D[1] ),
     ( D[2] ),
     ( D[3] ),
     ( D[4] ),
     ( D[5] ),
     ( D[6] ),
     ( D[7] ),
     ( 0x00 ) ])
  msg[9] = crc.crc8(msg,9,0x00)
  return msg

# define optional callback for received codes.
def rx_callback(code, bits, gap, t0, t1):
   print("Received msg with {} bits (gap={} t0={} t1={})  ".format(bits, gap, t0, t1), end='')
   print("Msg code=0x ", end='')
   l = bits if (bits<=MSGLEN) else MSGLEN;
   for i in range( int( (l+7)/8 ) ):
       print('{:02x} '.format( (code>>(int ((l+7)/8)*8-i*8-8) & 0xff )), end='')
   print('')

pi = pigpio.pi() # Connect to local Pi.
rx = _433.rx(pi, gpio=RX, callback=rx_callback)
tx = _433.tx(pi, gpio=TX, bits=MSGLEN, repeats=MSG_RPT, gap=GAP, t0=SHORT, t1=LONG)

# For now, just loop forever or 'til kbd interrupt
try:
  cntr = 0
  while True:
    # Make msg with Type=0, ID=13, first data byte as counter
    cntr = cntr+1 if cntr<256 else 0
    S = bytearray( [ (cntr&0xff), 0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07] )
    msg = make_msg(0x0f, 13, S)
    if 8*len(msg) != MSGLEN:
      print('!!Message length = ', 8*len(msg), ' should be 80')
    print('Sending message: 0x', end='')
    for i in range(0,10):
      print('{:02x} '.format(msg[i]), end='')
    print('', flush=True)
    tx.send(msg)
    time.sleep(SLPTIME)
except:
  tx.cancel()      # Cancel the transmitter.
  time.sleep(5)    # Wait for anything in flight
  rx.cancel()      # Cancel the receiver.
  pi.stop()        # Disconnect from local Pi.
  quit()
  
