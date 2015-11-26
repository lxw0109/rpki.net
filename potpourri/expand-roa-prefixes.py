# $Id$
# 
# Copyright (C) 2011  Internet Systems Consortium ("ISC")
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
I got tired of trying to explain in English how the maxLength macro
hack works in ROAs, so this is an attempt to explain it as code.

Given one or more ROA prefix sets on the command line, this script
prints out the expansion as a list of prefixes.
"""

import sys
import rpki.resource_set
import rpki.ipaddrs

class NotAPrefix(Exception):
  """
  Address is not a proper prefix.
  """

class address_range(object):
  """
  Iterator for rpki.ipaddrs address objects.
  """

  def __init__(self, start, stop, step):
    self.addr = start
    self.stop = stop
    self.step = step
    self.type = type(start)

  def __iter__(self):
    while self.addr < self.stop:
      yield self.addr
      self.addr = self.type(self.addr + self.step)

def main(argv):

  prefix_sets = []
  for arg in argv:
    if ":" in arg:
      prefix_sets.extend(rpki.resource_set.roa_prefix_set_ipv6(arg))
    else:
      prefix_sets.extend(rpki.resource_set.roa_prefix_set_ipv4(arg))

  for prefix_set in prefix_sets:
    sys.stdout.write("%s expands to:\n" % prefix_set)

    prefix_type = prefix_set.range_type.datum_type
    prefix_min = prefix_set.prefix
    prefix_max = prefix_set.prefix + (1L << (prefix_type.bits - prefix_set.prefixlen))

    for prefixlen in xrange(prefix_set.prefixlen, prefix_set.max_prefixlen + 1):

      step = (1L << (prefix_type.bits - prefixlen))
      mask = step - 1

      for addr in address_range(prefix_min, prefix_max, step):
        if (addr & mask) != 0:
          raise NotAPrefix, "%s is not a /%d prefix" % (addr, prefixlen)
        sys.stdout.write("  %s/%d\n" % (addr, prefixlen))

    sys.stdout.write("\n")

if __name__ == "__main__":
  main(sys.argv[1:] if len(sys.argv) > 1 else ["18.0.0.0/8-24"])
