#! /usr/local/bin/python3.9
# mach-proto.py
# Prototype machine to recognize 40-bit PPM codes from 433MHz receivers
#   as a model for recognizing Acurite 609TX temp/humidity sensor readings
import sys
from enum import Enum, auto

MSGLEN = 40
CSIRED = "\033[31m"
CSIBLK = "\033[30m"
#    PS1='\[\033[01;32m\]\u@\h\[\033[00m\]:\[\033[01;34m\]\w \$\[\033[00m\] '
class Interval_Type(Enum):
   SYNC_GAP      =  475       #interval between sync pulses                                                             
   PULSE         =  505       #pulses are this duration, +/- 5%                                                        
   SHORT         = 1006       #interval after pulse to indicate data bit "0"                                           
   LONG          = 2000       #interval after pulse to indicate data bit "1"                                           
   SYNC          = 8940       #interval after third sync pulse, before first data                                      
   GAP           =10200       #interval after pulse that terminates last data bit                                      

class State(Enum):
   SYNC_WAIT    = auto()
   DATA_COLLECT = auto()
   PKT_GAP_WAIT = auto()

class Pattern:
   s: State
   t: Interval_Type
   
class mach():
   def __init__(self,callback=None):
      self.state = State.SYNC_WAIT
      self.sync_count = 0
      self.bit_count = 0
      self.code = 0
      self.cb = callback
      
   def _next(self,token):
      if self.state == State.SYNC_WAIT:
         if token == Interval_Type.SYNC_GAP:
            self.sync_count += 1
            if self.sync_count >=3:
               #should be 2 pulse+sync-gaps then 1 pulse+sync-interval
               #  so 3 pulst+sync-gaps isn't our patern: reset machine
               self.state = State.SYNC_WAIT
               self.sync_count = 0
            else:
               pass
         elif token == Interval_Type.SYNC:
            if self.sync_count==2:
               #We've seen two sync pulse/gap pairs, and now a pulse/SYNC interval
               # So sync pattern is complete: go into data collect mode
               self.state = State.DATA_COLLECT
               self.sync_count==0
            else:
               #should have been 2 SYNC_GAPS followed by SYNC interval
               #  so <2 SYNC_GAPS followed by SYNC isn't our pattern: reset
               self.state = State.SYNC_WAIT
               self.sync_count = 0
      elif self.state == State.DATA_COLLECT:
         if token == Interval_Type.GAP and self.bit_count==MSGLEN:
            #This is a valid packet.  Send result back to caller and reset for next
            self.cb(self.code, self.bit_count, 0, 0, 0)  #pulsei, shorti, longi
            self.__init__(callback=self.cb)
         elif token == Interval_Type.SHORT or token == Interval_Type.LONG:
            #If this is a data bit, record it
            self.code <<= 1                   #make room for next bit
            self.bit_count += 1
            if token == Interval_Type.SHORT:
               pass                           #leave it "0" for SHORT
            elif token == Interval_Type.LONG:
               self.code += 1                 #make it "1" for LONG
            else:
               #Otherwise it's an invalid packet: reset
               self.__init__(callback=self.cb)
         else:
            #by default, all other cases reset recognition machine states
            #  and counts
            self.__init__(callback=self.cb)

   def _get_state(self):
      return self.state, self.sync_count, self.bit_count, self.code

def rx_callback(code, bits, pulsei, shorti, longi):
   print("\n\tFrom callback: Received msg with {:d} bits: avg pulse={:d}, avg short={:d}, avg long={:d}".format(bits, pulsei, shorti, longi))
   print("\tCode = 0x{:X} = 0b{:40b}".format(code, code))
      

#main      
print("\nProgram to test 433MHz PPM code pattern recognition for Acurite 609TX\n")

m = mach(callback=rx_callback)

#First, verify a valid bit packet
print(CSIRED,"\n1. Check for valid pattern with alternating 1/0 40-bit code",CSIBLK)

print("First SYNC_GAP ==> ", end="")
m._next(Interval_Type.SYNC_GAP)
print("State: {:s}, sync_count: {:d}, bit_count: {:d}, code: 0x{:X}".format(m.state, m.sync_count, m.bit_count, m.code))

print("Second SYNC_GAP ==> ", end="")
m._next(Interval_Type.SYNC_GAP)
print("State: {:s}, sync_count: {:d}, bit_count: {:d}, code: 0x{:X}".format(m.state, m.sync_count, m.bit_count, m.code))

