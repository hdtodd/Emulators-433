#!/usr/bin/env python
# _433_AR.py

'''
This module provides two classes to use with wireless 433MHz 
transmitters and receivers.  The tx class transmits device codes
and the rx class decodes received codes.

This customized library provides transmit & receive functions 
  specific for a 433MHz transmitter and receiver pair to emulate the
  data packets of Acurite 609 remote temp/humidity sensors.

The packet format is:
  -  constant pulse width throughout the packet
  -  3 sync pulses with pulse and gaps equal duration
  -  sync gap ("sync") following the sync pulses and before the first data bit
  -  pulse followed by gap: "short" pulse = 0, "long" pulse = 1
  -  40 data bits, each signified by a short or long gap
  -  trailing pulse after last gap (total of 44 pulses per packet)
  -  inter-packet gap (duration "gap") before next packet
  -  send the data packet "repeat" times before concluding

The transmit function allows the timings to be set as parameters,
  and a calibration function is provided to allow the calling program to
  correct for discrepancies between timing requested from the transmitter
  and timing actually seen at the receiver (known pigpio/Raspberry Pi anomaly)

  Base code was retrieved from wget abyz.me.uk/rpi/pigpio/code/_433_py.zip
    and dated 2015-10-30 and marked "Public Domain"
  Adapted by hdtodd@gmail.com, 2022.03, to mimic the Acurite 609: 
    constructed the sync pulses, gap timing, and packet length 
    to send/receive 40-bit Acurite packets
'''

# set default waveform parameters for Acurite 609 transmission timings
#  These are scaled after sending & receiving a test pulse train
#  The pigpio library timings vary depending upon system configuration,
#  So this library provides a calibration function to check
#  actual timings vs requested timings for pulses.
PULSE_WIDTH =  425
SHORT       = 1006
LONG        = 2000
SYNC        = 8940
GAP         =10200
MSGLEN      =   40
REPEATS     =    3

MICROS      =  500    #timing for calibration: 500usec high-low pulse

import time
import pigpio

