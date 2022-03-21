#! /usr/bin/python3
# RXA609.py -- Testing program for the rx class of the Acurite 609TX 433MHz library

'''
This program reads the pulses from a PulseView .ook file (converted from .cu8 by rtl_433)
to simulate the pulse stream that would be received from an Acurite 609TX remote
temp/humidity sensor on the 433MHz ISM band.

It passes those pulses to the rx-class for analysis and validation as an
Acurite 609 data transmission, and that class returns the bit-string represented
by the transmission

An Acurite data packet has 40 bits with byte format ID ST TT HH CS
  ID, Status, Temp (12 bits), Hum, Checksum
  This emulator uses ID 164 (0xA4)
  Temp 25 C, Hum <cntr>%, where <cntr> counts the packet number
The remote sensor sends the same packet multiple times (generally 5, it appears)
as a single transmission, with timed gaps between packets.

Written by HDTodd@gmail.com, 2022.03 and adapted from base code 
retrieved from wget abyz.me.uk/rpi/pigpio/code/_433_py.zip
2015-10-30
Public Domain
'''

import sys
import time
import pigpio
import _433_AR

#  These timings are from triq.org/pdv analysis of Acurite 609 remote samples
#    recorded with rtl_433 as .cu8 files and the converted to .ook files for analysis
#  These are the timings the Acurite monitor expects to see (approximately)
#  These are scaled in _433_AR depending on the "joan" factor of real-to-programmed timing ratio
#    as the pulses are generated and then received by pigpio.  See reference above.

PULSE=    425    # pulse width; all pulses equal width
SHORT=   1006    # short gap, indicating 0 bit value
LONG=    2000    # long gap, indicating 1 bit value
SYNC=    8940    # gap after 3 sync pulses, before 1st data
GAP=    10200    # gap between repeats of packet data in transmission
REPEATS=    5    # number of times to repeat packet in transmission

# GPIO pins on the Pi to use for transmit/receive
TX=16
RX=22

MSGLEN = 40    # Acurite 609 msgs are 40 bits
SLPTIME= 10    # Sleep 10 sec between beacons

# define optional callback for received codes to report recognized codes received
def rx_callback(code, bits, pulse=0, short=0, longi=0):
   print("Received msg with {} bits (pulse={} short={} long={})  ".format(bits, pulsei, shorti, longi), end='')
   print("Msg code=0x ", end='')
   l = bits if (bits<=MSGLEN) else MSGLEN;
   for i in range( int( (l+7)/8 ) ):
       print('{:02x} '.format( 0xff & ~(code>>(int ((l+7)/8)*8-i*8-8) & 0xff )), end='')
   print('')
   return

# main code

# instantiate receiver & set callback for received packet
#rx = _433_AR.rx(pi, gpio=RX, callback=rx_callback)

# For now, just loop forever
cntr = -1
while (True):
   # Make msg with ID=164, status code 2, temp = 25.0C, humidity = <cntr, 0..99>
   cntr = (cntr+1)%100
   msg = make_msg(164,2,250,cntr)

   print('Sending message: 0x', end='')
   for i in range(MSGLEN if (len(msg))>MSGLEN else len(msg)):
      print('{:<x} '.format(msg[i]), end='')
   print('')
   tx.send(msg)
   time.sleep(SLPTIME)

#  If we ever change conditions to exit that loop, shut things down
rx.cancel()      # Cancel the receiver.
