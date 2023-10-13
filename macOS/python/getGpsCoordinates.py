#!/usr/bin/env python3
"""
This example program gives the GPS Coordinates from your current location using the native macOS Localization service.

This program requires the pyobjc-Framework-CoreLocation module
"""
from objc import super as objcSuper
from CoreLocation import CLLocationManager, kCLDistanceFilterNone, kCLLocationAccuracyBest
from AppKit import NSApplication, NSObject, NSBundle

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
        return self
    def exitRunLoop_(self, timer=None):
        nsapp = NSApplication.sharedApplication()
        nsapp.stop_(None)
        nsapp.abortModal()   
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
    coordinates = finder.locationManager.location().coordinate()
    print(f"Latitude: {coordinates.latitude}, Longitude: {coordinates.longitude}")

if __name__ == '__main__':
    main()
