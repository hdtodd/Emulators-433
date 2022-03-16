#!/usr/bin/env python3
import time
import pigpio

DELAYUS = 500

p = pigpio.pi()
print("pigpio version: ", p.get_pigpio_version())

pulseTrain=[ pigpio.pulse(0, 0, DELAYUS), pulseTrain.append(pigpio.pulse(0, 0, DELAYUS)) ]

p.wave_clear()
p.wave_add_generic(pulseTrain)
pT = p.wave_create()

p.wave_send_once(pT)
t1 = p.get_current_tick()
while p.wave_tx_busy():
  pass
t2 = p.get_current_tick()

p.wave_clear()
deltaT = pigpio.tickDiff(t1, t2)
ratio = deltaT / (2*DELAYUS)
print("passed time: {} us, expected {} us => ratio {}".format(deltaT, 2*DELAYUS, ratio))

             
