# $Id: analyze-transition.py 5624 2014-01-09 20:56:06Z sra $
# 
# Copyright (C) 2012 Internet Systems Consortium, Inc. ("ISC")
# 
# Permission to use, copy, modify, and/or distribute this software for any
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
Compare rcynic.xml files, tell the user what became invalid, and why.
"""

import sys

try:
  from lxml.etree            import ElementTree
except ImportError:
  from xml.etree.ElementTree import ElementTree

class Object(object):

  def __init__(self, session, uri):
    self.session = session
    self.uri = uri
    self.labels = []

  def add(self, label):
    self.labels.append(label)

  def __cmp__(self, other):
    return cmp(self.labels, other.labels)

  @property
  def accepted(self):
    return "object_accepted" in self.labels

class Session(dict):

  def __init__(self, name):
    self.name = name
    tree = ElementTree(file = name)
    labels = tuple((elt.tag.strip(), elt.text.strip()) for elt in tree.find("labels"))
    self.labels = tuple(pair[0] for pair in labels)
    self.descrs = dict(labels)
    self.date = tree.getroot().get("date")
    for elt in tree.findall("validation_status"):
      status = elt.get("status")
      uri = elt.text.strip()
      if status.startswith("rsync_transfer_") or elt.get("generation") != "current":
        continue
      if uri not in self:
        self[uri] = Object(self, uri)
      self[uri].add(status)

skip_labels = frozenset(("object_accepted", "object_rejected"))

old_db = new_db = None

for arg in sys.argv[1:]:

  old_db = new_db
  new_db = Session(arg)
  if old_db is None:
    continue

  old_uris = frozenset(old_db)
  new_uris = frozenset(new_db)

  for uri in sorted(old_uris - new_uris):
    print new_db.date, uri, "dropped"

  for uri in sorted(old_uris & new_uris):
    old = old_db[uri]
    new = new_db[uri]
    if old.accepted and not new.accepted:
      print new_db.date, uri, "invalid"
      labels = frozenset(new.labels) - frozenset(old.labels) - skip_labels
      for label in new.labels:
        if label in labels:
          print " ", new_db.descrs[label]
