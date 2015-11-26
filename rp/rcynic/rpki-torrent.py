#!/usr/bin/env python
#
# $Id: rpki-torrent.py 5856 2014-05-31 18:32:19Z sra $
#
# Copyright (C) 2013--2014  Dragon Research Labs ("DRL")
# Portions copyright (C) 2012  Internet Systems Consortium ("ISC")
#
# Permission to use, copy, modify, and distribute this software for any
# purpose with or without fee is hereby granted, provided that the above
# copyright notices and this permission notice appear in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND DRL AND ISC DISCLAIM ALL
# WARRANTIES WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS.  IN NO EVENT SHALL DRL OR
# ISC BE LIABLE FOR ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL
# DAMAGES OR ANY DAMAGES WHATSOEVER RESULTING FROM LOSS OF USE, DATA
# OR PROFITS, WHETHER IN AN ACTION OF CONTRACT, NEGLIGENCE OR OTHER
# TORTIOUS ACTION, ARISING OUT OF OR IN CONNECTION WITH THE USE OR
# PERFORMANCE OF THIS SOFTWARE.

import urllib2
import httplib
import socket
import ssl
import urlparse
import zipfile
import sys
import os
import email.utils
import base64
import hashlib
import subprocess
import syslog
import traceback
import ConfigParser
import stat
import time
import errno
import fcntl
import argparse
import smtplib
import email.mime.text

import transmissionrpc

tr_env_vars = ("TR_TORRENT_DIR", "TR_TORRENT_ID", "TR_TORRENT_NAME")

class WrongServer(Exception):
  "Hostname not in X.509v3 subjectAltName extension."

class UnexpectedRedirect(Exception):
  "Unexpected HTTP redirect."

class WrongMode(Exception):
  "Wrong operation for mode."

class BadFormat(Exception):
  "Zip file does not match our expectations."

class InconsistentEnvironment(Exception):
  "Environment variables received from Transmission aren't consistent."

class TorrentNotReady(Exception):
  "Torrent is not ready for checking."

class TorrentDoesNotMatchManifest(Exception):
  "Retrieved torrent does not match manifest."

class TorrentNameDoesNotMatchURL(Exception):
  "Torrent name doesn't uniquely match a URL."

class CouldNotFindTorrents(Exception):
  "Could not find torrent(s) with given name(s)."

class UseTheSourceLuke(Exception):
  "Use The Source, Luke."

cfg = None

def main():
  try:
    syslog_flags = syslog.LOG_PID
    if os.isatty(sys.stderr.fileno()):
      syslog_flags |= syslog.LOG_PERROR
    syslog.openlog("rpki-torrent", syslog_flags)

    # If I seriously expected this script to get a lot of further use,
    # I might rewrite this using subparsers, but it'd be a bit tricky
    # as argparse doesn't support making the subparser argument
    # optional and transmission gives no sane way to provide arguments
    # when running a completion script.  So, for the moment, let's
    # just fix the bugs accidently introduced while converting the
    # universe to argparse without making any radical changes to the
    # program structure here, even if the result looks kind of klunky.

    parser = argparse.ArgumentParser(description = __doc__)
    parser.add_argument("-c", "--config",
                        help = "configuration file")
    parser.add_argument("action", choices = ("poll", "generate", "mirror"), nargs = "?",
                        help = "action to take")
    args = parser.parse_args()

    global cfg
    cfg = MyConfigParser()
    cfg.read(args.config or
             [os.path.join(dn, fn)
              for fn in ("rcynic.conf", "rpki.conf")
              for dn in ("/var/rcynic/etc", "/usr/local/etc", "/etc")])

    if cfg.act_as_generator:
      if args.action == "generate":
        generator_main()
      elif args.action == "mirror":
        mirror_main()
      else:
        raise UseTheSourceLuke
    else:
      if args.action is None and all(v in os.environ for v in tr_env_vars):
        torrent_completion_main()
      elif args.action == "poll":
        poll_main()
      else:
        raise UseTheSourceLuke

  except:
    for line in traceback.format_exc().splitlines():
      syslog.syslog(line)
    sys.exit(1)


