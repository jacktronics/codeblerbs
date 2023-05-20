#!/usr/bin/env python3
"""
This example program returns the current Safari Webkit UserAgent from your system

To mimik your default browser for your client side automation scripts.

This program requires the pyobjc-Framework-WebKit module
"""

from WebKit import WKWebView
from AppKit import NSBundle

def main():
	# The next 2 lines are to prevent the python icon to show up on the dock ... 
	info = NSBundle.mainBundle().infoDictionary()
	info.setValue_forKey_( "1", "LSUIElement" )

	# Initializing a WebKit View, gathering its default UserAgent, freeing memory
	wkv = WKWebView.alloc().init()
	userAgent = wkv.valueForKey_("userAgent")
	wkv.dealloc()

	print(userAgent)

if __name__ == '__main__':
    main()