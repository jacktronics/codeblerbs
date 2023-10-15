#!/usr/bin/env python3
"""
Sometimes, applications do not support pasting string into them for various reasons, but there are also reasons we as users need to allow a paste to happen
Imagine a password manager for example, if we can't paste the long random string provided to an application ? This incentivise the user to reduce the password complexity defeating the point ...
This example app allows you to paste a string into any other app by first pressing p. 

It can easily be modified to support you pasting the string from the clipboard using the module getpass for example.

This code needs accessibility permissions set for the terminal application in use, but it checks for such permissions and waits on you to actually make the necessary changes.

This code requires a Terminal application running in Sandbox and Signed (Terminal.app is in that case) otherwise the events do not get received.

It also requires the following modules : pyobjc-framework-ApplicationServices, pyobjc-framework-Cocoa, pyobjc-framework-Quartz
"""
import sys
from Quartz import CGEventSourceCreate, \
                CGEventCreateKeyboardEvent, \
                CGEventKeyboardGetUnicodeString, \
                CGEventFlags, \
                CGEventGetFlags, \
                CGEventSetFlags, \
                CGEventPost, \
                CGEventSourceStateID, \
                CGEventTapLocation, \
                kCGHIDEventTap, \
                kCGEventSourceStateHIDSystemState, \
                kCGEventFlagMaskShift, \
                kCGEventFlagMaskAlternate
from ApplicationServices import kAXTrustedCheckOptionPrompt
from HIServices import AXIsProcessTrustedWithOptions, AXIsProcessTrusted
from AppKit import NSApplication, NSObject, NSBundle, NSDistributedNotificationCenter,\
                NSControlKeyMask, NSEvent, NSTimer, NSKeyDownMask

SHIFT_KEY = 'SHIFT'
ALT_KEY = 'ALT'
RETURN_KEY = '\r'
BACKSPACE_KEY = '\u007f'

def log( message, verbose=False ):
    if verbose:
        print( message, file=sys.stderr )

class keyboardController:
    def __init__(self):
        # Keyboards are very diverse, we need to create a map between characters and the currently used keyboard layout.
        self.keyboardMap = {}
        self.eventSource = CGEventSourceCreate(CGEventSourceStateID(kCGEventSourceStateHIDSystemState))
        self.eventTapLocation = CGEventTapLocation(kCGHIDEventTap)
        i = 0
        while i < 128:
            e = CGEventCreateKeyboardEvent(self.eventSource, i, True)
            nse = NSEvent.eventWithCGEvent_(e)
            if CGEventFlags(kCGEventFlagMaskShift) & nse.modifierFlags() == CGEventFlags(kCGEventFlagMaskShift):
                self.keyboardMap['SHIFT'] = { 'code':i, 'shift':False, 'alt':False}
                self.shiftKeyCode = i
            if CGEventFlags(kCGEventFlagMaskAlternate) & nse.modifierFlags() == CGEventFlags(kCGEventFlagMaskAlternate):
                self.keyboardMap['ALT'] = { 'code':i, 'shift':False, 'alt':False}
                self.altKeyCode = i
            u = CGEventKeyboardGetUnicodeString(e, 1, None, None)
            if not u[1]:
                i+=1
                continue
            # keys with no modifiers
            char = nse.characters()
            if char not in self.keyboardMap.keys(): self.keyboardMap[char] = { 'code':i, 'shift':False, 'alt':False}
            # keys with shift pressed
            CGEventSetFlags(e, CGEventGetFlags(e) | CGEventFlags(kCGEventFlagMaskShift))
            nse = NSEvent.eventWithCGEvent_(e)
            char = nse.characters()
            if char not in self.keyboardMap.keys(): self.keyboardMap[char] = { 'code':i, 'shift':True, 'alt':False}
            CGEventSetFlags(e, CGEventGetFlags(e) & ~CGEventFlags(kCGEventFlagMaskShift))
            # keys with alt pressed
            CGEventSetFlags(e, CGEventGetFlags(e) | CGEventFlags(kCGEventFlagMaskAlternate))
            nse = NSEvent.eventWithCGEvent_(e)
            char = nse.characters()
            if char not in self.keyboardMap.keys(): self.keyboardMap[char] = { 'code':i, 'shift':False, 'alt':True}
            i+=1
        self.returnKeyCode = self.keyboardMap[RETURN_KEY]['code']
        self.backSpaceKeyCode = self.keyboardMap[BACKSPACE_KEY]['code']
    def typeString(self, passPhrase, backspace=False):
        # a key press is at least 2 events, key down and key up, but if it's a capital letter or a special character we need to press down SHIFT or ALT down before and later up ...
        def pressKeyWithModifier(keyCode, modifierKeyCode, modifierFlag):
            modifierEvent = CGEventCreateKeyboardEvent(self.eventSource, modifierKeyCode, True)
            CGEventPost(self.eventTapLocation, modifierEvent)
            keyEvent = CGEventCreateKeyboardEvent(self.eventSource, keyCode, True)
            CGEventSetFlags(keyEvent, CGEventGetFlags(keyEvent) | CGEventFlags(modifierFlag))
            CGEventPost(self.eventTapLocation, keyEvent)
            modifierEvent = CGEventCreateKeyboardEvent(self.eventSource, modifierKeyCode, False)
            CGEventPost(self.eventTapLocation, modifierEvent)
            keyEvent = CGEventCreateKeyboardEvent(self.eventSource, keyCode, False)
            CGEventSetFlags(keyEvent, CGEventGetFlags(keyEvent) & ~CGEventFlags(modifierFlag))
            CGEventPost(self.eventTapLocation, keyEvent)
        def pressKey(keyCode):
            keyEvent = CGEventCreateKeyboardEvent(self.eventSource, keyCode, True)
            CGEventPost(self.eventTapLocation, keyEvent)
            keyEvent = CGEventCreateKeyboardEvent(self.eventSource, keyCode, False)
            CGEventPost(self.eventTapLocation, keyEvent)
        i = 0
        if backspace: pressKey(self.backSpaceKeyCode)
        while i < len(passPhrase):
            settings = self.keyboardMap[passPhrase[i]]
            keyCode = settings['code']
            if settings['shift']: keyEvent = pressKeyWithModifier( keyCode, self.shiftKeyCode, kCGEventFlagMaskShift )
            elif settings['alt']: keyEvent = pressKeyWithModifier( keyCode, self.altKeyCode, kCGEventFlagMaskAlternate )
            else: pressKey(keyCode)
            i+=1
        # pressing the return key after we're done processing the string.
        pressKey(self.returnKeyCode)