def generator_main():
  import paramiko

  class SFTPClient(paramiko.SFTPClient):
    def atomic_rename(self, oldpath, newpath):
      oldpath = self._adjust_cwd(oldpath)
      newpath = self._adjust_cwd(newpath)
      self._log(paramiko.common.DEBUG, 'atomic_rename(%r, %r)' % (oldpath, newpath))
      self._request(paramiko.sftp.CMD_EXTENDED, "posix-rename@openssh.com", oldpath, newpath)

  z = ZipFile(url = cfg.generate_url, dn = cfg.zip_dir)
  client = TransmissionClient()

  client.remove_torrents(z.torrent_name)

  download_dir = client.get_session().download_dir
  torrent_dir = os.path.join(download_dir, z.torrent_name)
  torrent_file = os.path.join(cfg.zip_dir, z.torrent_name + ".torrent")


  syslog.syslog("Synchronizing local data from %s to %s" % (cfg.unauthenticated, torrent_dir))
  subprocess.check_call((cfg.rsync_prog, "--archive", "--delete",
                         os.path.normpath(cfg.unauthenticated) + "/",
                         os.path.normpath(torrent_dir) + "/"))

  syslog.syslog("Creating %s" % torrent_file)
  try:
    os.unlink(torrent_file)
  except OSError, e:
    if e.errno != errno.ENOENT:
      raise
  ignore_output_for_now = subprocess.check_output( # pylint: disable=W0612
    (cfg.mktorrent_prog,
     "-a", cfg.tracker_url,
     "-c", "RPKI unauthenticated data snapshot generated by rpki-torrent",
     "-o", torrent_file,
     torrent_dir))

  syslog.syslog("Generating manifest")
  manifest = create_manifest(download_dir, z.torrent_name)

  syslog.syslog("Loading %s with unlimited seeding" % torrent_file)
  f = open(torrent_file, "rb")
  client.add(base64.b64encode(f.read()))
  f.close()
  client.unlimited_seeding(z.torrent_name)

  syslog.syslog("Creating upload connection")
  ssh = paramiko.Transport((cfg.sftp_host, cfg.sftp_port))
  try:
    hostkeys = paramiko.util.load_host_keys(cfg.sftp_hostkey_file)[cfg.sftp_host]["ssh-rsa"]
  except ConfigParser.Error:
    hostkeys = None
  ssh.connect(
    username = cfg.sftp_user,
    hostkey  = hostkeys,
    pkey     = paramiko.RSAKey.from_private_key_file(cfg.sftp_private_key_file))
  sftp = SFTPClient.from_transport(ssh)

  zip_filename = os.path.join("data", os.path.basename(z.filename))
  zip_tempname = zip_filename + ".new"

  syslog.syslog("Creating %s" % zip_tempname)
  f = sftp.open(zip_tempname, "wb")
  z.set_output_stream(f)

  syslog.syslog("Writing %s to zip" % torrent_file)
  z.write(
    torrent_file,
    arcname = os.path.basename(torrent_file),
    compress_type = zipfile.ZIP_DEFLATED)

  manifest_name = z.torrent_name + ".manifest"

  syslog.syslog("Writing %s to zip" % manifest_name)
  zi = zipfile.ZipInfo(manifest_name, time.gmtime()[:6])
  zi.external_attr = (stat.S_IFREG | 0644) << 16
  zi.internal_attr = 1                  # Text, not binary
  z.writestr(zi,
             "".join("%s %s\n" % (v, k) for k, v in manifest.iteritems()),
             zipfile.ZIP_DEFLATED)

  syslog.syslog("Closing %s and renaming to %s" % (zip_tempname, zip_filename))
  z.close()
  f.close()
  sftp.atomic_rename(zip_tempname, zip_filename)

  syslog.syslog("Closing upload connection")
  ssh.close()

