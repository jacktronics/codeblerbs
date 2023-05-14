#!/usr/bin/env python3
"""
This example program extracts the CFBundleIdentifier from a macOS application

macOS applications store this information in [APPLICATION_PATH]/Contents/Info.plist

Here is an example of APPLICATION_PATH : /Applications/VLC.app 

You need this information in order detect the presence of an application on other machines
"""
import os
import sys
import plistlib

def main(argv):
	if len(argv) != 2:
		sys.exit('usage: {0} applicationPath'.format(argv[0]))

	plistPath = os.path.join(argv[1], 'Contents/Info.plist')

	if not os.path.isfile(plistPath):
		sys.exit('FATAL: This path does not contain a macOS application')

	with open(plistPath, 'rb') as plist:
		d = plistlib.loads(plist.read())
		print(d.get('CFBundleIdentifier', None))

if __name__ == '__main__':
    main(sys.argv)