# seperate class to define the necessary event handlers used to react to permission changes as well as key presses
class eventManager:
    # when we receive a permission change notification, wait 100ms for the system to finish processing the permission config change, and run the checkPermission_ function
    def permEventHandler(self, notification):
        NSTimer.scheduledTimerWithTimeInterval_target_selector_userInfo_repeats_(0.1, self, "checkPermissions:", None, False)
    # when we receive a keyEvent, if we receive CTRL+C we run exitRunLoop_ to stop the app, if we receive p we go ahead and type the string.
    def keyEventHandler(self, event):
        ctrlKeyPressed = NSEvent.modifierFlags() & NSControlKeyMask
        if ctrlKeyPressed and event.charactersIgnoringModifiers() == 'c':
            self.exitRunLoop_()
        elif event.charactersIgnoringModifiers() == 'p':
            # stopping the keyEvent monitor
            NSEvent.removeMonitor_(self.keyMonitor)
            # initialize a keyboard controller object, and run the function to type the strings as a suite of virtual keyboard key presses.
            keyboardController().typeString(self.string, backspace=True)
            # wait 500ms for the all the keys we pressed to be processed by the system, then we exit the runloop
            NSTimer.scheduledTimerWithTimeInterval_target_selector_userInfo_repeats_(0.5, self, "exitRunLoop:", None, False)

# Application Delegate for the macOS UI app runloop.
class AppDelegate(NSObject, eventManager):
    def init(self):
        self.app = NSApplication.sharedApplication()
        # setting the app delegate on the runloop
        self.app.setDelegate_(self)
        return self
    def exitRunLoop_(self, timer=None):
        self.app.stop_(None)
        self.app.abortModal()
    def checkPermissions_(self, timer):
        # if the accessibility permissions were granted, follow with the keyEvent monitoring, otherwise we do nothing ...
        if AXIsProcessTrustedWithOptions({kAXTrustedCheckOptionPrompt: False}):
            log('\U0001f6a9 Press p to paste, or press CTRL+C to exit', verbose=True)
            # as permissions were granted, we can stop monitoring permission changes.
            self.notificationCenter.removeObserver_(self.appObserver)
            # setting the keyEvent monitor to run keyEventHandler for any key presses (down only).
            self.keyMonitor = NSEvent.addGlobalMonitorForEventsMatchingMask_handler_(NSKeyDownMask, self.keyEventHandler)
    def applicationDidFinishLaunching_(self, notification):
        # this runs right after the runloop has initialized, we first check if we have accessibility permissions to detect key presses, and to later type send keyboard events. 
        if AXIsProcessTrustedWithOptions({kAXTrustedCheckOptionPrompt: True}):
            log('\U0001f6a9 Press p to paste, or press CTRL+C to exit', verbose=True)
            # setting the keyEvent monitor to run keyEventHandler for any key presses (down only).
            self.keyMonitor = NSEvent.addGlobalMonitorForEventsMatchingMask_handler_(NSKeyDownMask, self.keyEventHandler)
        else:
            # if we do not have permission, the system will notify the user and change the settings. We also setup an observer on the events related to the accessibility permissions so we can react to the user config changes
            log('\a\U0001F514 You must first follow the popup message instructions before continuing', verbose=True)
            self.notificationCenter = NSDistributedNotificationCenter.defaultCenter()
            self.appObserver = self.notificationCenter.addObserverForName_object_queue_usingBlock_( "com.apple.accessibility.api", None, None, self.permEventHandler)


def main(argv):
    if len(argv) != 2:
        sys.exit('usage: {0} messageToType'.format(argv[0]))

    # this is to prevent the interpreter icon to show up in dock ...
    info = NSBundle.mainBundle().infoDictionary()
    info.setValue_forKey_( "1", "LSUIElement" )

    # initializating the app delegate object, storing the string value in the object so the delegate subfunctions can access it.
    app = AppDelegate.new()
    app.string = argv[1]

    # run the application runloop
    NSApplication.sharedApplication().run()

if __name__ == '__main__':
    main(sys.argv)