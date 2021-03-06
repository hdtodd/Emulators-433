# Emulators-433

These are programs written for Raspberry Pi that emulate ISM 433MHz-band remote sensing devices.  They're used to test rtl_433 code (merbanan/rtl_433) on a system that can receive those transmissions.  They use the pigpio library to manage GPIO pins and the associated _433 library to access pigpio.

2022.03.24:  Acurite 609THX Python emulator working; Maverick-et73 working 

Use of these programs requires an ISM-band (Industrial-Scientific-Medical) transmitter (e.g., a 433MHz transmitter) connected to a Raspberry Pi.  These are usually small, inexpensive devices connected with three wires to the Pi (VCC, GND, DATA).  The receiving system will have a similar device as a receiver for ISM band.  For testing purposes within this program, the transmitter and receiver may be on the same Pi, and these testing programs are written to both send and receive/verify transmitted messages.

Run rtl_433 on this or another another Pi to receive messages from the emulated devices provided on this distribution.

To confirm transmission of packets by the emulators here and reception by the rtl_433 service, either:
- Configure that server to publish to an MQTT broker (and run that broker as a service on that Pi), then subscribe to that MQTT feed from any Pi on the network to watch MQTT packets from rtl-433 in real time, or
- Review the rtl_433 log on that system to see the entries from the devices emulated here.

So far, tests are provided for:
- Acurite 609THX: remote thermometer/hygrometer
- Maverick-et73: smoker dual-thermometer
- Raspi: multi-function, general-purpose remote sensor

Written by H D Todd, 2022-03; hdtodd@gmail.com
using base code associated with the pigpio distribution and retrieved from abyz.me.uk/rpi/pigpio/code/_433_py.zip
