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
def rx_callback(code, bits, gap, t0, t1):
   print("Received msg with {} bits (gap={} t0={} t1={})  ".format(bits, gap, t0, t1), end='')
   print("Msg code=0x ", end='')
   l = bits if (bits<=MSGLEN) else MSGLEN;
   for i in range( int( (l+7)/8 ) ):
       print('{:02x} '.format( 0xff & ~(code>>(int ((l+7)/8)*8-i*8-8) & 0xff )), end='')
   print('')
   return


# main code
pi = pigpio.pi() # Connect to local Pi.
if not pi.connected:
  print("Can't connect to piogpid.  Is it running?")
  exit()

rx = _433_AR.rx(pi, gpio=RX, callback=rx_callback)
tx = _433_AR.tx(pi,
                gpio=TX,
                repeats=REPEATS,
                pulse=PULSE,
                sync=SYNC,
                gap=GAP,
                t0=SHORT,
                t1=LONG)

print("pigpiod wave timing ratio, real:expected, = {:.2f}".format(tx.joan))

# For now, just loop forever
cntr = -1
while (True):
   cntr = cntr+1 if cntr<100 else 0
   # Make msg with ID=164, status code 2, temp = 25.0C, humidity = <cntr, 0..99>
   msg = make_msg(164,2,250,cntr)

   print('Sending message: 0x', end='')
   for i in range(MSGLEN if (len(msg))>MSGLEN else len(msg)):
      print('{:<x} '.format(msg[i]), end='')
   print('')
   tx.send(msg)
   time.sleep(SLPTIME)

#  If we ever change conditions to exit that loop, shut things down
tx.cancel()      # Cancel the transmitter.
time.sleep(5)    # Wait for anything in flight
rx.cancel()      # Cancel the receiver.
pi.stop()        # Disconnect from local Pi.
