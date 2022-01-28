# Emulators-433

These are programs written for Raspberry Pi that emulate ISM 433MHz-band remote sensing devices.  They're used to test rtl_433 code (merbanan/rtl_433) on a system that can receive those transmissions.  They use the pigpio library to manage GPIO pins and the associated \_433 library to access pigpio.

So far, tests are provided for:
- Acurite 609THX remote thermometer/hygrometer
- Maverick-et73 smoker dual-thermometer
- Raspi multi-function, general-purpose remote sensor

Written by H D Todd, 2022-02; hdtodd@gmail.com
