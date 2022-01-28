#!/usr/bin/env python3

# Mav.py
# Emulates an Maverick remote temp/hum sensor to confirm coding for 433MHz transmitter
# Packet has 48 bits with byte format II 11 12 22 xx xx
#   ID, Temp1, Temp2 (12 bits), unk, unk
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

MSGLEN = 48    # Mav msgs are 48 bits
SLPTIME= 5    # Sleep 60 sec between beacons

# Create a byte array for the message itself & compute checksum
def make_msg(I, T1, T2):
  t1 = int(T1*10.0)
  t2 = int(T2*10.0)
  msg = bytearray([
     ( I&0xff ),
     ( t1&0xff0 )>>4,
     ( t1&0x00f )<<4 | (t2&0xf00)>>8,
     ( t2&0x0ff ),
     ( 0xAA ),
     ( 0xAA ) ])
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
tx = _433.tx(pi, gpio=TX, bits=48, repeats=4, gap=2000, t0=1050, t1=525)

# For now, just loop forever or 'til kbd interrupt
try:
  cntr = 0
  while True:
    # Make msg with ID=<sequential counter>, Temp1=20C, Tem2=100C
    cntr = cntr+1 if cntr<256 else 0
    msg = make_msg(cntr, 20., -20.1)
    print('Sending message: 0x', end='')
    for i in range(MSGLEN if (len(msg))>MSGLEN else len(msg)):
      print('{:<x} '.format(msg[i]), end='')
    print('', flush=True)
    tx.send(msg)
    time.sleep(SLPTIME)
except KeyboardInterrupt:
  tx.cancel()      # Cancel the transmitter.
  time.sleep(5)    # Wait for anything in flight
  rx.cancel()      # Cancel the receiver.
  pi.stop()        # Disconnect from local Pi.

