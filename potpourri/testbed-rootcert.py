# $Id: testbed-rootcert.py 5624 2014-01-09 20:56:06Z sra $
# 
# Copyright (C) 2009-2012  Internet Systems Consortium ("ISC")
# 
# Permission to use, copy, modify, and distribute this software for any
# purpose with or without fee is hereby granted, provided that the above
# copyright notice and this permission notice appear in all copies.
# 
# THE SOFTWARE IS PROVIDED "AS IS" AND ISC DISCLAIMS ALL WARRANTIES WITH
# REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF MERCHANTABILITY
# AND FITNESS.  IN NO EVENT SHALL ISC BE LIABLE FOR ANY SPECIAL, DIRECT,
# INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES WHATSOEVER RESULTING FROM
# LOSS OF USE, DATA OR PROFITS, WHETHER IN AN ACTION OF CONTRACT, NEGLIGENCE
# OR OTHER TORTIOUS ACTION, ARISING OUT OF OR IN CONNECTION WITH THE USE OR
# PERFORMANCE OF THIS SOFTWARE.

"""
Generate config for a test RPKI root certificate for resources
specified in asns.csv and prefixes.csv.

This script is separate from arin-to-csv.py so that we can convert on
the fly rather than having to pull the entire database into memory.
"""

import sys
from rpki.csv_utils import csv_reader

if len(sys.argv) not in (2, 4):
  sys.exit("Usage: %s holder [asns.csv prefixes.csv]" % sys.argv[0])

print '''\
[req]
default_bits                    = 2048
default_md                      = sha256
distinguished_name              = req_dn
prompt                          = no
encrypt_key                     = no

[req_dn]
CN                              = Pseudo-%(HOLDER)s testbed root RPKI certificate

[x509v3_extensions]
basicConstraints                = critical,CA:true
subjectKeyIdentifier            = hash
keyUsage                        = critical,keyCertSign,cRLSign
subjectInfoAccess               = 1.3.6.1.5.5.7.48.5;URI:rsync://%(holder)s.rpki.net/rpki/%(holder)s/,1.3.6.1.5.5.7.48.10;URI:rsync://%(holder)s.rpki.net/rpki/%(holder)s/root.mft
certificatePolicies             = critical,1.3.6.1.5.5.7.14.2
sbgp-autonomousSysNum           = critical,@rfc3779_asns
sbgp-ipAddrBlock                = critical,@rfc3997_addrs

[rfc3779_asns]
''' % { "holder" : sys.argv[1].lower(),
        "HOLDER" : sys.argv[1].upper() }

for i, asn in enumerate(asn for handle, asn in csv_reader(sys.argv[2] if len(sys.argv) > 2 else "asns.csv", columns = 2)):
  print "AS.%d = %s" % (i, asn)

print '''\

[rfc3997_addrs]

'''

for i, prefix in enumerate(prefix for handle, prefix in csv_reader(sys.argv[3] if len(sys.argv) > 2 else "prefixes.csv", columns = 2)):
  v = 6 if ":" in prefix else 4
  print "IPv%d.%d = %s" % (v, i, prefix)
