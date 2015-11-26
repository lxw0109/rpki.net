# $Id: missing-oids.py 5624 2014-01-09 20:56:06Z sra $
# 
# Copyright (C) 2008  American Registry for Internet Numbers ("ARIN")
# 
# Permission to use, copy, modify, and distribute this software for any
# purpose with or without fee is hereby granted, provided that the above
# copyright notice and this permission notice appear in all copies.
# 
# THE SOFTWARE IS PROVIDED "AS IS" AND ARIN DISCLAIMS ALL WARRANTIES WITH
# REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF MERCHANTABILITY
# AND FITNESS.  IN NO EVENT SHALL ARIN BE LIABLE FOR ANY SPECIAL, DIRECT,
# INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES WHATSOEVER RESULTING FROM
# LOSS OF USE, DATA OR PROFITS, WHETHER IN AN ACTION OF CONTRACT, NEGLIGENCE
# OR OTHER TORTIOUS ACTION, ARISING OUT OF OR IN CONNECTION WITH THE USE OR
# PERFORMANCE OF THIS SOFTWARE.

"""
Figure out what OIDs from rpki.oids are missing from dumpasn1's database.
"""

import rpki.POW.pkix, rpki.oids

need_header = True

for oid, name in rpki.oids.oid2name.items():
  try:
    rpki.POW.pkix.oid2obj(oid)
  except:
    o = rpki.POW.pkix.Oid()
    o.set(oid)
    if need_header:
      print
      print "# Local additions"
      need_header = False
    print
    print "OID =", " ".join(("%02X" % ord(c)) for c in o.toString())
    print "Comment = RPKI project"
    print "Description =", name, "(" + " ".join((str(i) for i in oid)) + ")"
