#!/usr/local/bin/python3.10
# _433_AR.py

#Version 1: uses lists rather than classes

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

import time
import pigpio

# machine states
SYNC_WAIT    = 0
DATA_COLLECT = 1
PKT_GAP_WAIT = 2
States = ["SYNC_WAIT", "DATA_COLLECT", "PKT_GAP_WAIT"]

# interval types
SYNC_GAP = 0
PULSE    = 1
SHORT    = 2
LONG     = 3
SYNC     = 4
GAP      = 5
Intervals = ["SYNC_GAP", "PULSE", "SHORT", "LONG", "SYNC", "GAP"]

# set default waveform parameters for Acurite 609 transmission timings
#  These are scaled after sending & receiving a test pulse train
#  The pigpio library timings vary depending upon system configuration,
#  So this library provides a calibration function to check
#  actual timings vs requested timings for pulses.
Timing_Table = [
   [SYNC_GAP  , "SYNC_GAP",  475, 0, 0],       #interval between sync pulses
   [PULSE     , "PULSE"   ,  505, 0, 0],       #pulses are this duration, +/- TOLERANCE
   [SHORT     , "SHORT"   , 1006, 0, 0],       #interval after pulse to indicate data bit "0"
   [LONG      , "LONG"    , 2000, 0, 0],       #interval after pulse to indicate data bit "1"
   [SYNC      , "SYNC"    , 8240, 0, 0], #8940      #interval after third sync pulse, before first data
   [GAP       , "GAP"     ,10200, 0, 0]        #interval after pulse that terminates last data bit
   ]

MSGLEN      =   40
REPEATS     =    3

#IMPORTANT TO CHECK 433MHz receiver output to see if "on" is 0v0 or 3v3;
#  Trailing should be set to 1 if pulses are 3v3-->0v0 (inverted)
TRAILING    =    1           #Set to 0 if pulse voltages are 0->1 or to 1 if they're 1->0 
MICROS      =  500           #Timing for calibration: 500usec high-low pulse

TOLERANCE   =   17           #Timing tolerance for edge classification (as %)

#This is the state-machine recognizer for Acurite PPM packets
#Its _next() function  accepts a token that indicates the type of
#  "edge" of length "interval" microsec just received
#  and advances the machine state, depending on current state and token type
class mach():
   def __init__(self,callback=None):
      self.cb = callback
      self._reset()
      
   def _reset(self):
      self.state = SYNC_WAIT
      self.sync_count = 0
      self.bit_count  = 0
      self.code       = 0
      self.pulseavg   = 0
      self.pulsecnt   = 0
      self.shortavg   = 0
      self.shortcnt   = 0
      self.longavg    = 0
      self.longcnt    = 0
      self.need_pulse = True
      
   def _next(self,token,interval=1):
      #first, accumulate metrics for possible analysis
      if token == PULSE:
         self.pulseavg += interval
         self.pulsecnt += 1
         if not self.need_pulse:    #two pulses in a row?  No way.
            self._reset()
            return
         self.need_pulse = False
         return
      elif token == SHORT:
         self.shortavg += interval
         self.shortcnt += 1
      else:
         self.longavg  += interval
         self.longcnt  += 1

      if self.need_pulse:
#         print("got an interval when we expected a pulse; reset")
         self._reset()
         return

      #now evaluate state change: we have just a small number of valid transitions
      if ( self.state == SYNC_WAIT and token == SYNC_GAP ):
         self.sync_count += 1
#         print("Checking SYNC_WAIT and SYNC_GAP; sync_count = ", self.sync_count)
         if self.sync_count >=3:
            #should be 2 pulse+sync-gaps then 1 pulse+sync-interval
            #  so 3 pulst+sync-gaps isn't our patern: reset machine
            self._reset()
         self.need_pulse = True
         return

      if ( self.state == SYNC_WAIT and token == SYNC ):
         if self.sync_count==2:
            #We've seen two sync pulse/gap pairs, and now a pulse/SYNC interval
            # So sync pattern is complete: go into data collect mode
            self.state = DATA_COLLECT
            self.sync_count==0
         else:
            #should have been 2 SYNC_GAPS followed by SYNC interval
            #  so <2 SYNC_GAPS followed by SYNC isn't our pattern: reset
            self._reset()
         self.need_pulse = True
         return
         
      if ( self.state == DATA_COLLECT and token == GAP ):
         print("DATA_COLLECT + GAP with bit_count = ", self.bit_count)
         if self.bit_count==MSGLEN:
            #This is a valid packet.  Send result back to caller and reset for next
            self.cb(self.code, self.bit_count,
                    int(self.pulseavg/self.pulsecnt),
                    int(self.shortavg/self.shortcnt),
                    int(self.longavg/self.longcnt))
         else:
            print("SYNC OK; data collected != 40 bits, so packet not valid; ignore packet")
         #and reset machine in any case
         self._reset()
         return
      
      if ( self.state == DATA_COLLECT and token == SHORT) or ( self.state == DATA_COLLECT and token == LONG):
         #This is a data bit, so record it
         self.bit_count += 1
         self.code <<= 1                   #make room for next bit
         self.code += 1 if token == LONG else 0
         self.need_pulse = True
         return
         
      #by default, all other cases reset recognition machine
      self._reset()
      return
   
   def _get_state(self):
      return self.state, self.sync_count, self.bit_count, self.code


