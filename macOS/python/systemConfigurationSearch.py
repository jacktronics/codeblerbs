#!/usr/bin/env python3
"""
This example program shows how to extract all, parts or specific configuration keys out of your macOS system configuration

The system configuration database is used to store information about things such as Network, Bluetooth, MDM

When no argument is provided, a full database dump is attempted.

When an argument containing a .* is provided, we assume a key pattern search

When an argument is provided that does not contain .* a specific key lookup is executed

This program requires the pyobjc-framework-SystemConfiguration module
"""

import re
import sys
from SystemConfiguration import SCDynamicStoreCreate, SCDynamicStoreCopyValue, SCDynamicStoreCopyMultiple, kCFAllocatorDefault

def main(argv):
	search = False

	if len(argv) == 1:
		pattern = '.*'
	else:
		pattern = argv[1]

	starReg = re.compile('\.\*')
	if starReg.search(pattern):
		search = True
		
	# systemConfigurationSearch is an arbitrary string, this can be anything really
	ds = SCDynamicStoreCreate(kCFAllocatorDefault, "systemConfigurationSearch", None, None)

	if search:
		found = SCDynamicStoreCopyMultiple(ds, None, [pattern])
	else:
		found = SCDynamicStoreCopyValue(ds, pattern)

	# if the search is successful, we get a dictionnary we can search into, we are simply going to print our results here
	res = found if found else 'No Results'

	print(res)


if __name__ == '__main__':
    main(sys.argv)