"""
   rx: A class to read wireless codes transmitted by 433 MHz transmitter
"""
class rx():
   def __init__(self, pi, gpio, callback=None,
                      min_bits=8, max_bits=40, glitch=150):
      """
      Instantiate with the Pi and the GPIO connected to the wireless
      receiver.

      If specified the callback will be called whenever a new code
      is received.  The callback will be passed the code, the number
      of bits, the length (in us) of the gap, short pulse, and long
      pulse.

      Codes with bit lengths outside the range min_bits to max_bits
      will be ignored.

      A glitch filter will be used to remove edges shorter than
      glitch us long from the wireless stream.  This is intended
      to remove the bulk of radio noise.
      """
      self.pi = pi
      self.gpio = gpio
      self.cb = callback
      self.min_bits = min_bits
      self.max_bits = max_bits
      self.glitch = glitch

      self._in_code = False
      self._edge = 0
      self._code = 0
      self._gap = 0

      self._ready = False

      pi.set_mode(gpio, pigpio.INPUT)
      pi.set_glitch_filter(gpio, glitch)
      pi.set_pull_up_down(gpio, pigpio.PUD_DOWN)
      
      self._last_edge_tick = pi.get_current_tick()
      self._cb = pi.callback(gpio, pigpio.EITHER_EDGE, self._cbf)

   def _timings(self, e0, e1):
      """
      Accumulates the short and long pulse length so that an
      average short/long pulse length can be calculated. The
      figures may be used to tune the transimission settings.
      """
      if e0 < e1:
         shorter = e0
         longer = e1
      else:
         shorter = e1
         longer = e0

      if self._bits:
         self._t0 += shorter
         self._t1 += longer
      else:
         self._t0 = shorter
         self._t1 = longer

      self._bits += 1

   def _calibrate(self, e0, e1):
      """
      The first pair of pulses is used as the template for
      subsequent pulses.  They should be one short, one long, not
      necessarily in that order.  The ratio between long and short
      should really be 2 or more.  If less than 1.5 the pulses are
      assumed to be noise.
      """
      self._bits = 0
      self._timings(e0, e1)
      self._bits = 0

      ratio = float(self._t1)/float(self._t0)

      if ratio < 1.5:
         self._in_code = False

      slack0 = int(0.3 * self._t0)
      slack1 = int(0.2 * self._t1)

      self._min_0 = self._t0 - slack0
      self._max_0 = self._t0 + slack0
      self._min_1 = self._t1 - slack1
      self._max_1 = self._t1 + slack1

   def _test_bit(self, e0, e1):
      """
      Returns the bit value represented by the sequence of pulses.

      0: short long
      1: long short
      2: illegal sequence
      """
      self._timings(e0, e1)

      if   ( (self._min_0 < e0 < self._max_0) and
             (self._min_1 < e1 < self._max_1) ):
         return 0
      elif ( (self._min_0 < e1 < self._max_0) and
             (self._min_1 < e0 < self._max_1) ):
         return 1
      else:
         return 2

   def _cbf(self, g, l, t):
      """
      Accumulates the code from pairs of short/long pulses.
      The code end is assumed when an edge greater than 5 ms
      is detected.
      """
      edge_len = pigpio.tickDiff(self._last_edge_tick, t)
      self._last_edge_tick = t

      if edge_len > 2750: # 5000 us, 5 ms.

         if self._in_code:
            if self.min_bits <= self._bits <= self.max_bits:
               self._lbits = self._bits
               self._lcode = self._code
               self._lgap = self._gap
               self._lt0 = int(self._t0/self._bits)
               self._lt1 = int(self._t1/self._bits)
               self._ready = True
               if self.cb is not None:
                  self.cb(self._lcode, self._lbits,
                          self._lgap, self._lt0, self._lt1)

         self._in_code = True
         self._gap = edge_len
         self._edge = 0
         self._bits = 0
         self._code = 0

      elif self._in_code:

         if self._edge == 0:
            self._e0 = edge_len
         elif self._edge == 1:
            self._calibrate(self._e0, edge_len)

         if self._edge % 2: # Odd edge.

            bit = self._test_bit(self._even_edge_len, edge_len)
            self._code = self._code << 1
            if bit == 1:
               self._code += 1
            elif bit != 0:
               self._in_code = False

         else: # Even edge.

            self._even_edge_len = edge_len

         self._edge += 1

   def ready(self):
      """
      Returns True if a new code is ready.
      """
      return self._ready

   def code(self):
      """
      Returns the last received code.
      """
      self._ready = False
      return self._lcode

   def details(self):
      """
      Returns details of the last received code.  The details
      consist of the code, the number of bits, the length (in us)
      of the gap, short pulse, and long pulse.
      """
      self._ready = False
      return self._lcode, self._lbits, self._lgap, self._lt0, self._lt1

   def cancel(self):
      """
      Cancels the wireless code receiver.
      """
      if self._cb is not None:
         self.pi.set_glitch_filter(self.gpio, 0) # Remove glitch filter.
         self._cb.cancel()
         self._cb = None

