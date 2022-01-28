# Emulators-433

These are programs written for Raspberry Pi that emulate ISM 433MHz-band remote sensing devices.  They're used to test rtl_433 code (merbanan/rtl_433) on a system that can receive those transmissions.  They use the pigpio library to manage GPIO pins and the associated \_433 library to access pigpio.

Use of these programs requires an ISM-band (Industrial-Scientific-Medical) transmitter (e.g., a 433MHz transmitter) connected to a Raspberry Pi.  These are usually small, inexpensive devices connected with three wires to the Pi (VCC, GND, DATA).  The receiving system will have a similar device as a receiver for ISM band.  For testing purposes, the transmitter and receiver may be on the same Pi, and these testing programs are written to both send and receive/verify transmitted messages.

So far, tests are provided for:
- Acurite 609THX: remote thermometer/hygrometer
- Maverick-et73: smoker dual-thermometer
- Raspi: multi-function, general-purpose remote sensor

Written by H D Todd, 2022-02; hdtodd@gmail.com
