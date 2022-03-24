#!/usr/bin/env python3
# AR609.py

'''
Emulates an Acurite 609TX remote temp/hum sensor to confirm coding for 433MHz transmitter
Packet has 40 bits with byte format ID ST TT HH CS
  ID, Status, Temp (12 bits), Hum, Checksum
  This emulator uses ID 164 (0xA4)
  Temp 25 C, Hum <cntr>%, where <cntr> counts the packet number
Resends "REPEATS" packets every "SLPTIME" seconds

Adapted by HDTodd, 2022.03
Uses _433_AR.py to control 433MHz RX/TX
  which in turn uses pigpio for the actual GPIO control/timing
2015-10-30
Public Domain

It turns out that pigopid interacts with hardware/software 
that causes actual wave timings to differ from that requested, 
depending on operating environment (X11 running, at least)
I added a calibration routine, taken from joan's work (pigpiod author),
to calibrate actual vs programmed wave timings and then scale the
requsted transmit timings accordingly.  
See thread at  https://github.com/joan2937/pigpio/issues/331
HDT
'''

import sys
import time
import pigpio
import _433_AR
import math

# GPIO pins on the Pi to use for transmit/receive
TX=16
RX=22

CSIRED = "\033[31m"
CSIBLK = "\033[30m"
CSIBLU = "\033[34m"

#  These timings are from triq.org/pdv analysis of Acurite 609 remote samples
#    recorded with rtl_433 as .cu8 files and the converted to .ook files for analysis
#  These are the timings the Acurite monitor expects to see (approximately)
#  These are scaled in _433_AR depending on the "joan" factor of real-to-programmed timing ratio
#    as the pulses are generated and then received by pigpio.  See reference above.

SYNC_GAP =   475       #interval between sync pulses
PULSE    =   505       #pulses are this duration, +/- 5%
SHORT    =  1006       #interval after pulse to indicate data bit "0"
LONG     =  2000       #interval after pulse to indicate data bit "1"
SYNC     =  8940       #interval after third sync pulse, before first data
GAP      = 10200       #interval after pulse that terminates last data bit                                      

REPEATS  =     5       # number of times to repeat packet in transmission

MSGLEN   =    40       # Acurite 609 msgs are 40 bits
SLPTIME  =    10       # Sleep 10 sec between beacons

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

# define optional callback for received codes to report recognized codes received
def rx_callback(code, bits):
   global rxcalls
   print("\nFrom callback: Received msg with ", bits, " bits, ", end="")
   print("Code = 0x{:X} = 0b{:40b} ==> ".format(code, code), end="")
   b = code.to_bytes(5,'big')
   i = b[0]
   s = b[1]>>4
   t1 = ( b[1]&0x0f )<<8
   t2 = b[2]
   t = (t1+t2)/10.0
   h = b[3]
   print("\tID=%d, s=%d, t=%5.1f, h=%d" % (i,s,t,h))
   metric = rx.m._metrics()
   print(metric)
          
# main code
pi = pigpio.pi() # Connect to local Pi.
if not pi.connected:
  print("Can't connect to piogpid.  Is it running?")
  sys.exit(0)

rx = _433_AR.rx(pi, gpio=RX, valid_pkt_callback=rx_callback)
tx = _433_AR.tx(pi,
                gpio=TX,
                repeats=REPEATS,
                pulse=PULSE,
                sync=SYNC,
                gap=GAP,
                t0=SHORT,
                t1=LONG)

print("pigpiod wave timing ratio, real:expected, = {:.2f}".format(tx.joan))

# For now, just loop 'til CNTL-C
cntr = -1
try:
   while (True):
      cntr += 1
      cntr %= 100
      # Make msg with ID=164, status code 2, temp = 25.0C, humidity = <cntr, 0..99>
      msg = make_msg(164,2,250,cntr)
      print(CSIBLU,'\nSending message: 0x', end='')
      for i in range(MSGLEN if (len(msg))>MSGLEN else len(msg)):
         print('{:>02X} '.format(msg[i]), end='')
      print(CSIBLK, " ==> ", end="")
      tx.send(msg)
      time.sleep(SLPTIME)
except KeyboardInterrupt:
   stats = rx.m._stats()
   print(CSIRED,"\nOverall statistics\n   ",stats,CSIBLK)

#  If we ever change conditions to exit that loop, shut things down
tx.cancel()      # Cancel the transmitter.
rx.cancel()      # Cancel the receiver.
pi.stop()        # Disconnect from local Pi.
sys.exit(0)
