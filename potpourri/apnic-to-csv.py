# $Id: apnic-to-csv.py 5624 2014-01-09 20:56:06Z sra $
# 
# Copyright (C) 2010-2012  Internet Systems Consortium ("ISC")
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
Parse APNIC "Extended Allocation and Assignment" reports and write
out (just) the RPKI-relevant fields in myrpki-format CSV syntax.
"""

from rpki.csv_utils import csv_writer
from rpki.ipaddrs import v4addr

asns     = csv_writer("asns.csv")
prefixes = csv_writer("prefixes.csv")

for line in open("delegated-apnic-extended-latest"):

  line = line.rstrip()

  if not line.startswith("apnic|") or line.endswith("|summary"):
    continue

  try:
    registry, cc, rectype, start, value, date, status, opaque_id = line.split("|")
  except ValueError:
    continue

  if not opaque_id:
    continue

  assert registry == "apnic"

  if rectype == "asn":
    asns.writerow((opaque_id, "%s-%s" % (start, int(start) + int(value) - 1)))

  elif rectype == "ipv4":
    prefixes.writerow((opaque_id, "%s-%s" % (start, v4addr(v4addr(start) + long(value) - 1))))

  elif rectype == "ipv6":
    prefixes.writerow((opaque_id, "%s/%s" % (start, value)))

asns.close()
prefixes.close()
