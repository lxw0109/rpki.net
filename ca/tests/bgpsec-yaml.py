#!/usr/bin/env python
#
# $Id: bgpsec-yaml.py 5895 2014-07-12 15:41:55Z sra $
# 
# Copyright (C) 2014  Dragon Research Labs ("DRL")
#
# Permission to use, copy, modify, and distribute this software for any
# purpose with or without fee is hereby granted, provided that the above
# copyright notice and this permission notice appear in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND DRL DISCLAIMS ALL WARRANTIES WITH
# REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF MERCHANTABILITY
# AND FITNESS.  IN NO EVENT SHALL DRL BE LIABLE FOR ANY SPECIAL, DIRECT,
# INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES WHATSOEVER RESULTING FROM
# LOSS OF USE, DATA OR PROFITS, WHETHER IN AN ACTION OF CONTRACT, NEGLIGENCE
# OR OTHER TORTIOUS ACTION, ARISING OUT OF OR IN CONNECTION WITH THE USE OR
# PERFORMANCE OF THIS SOFTWARE.

"""
Script to generate YAML to feed to test scripts.  A bit circular, but less work this way.

This is a quick hack to generate some test data using BGPSEC router certificates.
It does not (yet?) correspond to any router configurations here or anywhere.  At some
point it may evolve into a proper test program.
"""

import yaml

root = "Root"

class Kid(object):

  def __init__(self, n):
    self.name = "ISP-%03d" % n
    self.ipv4 = "10.%d.0.0/16" % n
    self.asn  = n
    self.router_id = n * 10000

  @property
  def declare(self):
    return dict(name = self.name,
                ipv4 = self.ipv4,
                asn  = self.asn,
                hosted_by   = root,
                roa_request = [dict(asn = self.asn, ipv4 = self.ipv4)],
                router_cert = [dict(asn = self.asn, router_id = self.router_id)])

  @property
  def del_routercert(self):
    return dict(name = self.name, router_cert_del = [dict(asn = self.asn, router_id = self.router_id)])

  @property
  def add_routercert(self):
    return dict(name = self.name, router_cert_add = [dict(asn = self.asn, router_id = self.router_id)])


kids = [Kid(n + 1) for n in xrange(200)]

shell_fmt = "shell set -x; ../../../rp/rpki-rtr/rpki-rtr cronjob rcynic-data/authenticated && tar %svf rpki-rtr.tar *.[ai]x*.v*"
shell_first = shell_fmt % "c"
shell_next  = shell_fmt % "u"

sleeper = "sleep 30"

docs = [dict(name         = root,
             valid_for    = "1y",
             kids         = [kid.declare for kid in kids])]

docs.append([shell_first,
             sleeper])

gym = kids[50:70]

for kid in gym:
  docs.append([shell_next, 
               kid.del_routercert,
               sleeper])

for kid in gym:
  docs.append([shell_next, 
               kid.add_routercert,
               sleeper])

print '''\
# This configuration was generated by a script.  Edit at your own risk.
'''

print yaml.safe_dump_all(docs, default_flow_style = False, allow_unicode = False)