#   rx: A class to read wireless codes transmitted by 433 MHz transmitter
class rx():
   def __init__(self, pi, gpio, valid_pkt_callback=None, glitch=150):
      """
      Instantiate with the Pi and the GPIO connected to the wireless
      receiver on the pin specified by "gpio"

      If specified the callback will be called whenever a new code
      is received.  The callback will be passed the code, the number
      of bits, the length (in us) of the gap, short pulse, and long
      pulse.

      A glitch filter will be used to remove edges shorter than
      "glitch" us long from the wireless stream.  This is intended
      to remove the bulk of radio noise.
      """
      #instantiate the recognition machine and record the valid-packet callback
      self.m = mach(callback=valid_pkt_callback)
      self.pi = pi
      self.gpio = gpio
      self.glitch = glitch

      for e in Timing_Table:
         e[3] = int(e[2]*(1.0-TOLERANCE/100.))          #set low-bound for this interval type
         e[4] = int(e[2]*(1.0+TOLERANCE/100.))          #set high-bound for this interval type
#         print(e)
         
      pi.set_mode(gpio, pigpio.INPUT)
      pi.set_glitch_filter(gpio, glitch)
      pi.set_pull_up_down(gpio, pigpio.PUD_DOWN)
      
      self._tick_count = 0
      self._last_edge_tick = -1
      self._cb = pi.callback(gpio, pigpio.EITHER_EDGE, self._cbf)
      
   def _class_edge(self,e):
      for t in Timing_Table:
         if t[3] <= e <= t[4]:
            return t[0]
      return None

   def _cbf(self, gpio, level, tick):
      """
      Recognizer for PPM codes received from 433MHz receivers.

      Accumulates the data packet bit code from pulse-interval pairs, with constant pulse
      durations and with the interval length determining the value of the bit represented.  

      Edges are defined by rising and trailing edges of the electrical pulses.
      An "edge" that is the plateau is the pulse; the valley "edge" that follows is
      its interval.

      The edge length, "edge_len", can be time, in microseconds, of the
      duration of either the pulse or the inter-pulse interval. 
      We only know that it's an edge.  We assume that the first edge seen is a
      pulse (plateau defined by a rising electrical edge followed by its 
      trailing falling electrical edge. The interval that follows the pulse is 
      defined by that falling edge and the rising edge of the next electrical pulse. 

      The first two sync bits have lengths (PULSE,INTERVAL)) followed by the third
      sync bit (PULSE,SYNC).  After that, we should see (PULSE,SHORT) to
      represent a "0" data bit or (PULSE,LONG) to represent a "1" data bit.  
      The 40th bit is terminated by (PULSE,GAP) to signal the end of that packet.

      The start of packet is recognized by a sync preamble of 3 pulses.
      The end of packet is recognized when the 40th bit has been received and the gap
      that follows is at least GAP usec long.

      In short, the packet format is:
         -  constant pulse width throughout the packet
         -  3 sync pulses with intervals of nearly-equal duration after first two pulses
         -  sync interval ("sync") following the third sync pulse and before the first data bit
         -  data bit pulse followed by an interval: "short" gap = 0, "long" gap = 1
         -  trailing pulse terminates the last data-bit interval
         -  inter-packet interval (duration of at least GAP usec) before next packet
         -  transmitter sends the data packet "repeat" times before concluding transmission
      """

      # every other rising/falling edge triggers an analysis of the interval length
#      if gpio != self.gpio:
#         return
      edge_len = pigpio.tickDiff(self._last_edge_tick, tick)
      self._last_edge_tick = tick
      if self._last_edge_tick < 0:
         self._last_edge_tick = tick
         return
      if level == 2 or edge_len > 11000:          # watchdog timer
         edge_type = GAP
         self.pi.set_watchdog(self.gpio,0)
      elif level == TRAILING:                     # falling edge --> just saw pulse
         edge_type = PULSE
      else: 
         edge_type = self._class_edge(edge_len)
      if self.m.bit_count == MSGLEN:
         self.pi.set_watchdog(self.gpio,11)
#      print(States[self.m.state], edge_len, "NONE" if edge_type==None else Intervals[edge_type], "--> ", end="")
      self.m._next(edge_type,edge_len)
#      print(States[self.m.state])

"""
   tx: A class to transmit the wireless codes sent by 433 MHz wireless fobs.
   [HDT] modified for PPM: constant pulse width, variable inter-pulse gaps (marks)
"""
class tx():
   def __init__(self, pi, gpio, pulse=Timing_Table[PULSE][2],
                repeats=REPEATS, bits=MSGLEN, gap=Timing_Table[GAP][2],
                t0=Timing_Table[SHORT][2], t1=Timing_Table[LONG][2],
                sync=Timing_Table[SYNC][2]):
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
