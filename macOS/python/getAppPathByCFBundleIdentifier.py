#!/usr/bin/env python3
"""
This example program extracts the installation path of a macOS application by its CFBundleIdentifier
We described how to get this identifier in getCFBundleIdentifier.py

For reference here is a short list of common macOS application identifiers :
com.docker.docker
org.videolan.vlc
com.microsoft.rdc.macos

This program requires the pyobjc-Framework-Cocoa module
"""

import sys
from AppKit import NSWorkspace

def main(argv):
	if len(argv) != 2:
		sys.exit('usage: {0} CFBundleIdentifier'.format(argv[0]))

	appURL = NSWorkspace.sharedWorkspace().URLForApplicationWithBundleIdentifier_(argv[1])

	if appURL:
		print(appURL.path())

	else:
		sys.exit('This CFBundleIdentifier has not been detected on this computer')

if __name__ == '__main__':
    main(sys.argv)