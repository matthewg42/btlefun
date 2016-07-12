#!/usr/bin/env python3

import logging
from bluepy.btle import UUID, Peripheral, Scanner, DefaultDelegate
import threading
import time
import struct

global keepScanning
log = logging
keepScanning = True
internationalMorse = {
    'A': '.-',
    'B': '-...',
    'C': '-.-.',
    'D': '-..',
    'E': '.',
    'F': '..-.',
    'G': '--.',
    'H': '....',
    'I': '..',
    'J': '.---',
    'K': '-.-',
    'L': '.-..',
    'M': '--',
    'N': '-.',
    'O': '---',
    'P': '.--.',
    'Q': '--.-',
    'R': '.-.',
    'S': '...',
    'T': '-',
    'U': '..-',
    'V': '...-',
    'W': '.--',
    'X': '-..-',
    'Y': '-.--',
    'Z': '--..',
    '0': '-----',
    '1': '.----',
    '2': '..---',
    '3': '...--',
    '4': '....-',
    '5': '.....',
    '6': '-....',
    '7': '--...',
    '8': '---..',
    '9': '----.',
    '.': '.-.-.-',
    ',': '--..--',
    '?': '..--..',
    ':': '---...',
    "'": '.----.',
    '-': '-....-',
    ';': '-.-.-',
    '/': '-..-.',
    '(': '-.--.',
    ')': '-.--.-',
    '"': '.-..-.',
    '_': '..--.-',
    '=': '-...-',
    '+': '.-.-.',
    ' ': '/'
}

class BeepMaker:
    ''' BeepMaker takes an address, queries to see if the device is beepable, and sets it beeping if it is... '''
    def __init__(self, addr):
        self.addr = addr
        self.thread = threading.Thread(target=self.run)
        self.terminate = False
        self.per = None
        self.lastBeep = 0
        self.state = 'Initialized'
        self.beep_characteristic = None

    def __str__(self):
        return 'BeepMaker[addr=%s] state=%s' % (self.addr, self.state)

    def run(self):
        try:
            self.connect()
            if not self.terminate:
                self.discover()
            if not self.terminate:
                self.verify()
            while not self.terminate:
                self.state = 'Lurking'
                if time.time() - self.lastBeep > 15:
                    self.beep()
                time.sleep(1)
        except Exception as e:
            log.exception('BeepMaker[addr=%s] %s: %s' % (self.addr, type(e), e))
            self.terminate = True

        log.debug('BeepMaker addr=%s %s' % (self.addr, 'end' if not self.terminate else 'terminated'))

    def connect(self):
        log.debug('BeepMaker[addr=%s], connecting...' % self.addr)
        self.state = 'Connecting'
        self.per = Peripheral(self.addr)

    def discover(self):
        log.debug('BeepMaker[addr=%s], service discovery...' % self.addr)
        self.state = 'Discovery'
        self.per.discoverServices()

    def verify(self):
        ''' Check this is in fact a beepable device '''
        log.debug('BeepMaker[addr=%s], analysing services...' % self.addr)
        self.state = 'Analysing'
        inf = dict()
        for uuid, service in self.per.services.items():
            if uuid == '180a':
                for c in service.getCharacteristics():
                    if c.supportsRead():
                        inf[c.uuid.getCommonName()] = c.read()
            if uuid == 'fff0':
                for c in service.getCharacteristics():
                    if c.uuid == 'fff2':
                        self.beep_characteristic = c
        if inf['Manufacturer Name String'] != b'SIGNAL' or inf['Model Number String'] != b'BT A8105':
            raise Exception('Manufacturer and/or model not a known beeper: %s' % inf)
        if self.beep_characteristic is None:
            raise Exception('No beep characteristic fff0/fff2')

    def beep(self):
        log.debug('BeepMaker[addr=%s], beeping...' % self.addr)
        self.state = 'Beeping'
        self.morse('hi mouse')
        self.lastBeep = time.time()

    def morse(self, message):
        log.debug('BeepMaker[addr=%s], morse(%s)' % (self.addr, message))
        morse = ''
        for letter in list(message):
            morse += internationalMorse[letter.upper()] + ' '
        log.debug('Morse is: %s' % morse)
        ml = list(morse)
        while len(ml) > 0:
            chunk = ml.pop(0)
            while len(ml) > 0 and ml[0] == chunk[-1]:
                chunk += ml.pop(0)
            if chunk[0] == '.':
                self.dit(len(chunk))
            elif chunk[0] == '-':
                self.dash(len(chunk))
            elif chunk[0] == ' ':
                time.sleep(0.200)
            elif chunk[0] == '/':
                time.sleep(0.400)

    def dit(self, n=1):
        self.multibeep(120, 120, n)

    def dash(self, n=1):
        self.multibeep(255, 120, n)

    def multibeep(self, ontime, offtime, n=1):
        log.debug('BeepMaker[addr=%s], multibeep(on=%s, off=%s, n=%s)' % (self.addr, ontime, offtime, n))
        sleepms = (ontime+offtime)*n+(offtime*2)
        self.beep_characteristic.write(struct.pack('BBBBB', 0xaa, 3, n, ontime, offtime))
        time.sleep(sleepms/1000)
        log.debug('BeepMaker[addr=%s], multibeep wait end' % self.addr)

    def shutdown(self):
        self.terminate = True