def mirror_main():
  client = TransmissionClient()
  torrent_names = []

  for zip_url in cfg.zip_urls:
    if zip_url != cfg.generate_url:
      z = ZipFile(url = zip_url, dn = cfg.zip_dir, ta = cfg.zip_ta)
      if z.fetch():
        client.remove_torrents(z.torrent_name)
        syslog.syslog("Mirroring torrent %s" % z.torrent_name)
        client.add(z.get_torrent())
        torrent_names.append(z.torrent_name)

  if torrent_names:
    client.unlimited_seeding(*torrent_names)


def poll_main():
  for zip_url in cfg.zip_urls:

    z = ZipFile(url = zip_url, dn = cfg.zip_dir, ta = cfg.zip_ta)
    client = TransmissionClient()

    if z.fetch():
      client.remove_torrents(z.torrent_name)
      syslog.syslog("Adding torrent %s" % z.torrent_name)
      client.add(z.get_torrent())

    elif cfg.run_rcynic_anyway:
      run_rcynic(client, z)


def torrent_completion_main():
  torrent_name = os.getenv("TR_TORRENT_NAME")
  torrent_id = int(os.getenv("TR_TORRENT_ID"))

  z = ZipFile(url = cfg.find_url(torrent_name), dn = cfg.zip_dir, ta = cfg.zip_ta)
  client = TransmissionClient()
  torrent = client.info([torrent_id]).popitem()[1]

  if torrent.name != torrent_name:
    raise InconsistentEnvironment("Torrent name %s does not match ID %d" % (torrent_name, torrent_id))

  if z.torrent_name != torrent_name:
    raise InconsistentEnvironment("Torrent name %s does not match torrent name in zip file %s" % (torrent_name, z.torrent_name))

  if torrent is None or torrent.progress != 100:
    raise TorrentNotReady("Torrent %s not ready for checking, how did I get here?" % torrent_name)

  log_email("Download complete %s" % z.url)

  run_rcynic(client, z)


def run_rcynic(client, z):
  """
  Run rcynic and any post-processing we might want.
  """

  if cfg.lockfile is not None:
    syslog.syslog("Acquiring lock %s" % cfg.lockfile)
    lock = os.open(cfg.lockfile, os.O_WRONLY | os.O_CREAT, 0600)
    fcntl.flock(lock, fcntl.LOCK_EX)
  else:
    lock = None

  syslog.syslog("Checking manifest against disk")

  download_dir = client.get_session().download_dir

  manifest_from_disk = create_manifest(download_dir, z.torrent_name)
  manifest_from_zip = z.get_manifest()

  excess_files = set(manifest_from_disk) - set(manifest_from_zip)
  for fn in excess_files:
    del manifest_from_disk[fn]

  if manifest_from_disk != manifest_from_zip:
    raise TorrentDoesNotMatchManifest("Manifest for torrent %s does not match what we got" %
                                      z.torrent_name)

  if excess_files:
    syslog.syslog("Cleaning up excess files")
  for fn in excess_files:
    os.unlink(os.path.join(download_dir, fn))

  syslog.syslog("Running rcynic")
  log_email("Starting rcynic %s" % z.url)
  subprocess.check_call((cfg.rcynic_prog,
                         "-c", cfg.rcynic_conf,
                         "-u", os.path.join(client.get_session().download_dir, z.torrent_name)))
  log_email("Completed rcynic %s" % z.url)

  for cmd in cfg.post_rcynic_commands:
    syslog.syslog("Running post-rcynic command: %s" % cmd)
    subprocess.check_call(cmd, shell = True)

  if lock is not None:
    syslog.syslog("Releasing lock %s" % cfg.lockfile)
    os.close(lock)

# See http://www.minstrel.org.uk/papers/sftp/ for details on how to
# set up safe upload-only SFTP directories on the server.  In
# particular http://www.minstrel.org.uk/papers/sftp/builtin/ is likely
# to be the right path.


