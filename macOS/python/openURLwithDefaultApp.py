#!/usr/bin/env python3
"""
This example program opens the first command line argument URL with its default application

It is done through the native macOS NSWorkspace functions instead of the open utility method,
the latter method requiring a syscall to an external binary

This program requires the pyobjc-Framework-Cocoa module
"""

import sys
from AppKit import NSWorkspace, NSURL

def main(argv) -> None:
	if len(argv) != 2:
		sys.exit('usage: {0} URL'.format(argv[0]))

	# we initiate the URL object, then we create a workspace to validate it has an application attached to its protocol
	url = NSURL.alloc().initWithString_(argv[1])
	workspace = NSWorkspace.sharedWorkspace()
	applicationPath = workspace.URLForApplicationToOpenURL_(url)

	# if a path is returned, we can use the openURL function, otherwise we exit
	if applicationPath:
		workspace.openURL_(url)
	else:
		sys.exit('Unable to find a suitable application for this URL scheme')

if __name__ == '__main__':
	main(sys.argv)