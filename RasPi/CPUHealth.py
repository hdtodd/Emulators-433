# CPUHealth.py
# Demonstrate how to obtain CPU status in Python

from gpiozero import CPUTemperature
import re

print("CPU health report prototype code")
bb=bytearray([0,0,0,0,0,0,0,0,0,0])
print("Initial message byte array: ", end='')
print(bb)

cpu = str(CPUTemperature())
l=[]
l=re.findall(r'\d+.\d+',cpu)
t = float(l[0])
#t=-20.1  #used to force test of negatives
print("CPU Temp string: {:<s}; extracted temp as string: {:<s}; temp as a float: {:<5.1f}C".format(cpu,l[0],t))
n=int((t+0.049)*10) #round to 0.1 degree  & scale to 10th's of a degree C
print("As int * 10, temp = ", n)
n=n&0xFFF          #mask to rh 12 bits = 3 nibbles
print("temp as bit field: 0x{:<4x}".format(n))

u=float(open('/proc/uptime').read().split()[0])
d=int(u)//24//60//60
h=(int(u)-d*24*60*60)//60//60
m=(int(u)-d*24*60*60-h*60*60)//60
print("Elapsed time since boot in sec: {:<8.1f} = {:d} days {:d}:{:d}".format(u,d,h,m))
e=int(u)&0xFFFFF         #mask to rh 20 bits = 5 nibbles
print("Elapsed time since boot in sec as integer bit field: 0x{:<x}".format(e))

l1=float(open('/proc/loadavg').read().split()[0])
l2=float(open('/proc/loadavg').read().split()[1])
print("Load averages: {:6.1f} 1-min & {:6.1f} 5-min".format(l1,l2))
la1=int(l1*10)&0xFF      #mask to rh 8 bits = 2 nibbles as a precaution
la2=int(l2*10)&0xFF
print("Load averages *10 as bit fields: 0x{:<x} 1-min & 0x{:<x} 5 min".format(la1,la2))

bb[1] = (n&0xff0)>>4
bb[2] = (n&0x00f)<<4 | (e&0xf0000)>>16
bb[3] = (e&0x0ff00)>>8
bb[4] =  e&0x000ff
bb[5] = la1%(1<<8)
bb[6] = la2%(1<<8)

print("Prepared message: [ ", end='')
for i in range(len(bb)):
    print("0x{:02x} ".format(bb[i]), end='')
print("]")