class ZipFile(object):
  """
  Augmented version of standard python zipfile.ZipFile class, with
  some extra methods and specialized capabilities.

  All methods of the standard zipfile.ZipFile class are supported, but
  the constructor arguments are different, and opening the zip file
  itself is deferred until a call which requires this, since the file
  may first need to be fetched via HTTPS.
  """

  def __init__(self, url, dn, ta = None, verbose = True):
    self.url = url
    self.dir = dn
    self.ta = ta
    self.verbose = verbose
    self.filename = os.path.join(dn, os.path.basename(url))
    self.changed = False
    self.zf = None
    self.peercert = None
    self.torrent_name, zip_ext = os.path.splitext(os.path.basename(url))
    if zip_ext != ".zip":
      raise BadFormat


  def __getattr__(self, name):
    if self.zf is None:
      self.zf = zipfile.ZipFile(self.filename)
    return getattr(self.zf, name)


  def build_opener(self):
    """
    Voodoo to create a urllib2.OpenerDirector object with TLS
    certificate checking enabled and a hook to set self.peercert so
    our caller can check the subjectAltName field.

    You probably don't want to look at this if you can avoid it.
    """

    assert self.ta is not None

    # Yes, we're constructing one-off classes.  Look away, look away.

    class HTTPSConnection(httplib.HTTPSConnection):
      zip = self
      def connect(self):
        sock = socket.create_connection((self.host, self.port), self.timeout)
        if getattr(self, "_tunnel_host", None):
          self.sock = sock
          self._tunnel()
        self.sock = ssl.wrap_socket(sock,
                                    keyfile = self.key_file,
                                    certfile = self.cert_file,
                                    cert_reqs = ssl.CERT_REQUIRED,
                                    ssl_version = ssl.PROTOCOL_TLSv1,
                                    ca_certs = self.zip.ta)
        self.zip.peercert = self.sock.getpeercert()

    class HTTPSHandler(urllib2.HTTPSHandler):
      def https_open(self, req):
        return self.do_open(HTTPSConnection, req)

    return urllib2.build_opener(HTTPSHandler)


  def check_subjectAltNames(self):
    """
    Check self.peercert against URL to make sure we were talking to
    the right HTTPS server.
    """

    hostname = urlparse.urlparse(self.url).hostname
    subjectAltNames = set(i[1]
                          for i in self.peercert.get("subjectAltName", ())
                          if i[0] == "DNS")
    if hostname not in subjectAltNames:
      raise WrongServer


  def download_file(self, r, bufsize = 4096):
    """
    Downloaded file to disk.
    """

    tempname = self.filename + ".new"
    f = open(tempname, "wb")
    n = int(r.info()["Content-Length"])
    for i in xrange(0, n - bufsize, bufsize): # pylint: disable=W0612
      f.write(r.read(bufsize))
    f.write(r.read())
    f.close()
    mtime = email.utils.mktime_tz(email.utils.parsedate_tz(r.info()["Last-Modified"]))
    os.utime(tempname, (mtime, mtime))
    os.rename(tempname, self.filename)


  def set_output_stream(self, stream):
    """
    Set up this zip file for writing to a network stream.
    """

    assert self.zf is None
    self.zf = zipfile.ZipFile(stream, "w")


  def fetch(self):
    """
    Fetch zip file from URL given to constructor.
    """

    headers = { "User-Agent" : "rpki-torrent" }
    try:
      headers["If-Modified-Since"] = email.utils.formatdate(
        os.path.getmtime(self.filename), False, True)
    except OSError:
      pass

    syslog.syslog("Checking %s..." % self.url)
    try:
      r = self.build_opener().open(urllib2.Request(self.url, None, headers))
      syslog.syslog("%s has changed, starting download" % self.url)
      self.changed = True
      log_email("Downloading %s" % self.url)
    except urllib2.HTTPError, e:
      if e.code == 304:
        syslog.syslog("%s has not changed" % self.url)
      elif e.code == 404:
        syslog.syslog("%s does not exist" % self.url)
      else:
        raise
      r = None

    self.check_subjectAltNames()

    if r is not None and r.geturl() != self.url:
      raise UnexpectedRedirect

    if r is not None:
      self.download_file(r)
      r.close()

    return self.changed


  def check_format(self):
    """
    Make sure that format of zip file matches our preconceptions: it
    should contain two files, one of which is the .torrent file, the
    other is the manifest, with names derived from the torrent name
    inferred from the URL.
    """

    if set(self.namelist()) != set((self.torrent_name + ".torrent", self.torrent_name + ".manifest")):
      raise BadFormat


  def get_torrent(self):
    """
    Extract torrent file from zip file, encoded in Base64 because
    that's what the transmisionrpc library says it wants.
    """

    self.check_format()
    return base64.b64encode(self.read(self.torrent_name + ".torrent"))


  def get_manifest(self):
    """
    Extract manifest from zip file, as a dictionary.

    For the moment we're fixing up the internal file names from the
    format that the existing shell-script prototype uses, but this
    should go away once this program both generates and checks the
    manifests.
    """

    self.check_format()
    result = {}
    for line in self.open(self.torrent_name + ".manifest"):
      h, fn = line.split()
      #
      # Fixup for earlier manifest format, this should go away
      if not fn.startswith(self.torrent_name):
        fn = os.path.normpath(os.path.join(self.torrent_name, fn))
      #
      result[fn] = h
    return result