"""
   tx: A class to transmit the wireless codes sent by 433 MHz wireless fobs.
   [HDT] modified for PPM: constant pulse width, variable inter-pulse gaps (marks)
"""
class tx():
   def __init__(self, pi, gpio, pulse=PULSE_WIDTH,repeats=REPEATS, bits=MSGLEN, gap=GAP,
                t0=SHORT, t1=LONG, sync=SYNC):
      """
      Instantiate with the Pi and the GPIO connected to the wireless
      transmitter on pin "gpio".

      The packet format is:
         -  constant pulse width throughout the packet
         -  3 sync pulses with pulse and gaps of equal duration after first two
         -  sync gap ("sync") following the third sync pulse and before the first data bit
         -  data bit pulse followed by gap: "short" gap = 0, "long" gap = 1
         -  trailing pulse terminates the last gap
         -  inter-packet gap (duration "gap") before next packet
         -  send the data packet "repeat" times before concluding transmission

      The number of repeats (default REPEATS) and bits (default MSGLEN) may
      be set.

      The delay between sync pulses and first data bits (default SYNC us), 
      inter-packet gap (default GAP us), short mark length (default SHORT us), 
      and long mark length (default LONG us) may be set as parameters.

      Calibrate pigpiod timing by computing ratio of actual time to
        programmed time for a wave chain of known length
      Taken from Joan, https://github.com/joan2937/pigpio/issues/331
      """
      
      # Calibrate timings (requested-to-actual) using transmitter pin

      pi.set_mode(gpio, pigpio.OUTPUT)

      #create a pulse train of known duration for timing
      pi.wave_add_generic(
        [pigpio.pulse(1<<gpio,       0, MICROS), 
         pigpio.pulse(      0, 1<<gpio, MICROS)])
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

      # set our parameters; scale timings per "joan" ratio of actual-to-expected timings
      self.pi = pi
      self.gpio = gpio
      self.repeats = repeats
      self.bits = bits
      self.joan = joan
      self.gap = int(gap/joan)
      self.t0 = int(t0/joan)
      self.t1 = int(t1/joan)
      self.pulse = int(pulse/joan)
      self.sync = int(sync/joan)
      
      self._make_waves()

      pi.set_mode(gpio, pigpio.OUTPUT)
      pi.set_pull_up_down(gpio, pigpio.PUD_DOWN)
      
   """
   Generates the basic waveforms needed to transmit codes.
   """
   def _make_waves(self):

      # Pre-amble Sync has 3 pulses with a sync gap after the third
      wf = []
      wf.append(pigpio.pulse(1<<self.gpio, 0, self.pulse))
      wf.append(pigpio.pulse(0, 1<<self.gpio, self.pulse))
      wf.append(pigpio.pulse(1<<self.gpio, 0, self.pulse))
      wf.append(pigpio.pulse(0, 1<<self.gpio, self.pulse))
      wf.append(pigpio.pulse(1<<self.gpio, 0, self.pulse))
      wf.append(pigpio.pulse(0, 1<<self.gpio, self.sync))
      self.pi.wave_add_generic(wf)
      self._amble = self.pi.wave_create()

      # Post-amble is a pulse followed by an inter-packet gap
      wf = []
      wf.append(pigpio.pulse(1<<self.gpio, 0, self.pulse))
      wf.append(pigpio.pulse(0, 1<<self.gpio, self.gap))
      self.pi.wave_add_generic(wf)
      self._post = self.pi.wave_create()
      
      
      # "0" is a pulse followed by a short gap
      wf = []
      wf.append(pigpio.pulse(1<<self.gpio, 0, self.pulse))
      wf.append(pigpio.pulse(0, 1<<self.gpio, self.t0))
      self.pi.wave_add_generic(wf)
      self._wid0 = self.pi.wave_create()

      # "1" is a pulse follwed by a long gap
      wf = []
      wf.append(pigpio.pulse(1<<self.gpio, 0, self.pulse))
      wf.append(pigpio.pulse(0, 1<<self.gpio, self.t1))
      self.pi.wave_add_generic(wf)
      self._wid1 = self.pi.wave_create()

   def set_repeats(self, repeats):
#      Set the number of code repeats.
      if 1 < repeats < 100:
         self.repeats = repeats

   def set_bits(self, bits):
#      Set the number of code bits.
      if 5 < bits < 65:
         self.bits = bits

   def set_timings(self, gap, t0, t1):
#     Sets the code gap, short pulse, and long pulse length in us.
      self.gap = gap
      self.t0 = t0
      self.t1 = t1

      self.pi.wave_delete(self._amble)
      self.pi.wave_delete(self._wid0)
      self.pi.wave_delete(self._wid1)

      self._make_waves()

   def send(self, code):
      """
      Transmits the code (using the current settings of repeats,
      bits, gap, short, and long pulse length).
      """
      chain = [255,0]

      #  Pre-amble of sync pulses & gap
      chain += [self._amble]

      #  Now the data bits
      bs=""
      bit = (1<<(self.bits-1))
      for i in range(self.bits):
         bit = (1<<(7-i%8))
         if code[int(i/8)] & bit:
            chain += [self._wid1]
            bs += "1"
         else:
            chain += [self._wid0]
            bs += "0"
         bit = bit >> 1

      #[HDT] And finish with the terminal pulse and inter-packet gap
      chain += [self._post]

      #  Repeat packet transmission specified # of times
      chain += [255, 1, self.repeats, 0]

      print("Sending bit string of ",  self.bits, " bits:")
      print("\t", bs)
      print("Wave chain:")
      print(chain)
      
      self.pi.wave_chain(chain)

      while self.pi.wave_tx_busy():
         time.sleep(0.1)

   def cancel(self):
      """
      Cancels the wireless code transmitter.
      """
      self.pi.wave_delete(self._amble)
      self.pi.wave_delete(self._wid0)
      self.pi.wave_delete(self._wid1)
      self.pi.wave_delete(self._post)
