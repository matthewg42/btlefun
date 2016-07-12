
## BTLE Keyfobs

There are these little Bluetooth Low Energy things which attach to key fobs.  When you lose your keys, you can make them beep remotely with your iPad.  They also have a little button on them which you can use to take a photo.

This project exploits the fact that these devices perform no authentication (like regular Bluetooth Pairing), and my be set off by any client which can connect and issue the command used to make them beep.

Specifically, Service *fff0*, characteristic *fff2*, using this command written as 5 unsigned 8-bit integers:

-   byte 0: 0xAA
-   byte 1: 0x03
-   byte 2: *n*
-   byte 3: *on_ms*
-   byte 4: *off_ms*

Where *n* is the number of beeps, *on_ms* is the on-time in milliseconds and *off_ms* is the off time in milliseconds.

Other commands may be possible but I'venot gotten around to fuzzing the thing to see what it can do.

## Pre-requisites

-   Python (2.7 and 3.4 tested and working)
-   bluepy (sudo pip install bluepy)
-   bluepy.btle (comes with bluepy)

## beepmonster.py

This program will continuously scan for new BTLE devices, and if it detects that one is a compatible device, it will start it beeping in morse code, the phrase "hi mouse" every 15 seconds.  

NOTE: Needs to be executed as root on most Linux distros (BTLE scanning is a privileged opreation).

### Known Issues

When a BeepMaker thread experiences any sort of exception (e.g. BTLE stack reports a failure to connect), that thread is then useless, and the device in question will not be added again, and so will remain silent until the program is re-started.

## Acknowledgements

Found this page super-helpful:  http://guru.multimedia.cx/bluetooth-tracking-devicestagskey-finders/