def create_manifest(topdir, torrent_name):
  """
  Generate a manifest, expressed as a dictionary.
  """

  result = {}
  topdir = os.path.abspath(topdir)
  for dirpath, dirnames, filenames in os.walk(os.path.join(topdir, torrent_name)): # pylint: disable=W0612
    for filename in filenames:
      filename = os.path.join(dirpath, filename)
      f = open(filename, "rb")
      result[os.path.relpath(filename, topdir)] = hashlib.sha256(f.read()).hexdigest()
      f.close()
  return result


def log_email(msg, subj = None):
  try:
    if not msg.endswith("\n"):
      msg += "\n"
    if subj is None:
      subj = msg.partition("\n")[0]
    m = email.mime.text.MIMEText(msg)
    m["Date"]    = time.strftime("%d %b %Y %H:%M:%S +0000", time.gmtime())
    m["From"]    = cfg.log_email
    m["To"]      = cfg.log_email
    m["Subject"] = subj
    s = smtplib.SMTP("localhost")
    s.sendmail(cfg.log_email, [cfg.log_email], m.as_string())
    s.quit()
  except ConfigParser.Error:
    pass


class TransmissionClient(transmissionrpc.client.Client):
  """
  Extension of transmissionrpc.client.Client.
  """

  def __init__(self, **kwargs):
    kwargs.setdefault("address", "127.0.0.1")
    kwargs.setdefault("user",     cfg.transmission_username)
    kwargs.setdefault("password", cfg.transmission_password)
    transmissionrpc.client.Client.__init__(self, **kwargs)


  def find_torrents(self, *names):
    """
    Find torrents with given name(s), return id(s).
    """

    result = [i for i, t in self.list().iteritems() if t.name in names]
    if not result:
      raise CouldNotFindTorrents
    return result


  def remove_torrents(self, *names):
    """
    Remove any torrents with the given name(s).
    """

    try:
      ids = self.find_torrents(*names)
    except CouldNotFindTorrents:
      pass
    else:
      syslog.syslog("Removing torrent%s %s (%s)" % (
        "" if len(ids) == 1 else "s",
        ", ".join(names),
        ", ".join("#%s" % i for i in ids)))
      self.remove(ids)

  def unlimited_seeding(self, *names):
    """
    Set unlimited seeding for specified torrents.
    """

    # Apparently seedRatioMode = 2 means "no limit"
    try:
      self.change(self.find_torrents(*names), seedRatioMode = 2)
    except CouldNotFindTorrents:
      syslog.syslog("Couldn't tweak seedRatioMode, blundering onwards")