print("SYNC Interval ==> ", end="")
m._next(Interval_Type.SYNC)
print("State: {:s}, sync_count: {:d}, bit_count: {:d}, code: 0x{:X}".format(m.state, m.sync_count, m.bit_count, m.code))

print("40 data bits, alternating 1 & 0 ==> ", end="")
for i in range (0,40):
   m._next(Interval_Type.LONG if i%2==0 else Interval_Type.SHORT)
print("State: {:s}, sync_count: {:d}, bit_count: {:d}, code: 0x{:X}".format(m.state, m.sync_count, m.bit_count, m.code))

print("GAP interval next, should result in callback & code printout ==> ", end="")
m._next(Interval_Type.GAP)

print("Final state after GAP ==> ", end="")
print("State: {:s}, sync_count: {:d}, bit_count: {:d}, code: 0x{:X}".format(m.state, m.sync_count, m.bit_count, m.code))

#Next, try an incomplete preamble
print(CSIRED,"\n2. Check using an incomplete preamble (2 syncs) with 40-bit code",CSIBLK)
m._next(Interval_Type.SYNC_GAP)
m._next(Interval_Type.SYNC)
for i in range (0,40):
   m._next(Interval_Type.LONG if i%2==0 else Interval_Type.SHORT)
m._next(Interval_Type.GAP)
print("Final state after GAP ==> ", end="")
print("State: {:s}, sync_count: {:d}, bit_count: {:d}, code: 0x{:X}".format(m.state, m.sync_count, m.bit_count, m.code))

#Next, try an incomplete data packet
print(CSIRED,"\n3. Check using an incomplete data packet (39-bit code",CSIBLK)
m._next(Interval_Type.SYNC_GAP)
m._next(Interval_Type.SYNC_GAP)
m._next(Interval_Type.SYNC)
for i in range (0,39):
   m._next(Interval_Type.LONG if i%2==0 else Interval_Type.SHORT)
m._next(Interval_Type.GAP)
print("Final state after GAP ==> ", end="")
print("State: {:s}, sync_count: {:d}, bit_count: {:d}, code: 0x{:X}".format(m.state, m.sync_count, m.bit_count, m.code))

#Next, try a data packet that's too long
print(CSIRED,"\n4. Check using a data packet that's too long (41-bit code",CSIBLK)
m._next(Interval_Type.SYNC_GAP)
m._next(Interval_Type.SYNC_GAP)
m._next(Interval_Type.SYNC)
for i in range (0,41):
   m._next(Interval_Type.LONG if i%2==0 else Interval_Type.SHORT)
m._next(Interval_Type.GAP)
print("Final state after GAP ==> ", end="")
print("State: {:s}, sync_count: {:d}, bit_count: {:d}, code: 0x{:X}".format(m.state, m.sync_count, m.bit_count, m.code))

#Next, try a data packet that's too long
print(CSIRED,"\n5. Check using a sync & data packet but missing interpacket GAP",CSIBLK)
m._next(Interval_Type.SYNC_GAP)
m._next(Interval_Type.SYNC_GAP)
m._next(Interval_Type.SYNC)
for i in range (0,40):
   m._next(Interval_Type.LONG if i%2==0 else Interval_Type.SHORT)
m._next(Interval_Type.SYNC_GAP)
print("Final state after SYNC_GAP instead of GAP ==> ", end="")
print("State: {:s}, sync_count: {:d}, bit_count: {:d}, code: 0x{:X}".format(m.state, m.sync_count, m.bit_count, m.code))

#Next, finish with another valid packet
print(CSIRED,"\n6. Check again with a valid packet of alternating 0/1",CSIBLK)
m._next(Interval_Type.SYNC_GAP)
m._next(Interval_Type.SYNC_GAP)
m._next(Interval_Type.SYNC)
for i in range (0,40):
   m._next(Interval_Type.LONG if i%2==1 else Interval_Type.SHORT)
print("GAP interval next, should result in callback & code printout ==> ", end="")
m._next(Interval_Type.GAP)
print("Final state after GAP ==> ", end="")
print("State: {:s}, sync_count: {:d}, bit_count: {:d}, code: 0x{:X}".format(m.state, m.sync_count, m.bit_count, m.code))
