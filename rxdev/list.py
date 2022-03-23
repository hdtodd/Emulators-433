# interval types                                                                                                         
SYNC_GAP = 0
PULSE    = 1
SHORT    = 2
LONG     = 3
SYNC     = 4
GAP      = 5

Timing_Table = [[SYNC_GAP  , "SYNC_GAP",  475, 0, 0],       #interval between sync pulses
                [PULSE     , "PULSE"   ,  505, 0, 0],       #pulses are this duration, +/- TOLERANCE
                [SHORT     , "SHORT"   , 1006, 0, 0],       #interval after pulse to indicate data bit "0"
                [LONG      , "LONG"    , 2000, 0, 0],       #interval after pulse to indicate data bit "1"
                [SYNC      , "SYNC"    , 8940, 0, 0],       #interval after third sync pulse, before first data
                [GAP       , "GAP"     ,10200, 0, 0]        #interval after pulse that terminates last data bit
               ]

print(Timing_Table)
    
for i in Timing_Table:
    if i[0]==LONG:
        print(i[1])

for i in Timing_Table:
    i[3] = int(i[2]*0.9)
    i[4] = int(i[2]*1.1)
    print(i)

t = LONG
match t:
   case PULSE:
      print("match pulse")
   case LONG:
      print("match LONG")
   case _:
      print("no match")

