#!/usr/bin/env python3
"""
This example shows how to extract an email address (when present) from a certificate stored on the macOS keychain

Requires pyobjc-framework-Security
""" 
import sys
from Security import kCFBooleanTrue, \
                    kSecClass, kSecClassCertificate, kSecAttrLabel, \
                    kSecMatchLimit, kSecMatchLimitAll, \
                    kSecReturnRef, \
                    SecIdentityCopyCertificate, \
                    SecItemCopyMatching, \
                    SecCertificateCopyEmailAddresses

def getClientCertEmail(label:str) -> tuple[bool,str]:
    matchDict = {
        kSecClass: kSecClassCertificate,
        kSecAttrLabel: label,
        kSecReturnRef: kCFBooleanTrue,
        kSecMatchLimit: kSecMatchLimitAll
    }
    status, identity_refs = SecItemCopyMatching( matchDict, None )
    if status == 0:
        for identity_ref in identity_refs:
            status, cert_ref = SecIdentityCopyCertificate(identity_ref, None)
            status, cert_emails = SecCertificateCopyEmailAddresses(cert_ref, None)
            email = cert_emails[0] if status else None
            return True, email
    return False, None

def main(argv):
    if len(argv) != 2: sys.exit('usage: {0} certificateCommonName'.format(argv[0]))
    found, email = getClientCertEmail(argv[1]) 
    if not found: sys.exit('No matching certificate found')
    out = email if email else 'No email attribute found on matching certificate'
    print(out)

if __name__ == '__main__':
    main(sys.argv)