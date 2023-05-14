#!/usr/bin/env python3
"""
This example program pastes the first command line argument into the clipboard

It is done through the native macOS NSPasteboard function instead of the pbcopy utility method,
the latter method requiring a syscall to an external binary

This program requires the pyobjc-Framework-Cocoa module
"""

import sys
from AppKit import NSPasteboard, NSStringPboardType

def main(argv):
    if len(argv) != 2:
        sys.exit('usage: {0} toClipboardString'.format(argv[0]))

    toClipboardString = argv[1]

    # We initialize a general pasteboard object
    pboard = NSPasteboard.generalPasteboard()

    # We define there is no specific ownership for this new pasteboad by passing it a NULL (None) value
    pboard.declareTypes_owner_([NSStringPboardType], None)

    # This function returns a boolean for success/failure
    ret = pboard.setString_forType_(toClipboardString, NSStringPboardType)

    out = 'Success' if ret else 'Failure'
    print(out)

if __name__ == '__main__':
    main(sys.argv)