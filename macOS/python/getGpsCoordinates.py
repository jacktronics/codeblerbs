#!/usr/bin/env python3
"""
This example program gives the GPS Coordinates from your current location using the native macOS Localization service.

This program requires the pyobjc-Framework-CoreLocation module
"""
import sys
from objc import super as objcSuper
from CoreLocation import CLLocationManager, CLAuthorizationStatus, kCLAuthorizationStatusNotDetermined, kCLAuthorizationStatusRestricted, kCLAuthorizationStatusDenied, kCLDistanceFilterNone, kCLLocationAccuracyBest
from AppKit import NSApplication, NSObject, NSWorkspace, NSBundle, NSURL, NSTimer

class LocationDelegate(NSObject):
    def init(self):
        self = objcSuper(LocationDelegate, self).init()
        if not self:
            return
        self.locationManager = CLLocationManager.new()
        self.locationManager.requestWhenInUseAuthorization()
        self.locationManager.setDelegate_(self)
        self.locationManager.setDistanceFilter_(kCLDistanceFilterNone)
        self.locationManager.setDesiredAccuracy_(kCLLocationAccuracyBest)
        self.locationManager.startUpdatingLocation()
        print(f'\U0001F4CC Calling Location Services ...')
        NSTimer.scheduledTimerWithTimeInterval_target_selector_userInfo_repeats_(8, self, "locationCallTimer:", None, False)
        return self
    def locationCallTimer_(self, timer):
        print('\U000026A0\U0000FE0F  Location Services took too long to respond, cancelling')
        self.locationManager.stopUpdatingLocation()
        self.exitRunLoop_()
    def exitRunLoop_(self, timer=None):
        nsapp = NSApplication.sharedApplication()
        nsapp.stop_(None)
        nsapp.abortModal()
    def locationManagerDidChangeAuthorization_(self, manager):
        authorizationStatus = manager.authorizationStatus()
        if authorizationStatus in [kCLAuthorizationStatusRestricted, kCLAuthorizationStatusDenied]:
            url = NSURL.alloc().initWithString_("x-apple.systempreferences:com.apple.preference.security?Privacy_LocationServices")
            workspace = NSWorkspace.sharedWorkspace()
            workspace.openURL_(url)
            print(f'\a\U000026A0\U0000FE0F  The Location Services permissions must be given to Python for the automatic selection.')
    def locationManager_didUpdateLocations_(self, manager, locations):
        self.locationManager.stopUpdatingLocation()
        self.exitRunLoop_()
    def locationManager_didFailWithError_(self, manager, error):
        pass
    def locationManager_didChangeAuthorizationStatus_(self, manager, status):
        pass

def main():
    # to prevent the python icon from showing up ...
    info = NSBundle.mainBundle().infoDictionary()
    info.setValue_forKey_( "1", "LSUIElement" )

    finder = LocationDelegate.new()
    NSApplication.sharedApplication().run()
    location = finder.locationManager.location()
    if location is None: sys.exit('\U0000274c Unable to retrieve location, exiting.')
    coordinates = location.coordinate()
    print(f"Latitude: {coordinates.latitude}, Longitude: {coordinates.longitude}")

if __name__ == '__main__':
    main()
