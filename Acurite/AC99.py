#!/usr/bin/env python3

# AC99.py
# Emulates an Acurite TX remote temp/hum sensor to confirm coding for 433MHz transmitter
# Packet has 40 bits with byte format ID ST TT HH CS
#   ID, Status, Temp (12 bits), Hum, Checksum
#   This emulator uses ID 222 (0xDE)
#   Temp 99.9 C, Hum 99%
# Resends every 60 sec
#
#  HDTodd, 2022.01

# uses _433.py to control 433MHz RX/TX
#   which in turn uses pigpio for the actual GPIO control/timing
# 2015-10-30
# Public Domain

import sys
import time
import pigpio
import _433

# GPIO pins on the Pi to use for transmit/receive
TX=23
RX=22

MSGLEN = 40    # Acurite 609 msgs are 40 bits
SLPTIME= 10    # Sleep 60 sec between beacons

# Create a byte array for the message itself & compute checksum
def make_msg(I, S, T, H):
  msg = bytearray([
     ( I&0xff ),
     ( (S&0x0f)<<4 | (T>>8)&0x0f ),
     ( T&0xff ),
     ( H&0xff ),
     ( 0x00 ) ])
  msg[4] = ( msg[0] + msg[1] + msg[2] + msg[3] ) & 0xff
  return msg

# define optional callback for received codes.
def rx_callback(code, bits, gap, t0, t1):
   print("Received msg with {} bits (gap={} t0={} t1={})  ".format(bits, gap, t0, t1), end='')
   print("Msg code=0x ", end='')
   l = bits if (bits<=MSGLEN) else MSGLEN;
   for i in range( int( (l+7)/8 ) ):
       print('{:02x} '.format( 0xff & ~(code>>(int ((l+7)/8)*8-i*8-8) & 0xff )), end='')
   print('')

pi = pigpio.pi() # Connect to local Pi.
rx = _433.rx(pi, gpio=RX, callback=rx_callback)
tx = _433.tx(pi, gpio=TX, repeats=2, gap=1500, t0=1000, t1=500)

# For now, just loop forever
cntr = 0
while (True):
   cntr = cntr+1 if cntr<256 else 0
   # Make msg with ID=222, status code 8, temp = 99.9C, humidity 99%
   msg = make_msg(cntr,8,999,99)

   print('Sending message: 0x', end='')
   for i in range(MSGLEN if (len(msg))>MSGLEN else len(msg)):
      print('{:<x} '.format(msg[i]), end='')
   print('')
   tx.send(msg)
   time.sleep(SLPTIME)

#  If we ever change conditions toexit that loop, shut things down
tx.cancel()      # Cancel the transmitter.
time.sleep(5)    # Wait for anything in flight
rx.cancel()      # Cancel the receiver.
pi.stop()        # Disconnect from local Pi.

