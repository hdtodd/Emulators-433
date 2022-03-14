#!/usr/bin/env python3

# AC99.py
# Emulates an Acurite 609TX remote temp/hum sensor to confirm coding for 433MHz transmitter
# Packet has 40 bits with byte format ID ST TT HH CS
#   ID, Status, Temp (12 bits), Hum, Checksum
#   This emulator uses ID 164 (0xA4)
#   Temp 25 C, Hum <cntr>%, where <cntr> counts the packet number
# Resends every 60 sec
#
#  HDTodd, 2022.03

# uses _433_AC.py to control 433MHz RX/TX
#   which in turn uses pigpio for the actual GPIO control/timing
# 2015-10-30
# Public Domain
'''
    It turns out that pigopid interacts with hardware/software in a funny way
    that causes wave timings to vary, depending on operating environment.
    I added a calibration routine, taken from joan's work (pigpiod author)
    to calibrate actual vs programmed wave timings and then scale the
    requsted timings accordingly.  HDT
'''

import sys
import time
import pigpio
import _433_AC

#  These timings are from triq.org/pdv analysis of Acurite 609 remote samples
#    recorded with rtl_433 as .cu8 files and the converted to .ook files for analysis
#  These are the timings the Acurite monitor expects to see (approximately)
#  Scale accordingly, depending on the "joan" factor of real-to-programmed timing ratio
PULSE=    425    # pulse width; all pulses equal width
SHORT=   1006    # short gap, indicating 0 bit value
LONG=    2000    # long gap, indicating 1 bit value
SYNC=    8940    # gap after 3 sync pulses, before 1st data
GAP=    10200    # gap between repeats of packet data in transmission
REPEATS=    5    # number of times to repeat packet in transmission
MICROS=  1000    #timing for calibration

# GPIO pins on the Pi to use for transmit/receive
TX=16
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
   return

# Calibrate pigpiod timing by computing ratio of actual time to
#   programmed time for a wave chain of known length
# Taken from Joan, https://github.com/joan2937/pigpio/issues/331
def cal():
   # Use transmitter pin for calibration   
   pi.set_mode(TX, pigpio.OUTPUT)

   pi.wave_add_generic(
      [pigpio.pulse(1<<TX,     0, MICROS), 
       pigpio.pulse(    0, 1<<TX, MICROS)])
   wid = pi.wave_create()
   if wid >= 0:
      start = time.time()
      pi.wave_chain([255, 0, wid, 255, 1, 200, 0]) # send wave 200 times
      while pi.wave_tx_busy():
         time.sleep(0.001)
      duration = time.time() - start
      pi.wave_delete(wid)
   EXPECTED_SECS = 400.0 * MICROS / 1000000.0
   joan = duration / EXPECTED_SECS
   print("pigpiod wave timing ratio, real:expected, = {:.2f}".format(joan))
   return joan

# main code
pi = pigpio.pi() # Connect to local Pi.
if not pi.connected:
  print("Can't connect to piogpid.  Is it running?")
  exit()

#calibrate pigpiod timings
joan = cal()

rx = _433_AC.rx(pi, gpio=RX, callback=rx_callback)
tx = _433_AC.tx(pi,
                gpio=TX,
                repeats=REPEATS,
                pulse=int(PULSE/joan),
                sync=int(SYNC/joan),
                gap=int(GAP/joan),
                t0=int(SHORT/joan),
                t1=int(LONG/joan))

# For now, just loop forever
cntr = 0
while (True):
   cntr = cntr+1 if cntr<100 else 0
   # Make msg with ID=222, status code 8, temp = 99.9C, humidity 99%
   msg = make_msg(164,2,250,cntr)

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

