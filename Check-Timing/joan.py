#!/usr/bin/env python

import time
import pigpio

GPIO=4
MICROS=1000

pi = pigpio.pi()
if not pi.connected:
   exit()

pi.set_mode(GPIO, pigpio.OUTPUT)

pi.wave_add_generic(
   [pigpio.pulse(1<<GPIO,       0, MICROS), 
    pigpio.pulse(      0, 1<<GPIO, MICROS)])
wid = pi.wave_create()
if wid >= 0:
   start = time.time()
   pi.wave_chain([255, 0, wid, 255, 1, 200, 0]) # send wave 200 times
   while pi.wave_tx_busy():
      time.sleep(0.001)
   duration = time.time() - start
   pi.wave_delete(wid)
pi.stop()

EXPECTED_SECS = 400.0 * MICROS / 1000000.0

ratio = duration / EXPECTED_SECS

print("{:.2f}".format(ratio))