class BeepManager:
    ''' A singleton manager class that herds the BeepMaker threads '''
    instance = None
    class __BeepManager:
        def __init__(self):
            self.makers = dict()
            self.terminate = False
            self.thread = threading.Thread(target=self.run)
            self.last_report = 0

        def run(self):
            log.debug('BeepManager start')
            while not self.terminate:
                if time.time() - self.last_report > 10:
                    self.report()
                time.sleep(1)
            log.info('BeepManager shutting down...')
            for m in self.makers.values():
                m.shutdown()
            for m in self.makers.values():
                log.debug('BeepManager joining %s' % str(m))
                m.thread.join()
            log.debug('BeepManager end')

        def report(self):
            log.info('BeepManager.report() %d BeepMakers...' % len(self.makers.values()))
            self.last_report = time.time()

        def shutdown(self):
            self.terminate = True

        def addMaker(self, addr):
            if addr not in self.makers:
                beepmaker = BeepMaker(addr)
                beepmaker.thread.start()
                self.makers[addr] = beepmaker
            else:
                log.debug('BeepManager not adding for %s - already have it' % addr)

    def __init__(self):
        if not BeepManager.instance:
            BeepManager.instance = BeepManager.__BeepManager()
    def __getattr__(self, name):
        return getattr(self.instance, name)
        
       
class ScanDelegate(DefaultDelegate):
    def __init__(self):
        DefaultDelegate.__init__(self)

    def handleDiscovery(self, dev, isNewDev, isNewData):
        if isNewDev:
            scanData = dev.getScanData()
            log.info("BTLE dev: %s (%s) RSSI=%d dB | %s" % (dev.addr, dev.addrType, dev.rssi, '; '.join(['%s=%s' % (x[1], x[2]) for x in scanData])))
            BeepManager().addMaker(dev.addr)

def sighandler(signum, frame):
    log.info('Caught signal, shutting down...')
    global keepScanning
    BeepManager().shutdown()
    keepScanning = False
        


if __name__ == '__main__':
    import signal
    log.basicConfig(level=logging.DEBUG)
    log.info('OHHAI')

    for sig in [signal.SIGHUP, 
                signal.SIGUSR1, 
                signal.SIGUSR2,
                signal.SIGTERM, 
                signal.SIGQUIT, 
                signal.SIGINT]:
        signal.signal(sig, sighandler)

    bm = BeepManager()
    bm.thread.start()
    while keepScanning:
        try:
            log.info('Starting scan...')
            scanner = Scanner().withDelegate(ScanDelegate())
            scanner.scan(30.0)
        except Exception as e:
            log.error('while scanning: %s: %s' % (type(e), e))
    bm.shutdown()
    bm.thread.join()
    log.info('KTHXBYE')

