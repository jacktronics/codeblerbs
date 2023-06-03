#!/usr/bin/env python3
"""
This example program opens the first command line argument file path with its default application

It is done through the native macOS NSWorkspace functions instead of the open utility method,
the latter method requiring a syscall to an external binary

This program requires the pyobjc-Framework-Cocoa module
"""

import sys
from AppKit import NSWorkspace, NSURL

def main(argv) -> None:
	if len(argv) != 2:
		sys.exit('usage: {0} filePath'.format(argv[0]))

	# we create a NSURL object initialized with the file path
	url = NSURL.alloc().initFileURLWithPath_(argv[1])

	# we check if the file exists with the macOS native function call
	canBeOpened, error = url.checkResourceIsReachableAndReturnError_(None)

	# if the function returns True, we create a NSWorkspace and use its openURL function
	# otherwise we gather the error information, print it and exit
	if canBeOpened:
		workspace = NSWorkspace.sharedWorkspace()
		workspace.openURL_(url)
	else:
		errInfo = error.userInfo().valueForKey_("NSUnderlyingError")
		sys.exit(errInfo)

if __name__ == '__main__':
	main(sys.argv)