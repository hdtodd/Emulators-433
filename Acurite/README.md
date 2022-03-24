# Acurite 609THX Temp/Humidity Emulator

This is one of a set of  programs written for Raspberry Pi that emulate ISM 433MHz-band remote sensing devices.  They're used to test rtl_433 code (merbanan/rtl_433) on a system that can receive those transmissions.  They use the pigpio library to manage GPIO pins and the associated _433 library to access pigpio.

This particular program emulates the Acurite 609THX.

This requires an ISM-band (Industrial-Scientific-Medical) transmitter (e.g., a 433MHz transmitter) connected to a Raspberry Pi.  These are usually small, inexpensive devices connected with three wires to the Pi (VCC, GND, DATA).  The receiving system will have a similar device as a receiver for ISM band.  For testing purposes within this program, the transmitter and receiver may be on the same Pi, and these testing programs are written to both send and receive/verify transmitted messages.

This uses GPIO16 for transmit and GPIO22 for receive, but those program parameters are easily changed (see code beginning).

Execute the program with "python3.10 AR609.py" and terminate execution with CNTL-C from the keyboard.

Run rtl_433 on this or another another Pi to receive messages from the emulated devices provided on this distribution.

To confirm transmission of packets by the emulators here and reception by the rtl_433 service, either:
- Configure that server to publish to an MQTT broker (and run that broker as a service on that Pi), then subscribe to that MQTT feed from any Pi on the network to watch MQTT packets from rtl-433 in real time, or
- Review the rtl_433 log on that system to see the entries from the devices emulated here.

This version of the program does extensive data collection that can be used to "tune" the program for better recognition of Acurite 609 transmissions.  The average pulse and data-interval lengths are printed after every valid packet has been received and summarized over all packets upon program termination.  The average pulse, short, and long intervals can be to reset the timings in _433_AR.py to improve packet recognition.

Written by H D Todd, 2022-03; hdtodd@gmail.com
using base code associated with the pigpio distribution and retrieved from abyz.me.uk/rpi/pigpio/code/_433_py.zip