class MyConfigParser(ConfigParser.RawConfigParser):

  rpki_torrent_section = "rpki-torrent"

  @property
  def zip_dir(self):
    return self.get(self.rpki_torrent_section, "zip_dir")

  @property
  def zip_ta(self):
    return self.get(self.rpki_torrent_section, "zip_ta")

  @property
  def rcynic_prog(self):
    return self.get(self.rpki_torrent_section, "rcynic_prog")

  @property
  def rcynic_conf(self):
    return self.get(self.rpki_torrent_section, "rcynic_conf")

  @property
  def run_rcynic_anyway(self):
    return self.getboolean(self.rpki_torrent_section, "run_rcynic_anyway")

  @property
  def generate_url(self):
    return self.get(self.rpki_torrent_section, "generate_url")

  @property
  def act_as_generator(self):
    try:
      return self.get(self.rpki_torrent_section, "generate_url") != ""
    except ConfigParser.Error:
      return False

  @property
  def rsync_prog(self):
    return self.get(self.rpki_torrent_section, "rsync_prog")

  @property
  def mktorrent_prog(self):
    return self.get(self.rpki_torrent_section, "mktorrent_prog")

  @property
  def tracker_url(self):
    return self.get(self.rpki_torrent_section, "tracker_url")

  @property
  def sftp_host(self):
    return self.get(self.rpki_torrent_section, "sftp_host")

  @property
  def sftp_port(self):
    try:
      return self.getint(self.rpki_torrent_section, "sftp_port")
    except ConfigParser.Error:
      return 22

  @property
  def sftp_user(self):
    return self.get(self.rpki_torrent_section, "sftp_user")

  @property
  def sftp_hostkey_file(self):
    return self.get(self.rpki_torrent_section, "sftp_hostkey_file")

  @property
  def sftp_private_key_file(self):
    return self.get(self.rpki_torrent_section, "sftp_private_key_file")

  @property
  def lockfile(self):
    try:
      return self.get(self.rpki_torrent_section, "lockfile")
    except ConfigParser.Error:
      return None

  @property
  def unauthenticated(self):
    try:
      return self.get(self.rpki_torrent_section, "unauthenticated")
    except ConfigParser.Error:
      return self.get("rcynic", "unauthenticated")

  @property
  def log_email(self):
    return self.get(self.rpki_torrent_section, "log_email")

  @property
  def transmission_username(self):
    try:
      return self.get(self.rpki_torrent_section, "transmission_username")
    except ConfigParser.Error:
      return None

  @property
  def transmission_password(self):
    try:
      return self.get(self.rpki_torrent_section, "transmission_password")
    except ConfigParser.Error:
      return None

  def multioption_iter(self, name, getter = None):
    if getter is None:
      getter = self.get
    if self.has_option(self.rpki_torrent_section, name):
      yield getter(self.rpki_torrent_section, name)
    name += "."
    names = [i for i in self.options(self.rpki_torrent_section) if i.startswith(name) and i[len(name):].isdigit()]
    names.sort(key = lambda s: int(s[len(name):])) # pylint: disable=W0631
    for name in names:
      yield getter(self.rpki_torrent_section, name)

  @property
  def zip_urls(self):
    return self.multioption_iter("zip_url")

  @property
  def post_rcynic_commands(self):
    return self.multioption_iter("post_rcynic_command")

  def find_url(self, torrent_name):
    urls = [u for u in self.zip_urls
            if os.path.splitext(os.path.basename(u))[0] == torrent_name]
    if len(urls) != 1:
      raise TorrentNameDoesNotMatchURL("Can't find URL matching torrent name %s" % torrent_name)
    return urls[0]


if __name__ == "__main__":
  main()
