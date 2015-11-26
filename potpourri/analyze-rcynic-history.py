# $Id: analyze-rcynic-history.py 6104 2015-10-09 03:00:38Z sra $
# 
# Copyright (C) 2011-2012  Internet Systems Consortium ("ISC")
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
Parse traffic data out of rynic XML output, whack it a bit, print some
summaries and run gnuplot to draw some pictures.
"""

plot_all_hosts = False

window_hours = 72

import mailbox
import sys
import urlparse
import os
import datetime
import subprocess
import shelve

from xml.etree.cElementTree import (ElementTree as ElementTree,
                                    fromstring  as ElementTreeFromString)

def parse_utc(s):
  return datetime.datetime.strptime(s, "%Y-%m-%dT%H:%M:%SZ")

class Rsync_History(object):
  """
  An Rsync_History object represents one rsync connection.
  """

  def __init__(self, elt):
    self.error = elt.get("error")
    self.uri = elt.text.strip()
    self.hostname = urlparse.urlparse(self.uri).hostname or None
    self.elapsed = parse_utc(elt.get("finished")) - parse_utc(elt.get("started"))

class Host(object):
  """
  A host object represents all the data collected for one host.  Note
  that it (usually) contains a list of all the sessions in which this
  host appears.
  """

  def __init__(self, hostname, session_id):
    self.hostname = hostname
    self.session_id = session_id
    self.elapsed = datetime.timedelta(0)
    self.connection_count = 0
    self.dead_connections = 0
    self.uris = set()
    self.total_connection_time = datetime.timedelta(0)

  def add_rsync_history(self, h):
    self.connection_count      += 1
    self.elapsed               += h.elapsed
    self.dead_connections      += int(h.error is not None)
    self.total_connection_time += h.elapsed

  def add_uri(self, u):
    self.uris.add(u)

  def finalize(self):
    self.object_count = len(self.uris)
    del self.uris

  @property
  def failed(self):
    return 1 if self.dead_connections else 0

  @property
  def seconds_per_object(self):
    if self.failed:
      return None
    else:
      return float(self.elapsed.days * 24 * 60 * 60 +
                   self.elapsed.seconds +
                   self.elapsed.microseconds / 10**6) / float(self.object_count)

  @property
  def objects_per_connection(self):
    if self.failed:
      return None 
    else:
      return float(self.object_count) / float(self.connection_count)

  @property
  def average_connection_time(self):
    return float(self.total_connection_time.days * 24 * 60 * 60 +
                 self.total_connection_time.seconds +
                 self.total_connection_time.microseconds / 10**6) / float(self.connection_count)

  class Format(object):

    def __init__(self, attr, title, fmt, ylabel = ""):
      self.attr = attr
      self.title = title
      self.width = len(title) - int("%" in fmt)
      self.fmt = "%%%d%s" % (self.width, fmt)
      self.oops = "*" * self.width
      self.ylabel = ylabel

    def __call__(self, obj):
      try:
        value = getattr(obj, self.attr)
        return None if value is None else self.fmt % value
      except ZeroDivisionError:
        return self.oops

  format = (Format("connection_count",        "Connections",        "d",     "Connections To Repository (Per Session)"),
            Format("object_count",            "Objects",            "d",     "Objects In Repository (Distinct URIs Per Session)"),
            Format("objects_per_connection",  "Objects/Connection", ".3f",   "Objects In Repository / Connections To Repository"),
            Format("seconds_per_object",      "Seconds/Object",     ".3f",   "Seconds To Transfer / Object (Average Per Session)"),
            Format("failure_rate_running",    "Failure Rate",       ".3f%%", "Sessions With Failed Connections Within Last %d Hours" % window_hours),
            Format("average_connection_time", "Average Connection", ".3f",   "Seconds / Connection (Average Per Session)"),
            Format("hostname",                "Hostname",           "s"))

  format_dict = dict((fmt.attr, fmt) for fmt in format)

  def format_field(self, name):
    result = self.format_dict[name](self)
    return None if result is None else result.strip()

class Session(dict):
  """
  A session corresponds to one XML file.  This is a dictionary of Host
  objects, keyed by hostname.
  """

  def __init__(self, session_id, msg_key):
    self.session_id = session_id
    self.msg_key = msg_key
    self.date = parse_utc(session_id)
    self.calculated_failure_history = False

  @property
  def hostnames(self):
    return set(self.iterkeys())

  def get_plot_row(self, name, hostnames):
    return (self.session_id,) + tuple(self[h].format_field(name) if h in self else "" for h in hostnames)

  def add_rsync_history(self, h):
    if h.hostname not in self:
      self[h.hostname] = Host(h.hostname, self.session_id)
    self[h.hostname].add_rsync_history(h)

  def add_uri(self, u):
    h = urlparse.urlparse(u).hostname
    if h and h in self:
      self[h].add_uri(u)

  def finalize(self):
    for h in self.itervalues():
      h.finalize()

  def calculate_failure_history(self, sessions):
    start = self.date - datetime.timedelta(hours = window_hours)
    sessions = tuple(s for s in sessions if s.date <= self.date and s.date > start)
    for hostname, h in self.iteritems():
      i = n = 0
      for s in sessions:
        if hostname in s:
          i += s[hostname].failed
          n += 1
      h.failure_rate_running = float(100 * i) / n
    self.calculated_failure_history = True

def plotter(f, hostnames, field, logscale = False):
  plotlines = sorted(session.get_plot_row(field, hostnames) for session in sessions)
  title = Host.format_dict[field].title
  ylabel = Host.format_dict[field].ylabel
  n = len(hostnames) + 1
  assert all(n == len(plotline) for plotline in plotlines)
  if "%%" in Host.format_dict[field].fmt:
    f.write('set format y "%.0f%%"\n')
  else:
    f.write('set format y\n')
  if logscale:
    f.write("set logscale y\n")
  else:
    f.write("unset logscale y\n")
  f.write("""
          set xdata time
          set timefmt '%Y-%m-%dT%H:%M:%SZ'
          #set format x '%m/%d'
          #set format x '%b%d'
          #set format x '%Y-%m-%d'
          set format x '%Y-%m'
          #set title '""" + title + """'
          set ylabel '""" + ylabel + """'
          plot""" + ",".join(" '-' using 1:2 with linespoints pointinterval 500 title '%s'" % h for h in hostnames) + "\n")
  for i in xrange(1, n):
    for plotline in plotlines:
      if plotline[i] is not None:
        f.write("%s %s\n" % (plotline[0], plotline[i].rstrip("%")))
    f.write("e\n")

def plot_hosts(hostnames, fields):
  for field in fields:
    for logscale in (False, True):
      gnuplot = subprocess.Popen(("gnuplot",), stdin = subprocess.PIPE)
      gnuplot.stdin.write("set terminal pdf\n")
      gnuplot.stdin.write("set output '%s/%s-%s.pdf'\n" % (outdir, field, "log" if logscale else "linear"))
      plotter(gnuplot.stdin, hostnames, field, logscale = logscale)
      gnuplot.stdin.close()
      gnuplot.wait()

outdir = "images"

if not os.path.exists(outdir):
  os.makedirs(outdir)

mb = mailbox.Maildir("/u/sra/rpki/rcynic-xml", factory = None, create = False)

if sys.platform == "darwin":            # Sigh
  shelf = shelve.open("rcynic-xml", "c")
else:
  shelf = shelve.open("rcynic-xml.db", "c")

sessions = []

latest = None
parsed = 0

for i, key in enumerate(mb.iterkeys(), 1):
  sys.stderr.write("\r%s %d/%d/%d..." % ("|\\-/"[i & 3], parsed, i, len(mb)))

  if key in shelf:
    session = shelf[key]

  else:
    sys.stderr.write("%s..." % key)
    assert not mb[key].is_multipart()
    input = ElementTreeFromString(mb[key].get_payload())
    date = input.get("date")
    sys.stderr.write("%s..." % date)
    session = Session(date, key)
    for elt in input.findall("rsync_history"):
      session.add_rsync_history(Rsync_History(elt))
    for elt in input.findall("validation_status"):
      if elt.get("generation") == "current":
        session.add_uri(elt.text.strip())
    session.finalize()
    shelf[key] = session
    parsed += 1

  sessions.append(session)
  if latest is None or session.session_id > latest.session_id:
    latest = session

sys.stderr.write("\n")

shelf.sync()

for session in sessions:
  if not getattr(session, "calculated_failure_history", False):
    session.calculate_failure_history(sessions)
    shelf[session.msg_key] = session

if plot_all_hosts:
  hostnames = sorted(reduce(lambda x, y: x | y,
                            (s.hostnames for s in sessions),
                            set()))

else:
  hostnames = ("rpki.apnic.net", "rpki.ripe.net", "repository.lacnic.net", "rpki.afrinic.net", "rpki.arin.net",
               #"localcert.ripe.net", "arin.rpki.net", "repo0.rpki.net", "rgnet.rpki.net",
               "ca0.rpki.net")

plot_hosts(hostnames, [fmt.attr for fmt in Host.format if fmt.attr != "hostname"])

if latest is not None:
  f = open("rcynic.xml", "wb")
  f.write(mb[latest.msg_key].get_payload())
  f.close()

shelf.close()
