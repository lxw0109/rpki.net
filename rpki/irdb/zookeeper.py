# $Id: zookeeper.py 6027 2014-11-19 19:52:54Z sra $
#
# Copyright (C) 2013--2014  Dragon Research Labs ("DRL")
# Portions copyright (C) 2009--2012  Internet Systems Consortium ("ISC")
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

"""
Management code for the IRDB.
"""

# pylint: disable=W0612,C0325

import os
import copy
import types
import rpki.config
import rpki.sundial
import rpki.oids
import rpki.http
import rpki.resource_set
import rpki.relaxng
import rpki.left_right
import rpki.x509
import rpki.async
import rpki.irdb
import django.db.transaction

from lxml.etree import (Element, SubElement, ElementTree,
                        tostring as ElementToString)

from rpki.csv_utils import csv_reader

# XML namespace and protocol version for OOB setup protocol.  The name
# is historical and may change before we propose this as the basis for
# a standard.

myrpki_xmlns   = rpki.relaxng.myrpki.xmlns
myrpki_version = rpki.relaxng.myrpki.version

# XML namespace and protocol version for router certificate requests.
# We probably ought to be pulling this sort of thing from the schema,
# with an assertion to make sure that we understand the current
# protocol version number, but just copy what we did for myrpki until
# I'm ready to rewrite the rpki.relaxng code.

routercert_xmlns   = rpki.relaxng.router_certificate.xmlns
routercert_version = rpki.relaxng.router_certificate.version

myrpki_section = "myrpki"
irdbd_section  = "irdbd"
rpkid_section  = "rpkid"
pubd_section   = "pubd"
rootd_section  = "rootd"

# A whole lot of exceptions

class HandleNotSet(Exception):          "Handle not set."
class MissingHandle(Exception):         "Missing handle."
class CouldntTalkToDaemon(Exception):   "Couldn't talk to daemon."
class BadXMLMessage(Exception):         "Bad XML message."
class PastExpiration(Exception):        "Expiration date has already passed."
class CantRunRootd(Exception):          "Can't run rootd."


def B64Element(e, tag, obj, **kwargs):
  """
  Create an XML element containing Base64 encoded data taken from a
  DER object.
  """

  if e is None:
    se = Element(tag, **kwargs)
  else:
    se = SubElement(e, tag, **kwargs)
  if e is not None and e.text is None:
    e.text = "\n"
  se.text = "\n" + obj.get_Base64()
  se.tail = "\n"
  return se

class PEM_writer(object):
  """
  Write PEM files to disk, keeping track of which ones we've already
  written and setting the file mode appropriately.

  Comparing the old file with what we're about to write serves no real
  purpose except to calm users who find repeated messages about
  writing the same file confusing.
  """

  def __init__(self, logstream = None):
    self.wrote = set()
    self.logstream = logstream

  def __call__(self, filename, obj, compare = True):
    filename = os.path.realpath(filename)
    if filename in self.wrote:
      return
    tempname = filename
    pem = obj.get_PEM()
    if not filename.startswith("/dev/"):
      try:
        if compare and pem == open(filename, "r").read():
          return
      except:                           # pylint: disable=W0702
        pass
      tempname += ".%s.tmp" % os.getpid()
    mode = 0400 if filename.endswith(".key") else 0444
    if self.logstream is not None:
      self.logstream.write("Writing %s\n" % filename)
    f = os.fdopen(os.open(tempname, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, mode), "w")
    f.write(pem)
    f.close()
    if tempname != filename:
      os.rename(tempname, filename)
    self.wrote.add(filename)


def etree_read(filename):
  """
  Read an etree from a file, verifying then stripping XML namespace
  cruft.
  """

  e = ElementTree(file = filename).getroot()
  rpki.relaxng.myrpki.assertValid(e)
  for i in e.getiterator():
    if i.tag.startswith(myrpki_xmlns):
      i.tag = i.tag[len(myrpki_xmlns):]
    else:
      raise BadXMLMessage("XML tag %r is not in namespace %r" % (i.tag, myrpki_xmlns[1:-1]))
  return e


class etree_wrapper(object):
  """
  Wrapper for ETree objects so we can return them as function results
  without requiring the caller to understand much about them.

  """

  def __init__(self, e, msg = None, debug = False):
    self.msg = msg
    e = copy.deepcopy(e)
    e.set("version", myrpki_version)
    for i in e.getiterator():
      if i.tag[0] != "{":
        i.tag = myrpki_xmlns + i.tag
      assert i.tag.startswith(myrpki_xmlns)
    if debug:
      print ElementToString(e)
    rpki.relaxng.myrpki.assertValid(e)
    self.etree = e

  def __str__(self):
    return ElementToString(self.etree)

  def save(self, filename, logstream = None):
    filename = os.path.realpath(filename)
    tempname = filename
    if not filename.startswith("/dev/"):
      tempname += ".%s.tmp" % os.getpid()
    ElementTree(self.etree).write(tempname)
    if tempname != filename:
      os.rename(tempname, filename)
    if logstream is not None:
      logstream.write("Wrote %s\n" % filename)
      if self.msg is not None:
        logstream.write(self.msg + "\n")

  @property
  def file(self):
    from cStringIO import StringIO
    return StringIO(ElementToString(self.etree))


class Zookeeper(object):

  ## @var show_xml
  # Whether to show XML for debugging

  show_xml = False

  def __init__(self, cfg = None, handle = None, logstream = None, disable_signal_handlers = False):

    if cfg is None:
      cfg = rpki.config.parser()

    if handle is None:
      handle = cfg.get("handle", section = myrpki_section)

    self.cfg = cfg

    self.logstream = logstream
    self.disable_signal_handlers = disable_signal_handlers

    self.run_rpkid = cfg.getboolean("run_rpkid", section = myrpki_section)
    self.run_pubd  = cfg.getboolean("run_pubd", section = myrpki_section)
    self.run_rootd = cfg.getboolean("run_rootd", section = myrpki_section)

    if self.run_rootd and (not self.run_pubd or not self.run_rpkid):
      raise CantRunRootd("Can't run rootd unless also running rpkid and pubd")

    self.default_repository = cfg.get("default_repository", "", section = myrpki_section)
    self.pubd_contact_info = cfg.get("pubd_contact_info", "", section = myrpki_section)

    self.rsync_module = cfg.get("publication_rsync_module", section = myrpki_section)
    self.rsync_server = cfg.get("publication_rsync_server", section = myrpki_section)

    self.reset_identity(handle)


  def reset_identity(self, handle):
    """
    Select handle of current resource holding entity.
    """

    if handle is None:
      raise MissingHandle
    self.handle = handle


  def set_logstream(self, logstream):
    """
    Set log stream for this Zookeeper.  The log stream is a file-like
    object, or None to suppress all logging.
    """

    self.logstream = logstream


  def log(self, msg):
    """
    Send some text to this Zookeeper's log stream, if one is set.
    """

    if self.logstream is not None:
      self.logstream.write(msg)
      self.logstream.write("\n")


  @property
  def resource_ca(self):
    """
    Get ResourceHolderCA object associated with current handle.
    """

    if self.handle is None:
      raise HandleNotSet
    return rpki.irdb.ResourceHolderCA.objects.get(handle = self.handle)


  @property
  def server_ca(self):
    """
    Get ServerCA object.
    """

    return rpki.irdb.ServerCA.objects.get()


  @django.db.transaction.commit_on_success
  def initialize_server_bpki(self):
    """
    Initialize server BPKI portion of an RPKI installation.  Reads the
    configuration file and generates the initial BPKI server
    certificates needed to start daemons.
    """

    if self.run_rpkid or self.run_pubd:
      server_ca, created = rpki.irdb.ServerCA.objects.get_or_certify()
      rpki.irdb.ServerEE.objects.get_or_certify(issuer = server_ca, purpose = "irbe")

    if self.run_rpkid:
      rpki.irdb.ServerEE.objects.get_or_certify(issuer = server_ca, purpose = "rpkid")
      rpki.irdb.ServerEE.objects.get_or_certify(issuer = server_ca, purpose = "irdbd")

    if self.run_pubd:
      rpki.irdb.ServerEE.objects.get_or_certify(issuer = server_ca, purpose = "pubd")


  @django.db.transaction.commit_on_success
  def initialize_resource_bpki(self):
    """
    Initialize the resource-holding BPKI for an RPKI installation.
    Returns XML describing the resource holder.

    This method is present primarily for backwards compatibility with
    the old combined initialize() method which initialized both the
    server BPKI and the default resource-holding BPKI in a single
    method call.  In the long run we want to replace this with
    something that takes a handle as argument and creates the
    resource-holding BPKI idenity if needed.
    """

    resource_ca, created = rpki.irdb.ResourceHolderCA.objects.get_or_certify(handle = self.handle)
    return self.generate_identity()


  def initialize(self):
    """
    Backwards compatibility wrapper: calls initialize_server_bpki()
    and initialize_resource_bpki(), returns latter's result.
    """

    self.initialize_server_bpki()
    return self.initialize_resource_bpki()


  def generate_identity(self):
    """
    Generate identity XML.  Broken out of .initialize() because it's
    easier for the GUI this way.
    """

    e = Element("identity", handle = self.handle)
    B64Element(e, "bpki_ta", self.resource_ca.certificate)
    return etree_wrapper(e, msg = 'This is the "identity" file you will need to send to your parent')


  @django.db.transaction.commit_on_success
  def delete_self(self):
    """
    Delete the ResourceHolderCA object corresponding to the current handle.
    This corresponds to deleting an rpkid <self/> object.

    This code assumes the normal Django cascade-on-delete behavior,
    that is, we assume that deleting the ResourceHolderCA object
    deletes all the subordinate objects that refer to it via foreign
    key relationships.
    """

    resource_ca = self.resource_ca
    if resource_ca is not None:
      resource_ca.delete()
    else:
      self.log("No such ResourceHolderCA \"%s\"" % self.handle)


  @django.db.transaction.commit_on_success
  def configure_rootd(self):

    assert self.run_rpkid and self.run_pubd and self.run_rootd

    rpki.irdb.Rootd.objects.get_or_certify(
      issuer = self.resource_ca,
      service_uri = "http://localhost:%s/" % self.cfg.get("rootd_server_port", section = myrpki_section))

    return self.generate_rootd_repository_offer()


  def generate_rootd_repository_offer(self):
    """
    Generate repository offer for rootd.  Split out of
    configure_rootd() because that's easier for the GUI.
    """

    # The following assumes we'll set up the respository manually.
    # Not sure this is a reasonable assumption, particularly if we
    # ever fix rootd to use the publication protocol.

    try:
      self.resource_ca.repositories.get(handle = self.handle)
      return None

    except rpki.irdb.Repository.DoesNotExist:
      e = Element("repository", type = "offer", handle = self.handle, parent_handle = self.handle)
      B64Element(e, "bpki_client_ta", self.resource_ca.certificate)
      return etree_wrapper(e, msg = 'This is the "repository offer" file for you to use if you want to publish in your own repository')


  def write_bpki_files(self):
    """
    Write out BPKI certificate, key, and CRL files for daemons that
    need them.
    """

    writer = PEM_writer(self.logstream)

    if self.run_rpkid:
      rpkid = self.server_ca.ee_certificates.get(purpose = "rpkid")
      writer(self.cfg.get("bpki-ta",    section = rpkid_section), self.server_ca.certificate)
      writer(self.cfg.get("rpkid-key",  section = rpkid_section), rpkid.private_key)
      writer(self.cfg.get("rpkid-cert", section = rpkid_section), rpkid.certificate)
      writer(self.cfg.get("irdb-cert",  section = rpkid_section),
             self.server_ca.ee_certificates.get(purpose = "irdbd").certificate)
      writer(self.cfg.get("irbe-cert",  section = rpkid_section),
             self.server_ca.ee_certificates.get(purpose = "irbe").certificate)

    if self.run_pubd:
      pubd = self.server_ca.ee_certificates.get(purpose = "pubd")
      writer(self.cfg.get("bpki-ta",   section = pubd_section), self.server_ca.certificate)
      writer(self.cfg.get("pubd-key",  section = pubd_section), pubd.private_key)
      writer(self.cfg.get("pubd-cert", section = pubd_section), pubd.certificate)
      writer(self.cfg.get("irbe-cert", section = pubd_section),
             self.server_ca.ee_certificates.get(purpose = "irbe").certificate)

    if self.run_rootd:
      try:
        rootd = rpki.irdb.ResourceHolderCA.objects.get(handle = self.handle).rootd
        writer(self.cfg.get("bpki-ta",         section = rootd_section), self.server_ca.certificate)
        writer(self.cfg.get("rootd-bpki-crl",  section = rootd_section), self.server_ca.latest_crl)
        writer(self.cfg.get("rootd-bpki-key",  section = rootd_section), rootd.private_key)
        writer(self.cfg.get("rootd-bpki-cert", section = rootd_section), rootd.certificate)
        writer(self.cfg.get("child-bpki-cert", section = rootd_section), rootd.issuer.certificate)
      except rpki.irdb.ResourceHolderCA.DoesNotExist:
        self.log("rootd enabled but resource holding entity not yet configured, skipping rootd setup")
      except rpki.irdb.Rootd.DoesNotExist:
        self.log("rootd enabled but not yet configured, skipping rootd setup")


  @django.db.transaction.commit_on_success
  def update_bpki(self):
    """
    Update BPKI certificates.  Assumes an existing RPKI installation.

    Basic plan here is to reissue all BPKI certificates we can, right
    now.  In the long run we might want to be more clever about only
    touching ones that need maintenance, but this will do for a start.

    We also reissue CRLs for all CAs.

    Most likely this should be run under cron.
    """

    for model in (rpki.irdb.ServerCA,
                  rpki.irdb.ResourceHolderCA,
                  rpki.irdb.ServerEE,
                  rpki.irdb.Referral,
                  rpki.irdb.Rootd,
                  rpki.irdb.HostedCA,
                  rpki.irdb.BSC,
                  rpki.irdb.Child,
                  rpki.irdb.Parent,
                  rpki.irdb.Client,
                  rpki.irdb.Repository):
      for obj in model.objects.all():
        self.log("Regenerating BPKI certificate %s" % obj.certificate.getSubject())
        obj.avow()
        obj.save()

    self.log("Regenerating Server BPKI CRL")
    self.server_ca.generate_crl()
    self.server_ca.save()

    for ca in rpki.irdb.ResourceHolderCA.objects.all():
      self.log("Regenerating BPKI CRL for Resource Holder %s" % ca.handle)
      ca.generate_crl()
      ca.save()


  @django.db.transaction.commit_on_success
  def synchronize_bpki(self):
    """
    Synchronize BPKI updates.  This is separate from .update_bpki()
    because this requires rpkid to be running and none of the other
    BPKI update stuff does; there may be circumstances under which it
    makes sense to do the rest of the BPKI update and allow this to
    fail with a warning.
    """

    if self.run_rpkid:
      updates = []

      updates.extend(
        rpki.left_right.self_elt.make_pdu(
          action = "set",
          tag = "%s__self" % ca.handle,
          self_handle = ca.handle,
          bpki_cert = ca.certificate)
        for ca in rpki.irdb.ResourceHolderCA.objects.all())

      updates.extend(
        rpki.left_right.bsc_elt.make_pdu(
          action = "set",
          tag = "%s__bsc__%s" % (bsc.issuer.handle, bsc.handle),
          self_handle = bsc.issuer.handle,
          bsc_handle = bsc.handle,
          signing_cert = bsc.certificate,
          signing_cert_crl = bsc.issuer.latest_crl)
        for bsc in rpki.irdb.BSC.objects.all())

      updates.extend(
        rpki.left_right.repository_elt.make_pdu(
          action = "set",
          tag = "%s__repository__%s" % (repository.issuer.handle, repository.handle),
          self_handle = repository.issuer.handle,
          repository_handle = repository.handle,
          bpki_cert = repository.certificate)
        for repository in rpki.irdb.Repository.objects.all())

      updates.extend(
        rpki.left_right.parent_elt.make_pdu(
          action = "set",
          tag = "%s__parent__%s" % (parent.issuer.handle, parent.handle),
          self_handle = parent.issuer.handle,
          parent_handle = parent.handle,
          bpki_cms_cert = parent.certificate)
        for parent in rpki.irdb.Parent.objects.all())

      updates.extend(
        rpki.left_right.parent_elt.make_pdu(
          action = "set",
          tag = "%s__rootd" % rootd.issuer.handle,
          self_handle = rootd.issuer.handle,
          parent_handle = rootd.issuer.handle,
          bpki_cms_cert = rootd.certificate)
        for rootd in rpki.irdb.Rootd.objects.all())

      updates.extend(
        rpki.left_right.child_elt.make_pdu(
          action = "set",
          tag = "%s__child__%s" % (child.issuer.handle, child.handle),
          self_handle = child.issuer.handle,
          child_handle = child.handle,
          bpki_cert = child.certificate)
        for child in rpki.irdb.Child.objects.all())

      if updates:
        self.check_error_report(self.call_rpkid(updates))

    if self.run_pubd:
      updates = []

      updates.append(
        rpki.publication.config_elt.make_pdu(
          action = "set",
          bpki_crl = self.server_ca.latest_crl))

      updates.extend(
        rpki.publication.client_elt.make_pdu(
          action = "set",
          client_handle = client.handle,
          bpki_cert = client.certificate)
        for client in self.server_ca.clients.all())

      if updates:
        self.check_error_report(self.call_pubd(updates))


  @django.db.transaction.commit_on_success
  def configure_child(self, filename, child_handle = None, valid_until = None):
    """
    Configure a new child of this RPKI entity, given the child's XML
    identity file as an input.  Extracts the child's data from the
    XML, cross-certifies the child's resource-holding BPKI
    certificate, and generates an XML file describing the relationship
    between the child and this parent, including this parent's BPKI
    data and up-down protocol service URI.
    """

    c = etree_read(filename)

    if child_handle is None:
      child_handle = c.get("handle")

    if valid_until is None:
      valid_until = rpki.sundial.now() + rpki.sundial.timedelta(days = 365)
    else:
      valid_until = rpki.sundial.datetime.fromXMLtime(valid_until)
      if valid_until < rpki.sundial.now():
        raise PastExpiration("Specified new expiration time %s has passed" % valid_until)

    self.log("Child calls itself %r, we call it %r" % (c.get("handle"), child_handle))

    child, created = rpki.irdb.Child.objects.get_or_certify(
      issuer = self.resource_ca,
      handle = child_handle,
      ta = rpki.x509.X509(Base64 = c.findtext("bpki_ta")),
      valid_until = valid_until)

    return self.generate_parental_response(child), child_handle


  @django.db.transaction.commit_on_success
  def generate_parental_response(self, child):
    """
    Generate parental response XML.  Broken out of .configure_child()
    for GUI.
    """

    service_uri = "http://%s:%s/up-down/%s/%s" % (
      self.cfg.get("rpkid_server_host", section = myrpki_section),
      self.cfg.get("rpkid_server_port", section = myrpki_section),
      self.handle, child.handle)

    e = Element("parent", parent_handle = self.handle, child_handle = child.handle,
                service_uri = service_uri, valid_until = str(child.valid_until))
    B64Element(e, "bpki_resource_ta", self.resource_ca.certificate)
    B64Element(e, "bpki_child_ta", child.ta)

    try:
      if self.default_repository:
        repo = self.resource_ca.repositories.get(handle = self.default_repository)
      else:
        repo = self.resource_ca.repositories.get()
    except rpki.irdb.Repository.DoesNotExist:
      repo = None

    if repo is None:
      self.log("Couldn't find any usable repositories, not giving referral")

    elif repo.handle == self.handle:
      SubElement(e, "repository", type = "offer")

    else:
      proposed_sia_base = repo.sia_base + child.handle + "/"
      referral_cert, created = rpki.irdb.Referral.objects.get_or_certify(issuer = self.resource_ca)
      auth = rpki.x509.SignedReferral()
      auth.set_content(B64Element(None, myrpki_xmlns + "referral", child.ta,
                                  version = myrpki_version,
                                  authorized_sia_base = proposed_sia_base))
      auth.schema_check()
      auth.sign(referral_cert.private_key, referral_cert.certificate, self.resource_ca.latest_crl)

      r = SubElement(e, "repository", type = "referral")
      B64Element(r, "authorization", auth, referrer = repo.client_handle)
      SubElement(r, "contact_info")

    return etree_wrapper(e, msg = "Send this file back to the child you just configured")


  @django.db.transaction.commit_on_success
  def delete_child(self, child_handle):
    """
    Delete a child of this RPKI entity.
    """

    self.resource_ca.children.get(handle = child_handle).delete()


  @django.db.transaction.commit_on_success
  def configure_parent(self, filename, parent_handle = None):
    """
    Configure a new parent of this RPKI entity, given the output of
    the parent's configure_child command as input.  Reads the parent's
    response XML, extracts the parent's BPKI and service URI
    information, cross-certifies the parent's BPKI data into this
    entity's BPKI, and checks for offers or referrals of publication
    service.  If a publication offer or referral is present, we
    generate a request-for-service message to that repository, in case
    the user wants to avail herself of the referral or offer.
    """

    p = etree_read(filename)

    if parent_handle is None:
      parent_handle = p.get("parent_handle")

    r = p.find("repository")

    repository_type = "none"
    referrer = None
    referral_authorization = None

    if r is not None:
      repository_type = r.get("type")

    if repository_type == "referral":
      a = r.find("authorization")
      referrer = a.get("referrer")
      referral_authorization = rpki.x509.SignedReferral(Base64 = a.text)

    self.log("Parent calls itself %r, we call it %r" % (p.get("parent_handle"), parent_handle))
    self.log("Parent calls us %r" % p.get("child_handle"))

    parent, created = rpki.irdb.Parent.objects.get_or_certify(
      issuer = self.resource_ca,
      handle = parent_handle,
      child_handle = p.get("child_handle"),
      parent_handle = p.get("parent_handle"),
      service_uri = p.get("service_uri"),
      ta = rpki.x509.X509(Base64 = p.findtext("bpki_resource_ta")),
      repository_type = repository_type,
      referrer = referrer,
      referral_authorization = referral_authorization)

    return self.generate_repository_request(parent), parent_handle


  def generate_repository_request(self, parent):
    """
    Generate repository request for a given parent.
    """

    e = Element("repository", handle = self.handle,
                parent_handle = parent.handle, type = parent.repository_type)
    if parent.repository_type == "referral":
      B64Element(e, "authorization", parent.referral_authorization, referrer = parent.referrer)
      SubElement(e, "contact_info")
    B64Element(e, "bpki_client_ta", self.resource_ca.certificate)
    return etree_wrapper(e, msg = "This is the file to send to the repository operator")


  @django.db.transaction.commit_on_success
  def delete_parent(self, parent_handle):
    """
    Delete a parent of this RPKI entity.
    """

    self.resource_ca.parents.get(handle = parent_handle).delete()


  @django.db.transaction.commit_on_success
  def delete_rootd(self):
    """
    Delete rootd associated with this RPKI entity.
    """

    self.resource_ca.rootd.delete()


  @django.db.transaction.commit_on_success
  def configure_publication_client(self, filename, sia_base = None, flat = False):
    """
    Configure publication server to know about a new client, given the
    client's request-for-service message as input.  Reads the client's
    request for service, cross-certifies the client's BPKI data, and
    generates a response message containing the repository's BPKI data
    and service URI.
    """

    client = etree_read(filename)

    client_ta = rpki.x509.X509(Base64 = client.findtext("bpki_client_ta"))

    if sia_base is None and flat:
      self.log("Flat publication structure forced, homing client at top-level")
      sia_base = "rsync://%s/%s/%s/" % (self.rsync_server, self.rsync_module, client.get("handle"))

    if sia_base is None and client.get("type") == "referral":
      self.log("This looks like a referral, checking")
      try:
        auth = client.find("authorization")
        referrer = self.server_ca.clients.get(handle = auth.get("referrer"))
        referral_cms = rpki.x509.SignedReferral(Base64 = auth.text)
        referral_xml = referral_cms.unwrap(ta = (referrer.certificate, self.server_ca.certificate))
        if rpki.x509.X509(Base64 = referral_xml.text) != client_ta:
          raise BadXMLMessage("Referral trust anchor does not match")
        sia_base = referral_xml.get("authorized_sia_base")
      except rpki.irdb.Client.DoesNotExist:
        self.log("We have no record of the client (%s) alleged to have made this referral" % auth.get("referrer"))

    if sia_base is None and client.get("type") == "offer":
      self.log("This looks like an offer, checking")
      try:
        parent = rpki.irdb.ResourceHolderCA.objects.get(children__ta__exact = client_ta)
        if "/" in parent.repositories.get(ta = self.server_ca.certificate).client_handle:
          self.log("Client's parent is not top-level, this is not a valid offer")
        else:
          self.log("Found client and its parent, nesting")
          sia_base = "rsync://%s/%s/%s/%s/" % (self.rsync_server, self.rsync_module,
                                                 parent.handle, client.get("handle"))
      except rpki.irdb.Repository.DoesNotExist:
        self.log("Found client's parent, but repository isn't set, this shouldn't happen!")
      except rpki.irdb.ResourceHolderCA.DoesNotExist:
        try:
          rpki.irdb.Rootd.objects.get(issuer__certificate__exact = client_ta)
        except rpki.irdb.Rootd.DoesNotExist:
          self.log("We don't host this client's parent, so we didn't make this offer")
        else:
          self.log("This client's parent is rootd")

    if sia_base is None:
      self.log("Don't know where to nest this client, defaulting to top-level")
      sia_base = "rsync://%s/%s/%s/" % (self.rsync_server, self.rsync_module, client.get("handle"))

    if not sia_base.startswith("rsync://"):
      raise BadXMLMessage("Malformed sia_base parameter %r, should start with 'rsync://'" % sia_base)

    client_handle = "/".join(sia_base.rstrip("/").split("/")[4:])

    parent_handle = client.get("parent_handle")

    self.log("Client calls itself %r, we call it %r" % (client.get("handle"), client_handle))
    self.log("Client says its parent handle is %r" % parent_handle)

    client, created = rpki.irdb.Client.objects.get_or_certify(
      issuer = self.server_ca,
      handle = client_handle,
      parent_handle = parent_handle,
      ta = client_ta,
      sia_base = sia_base)

    return self.generate_repository_response(client), client_handle


  def generate_repository_response(self, client):
    """
    Generate repository response XML to a given client.
    """

    service_uri = "http://%s:%s/client/%s" % (
      self.cfg.get("pubd_server_host", section = myrpki_section),
      self.cfg.get("pubd_server_port", section = myrpki_section),
      client.handle)

    e = Element("repository", type = "confirmed",
                client_handle = client.handle,
                parent_handle = client.parent_handle,
                sia_base = client.sia_base,
                service_uri = service_uri)

    B64Element(e, "bpki_server_ta", self.server_ca.certificate)
    B64Element(e, "bpki_client_ta", client.ta)
    SubElement(e, "contact_info").text = self.pubd_contact_info
    return etree_wrapper(e, msg = "Send this file back to the publication client you just configured")


  @django.db.transaction.commit_on_success
  def delete_publication_client(self, client_handle):
    """
    Delete a publication client of this RPKI entity.
    """

    self.server_ca.clients.get(handle = client_handle).delete()


  @django.db.transaction.commit_on_success
  def configure_repository(self, filename, parent_handle = None):
    """
    Configure a publication repository for this RPKI entity, given the
    repository's response to our request-for-service message as input.
    Reads the repository's response, extracts and cross-certifies the
    BPKI data and service URI, and links the repository data with the
    corresponding parent data in our local database.
    """

    r = etree_read(filename)

    if parent_handle is None:
      parent_handle = r.get("parent_handle")

    self.log("Repository calls us %r" % (r.get("client_handle")))
    self.log("Repository response associated with parent_handle %r" % parent_handle)

    try:
      if parent_handle == self.handle:
        turtle = self.resource_ca.rootd
      else:
        turtle = self.resource_ca.parents.get(handle = parent_handle)

    except (rpki.irdb.Parent.DoesNotExist, rpki.irdb.Rootd.DoesNotExist):
      self.log("Could not find parent %r in our database" % parent_handle)

    else:
      rpki.irdb.Repository.objects.get_or_certify(
        issuer = self.resource_ca,
        handle = parent_handle,
        client_handle = r.get("client_handle"),
        service_uri = r.get("service_uri"),
        sia_base = r.get("sia_base"),
        ta = rpki.x509.X509(Base64 = r.findtext("bpki_server_ta")),
        turtle = turtle)


  @django.db.transaction.commit_on_success
  def delete_repository(self, repository_handle):
    """
    Delete a repository of this RPKI entity.
    """

    self.resource_ca.repositories.get(handle = repository_handle).delete()


  @django.db.transaction.commit_on_success
  def renew_children(self, child_handle, valid_until = None):
    """
    Update validity period for one child entity or, if child_handle is
    None, for all child entities.
    """

    if child_handle is None:
      children = self.resource_ca.children.all()
    else:
      children = self.resource_ca.children.filter(handle = child_handle)

    if valid_until is None:
      valid_until = rpki.sundial.now() + rpki.sundial.timedelta(days = 365)
    else:
      valid_until = rpki.sundial.datetime.fromXMLtime(valid_until)
      if valid_until < rpki.sundial.now():
        raise PastExpiration("Specified new expiration time %s has passed" % valid_until)

    self.log("New validity date %s" % valid_until)

    for child in children:
      child.valid_until = valid_until
      child.save()


  @django.db.transaction.commit_on_success
  def load_prefixes(self, filename, ignore_missing_children = False):
    """
    Whack IRDB to match prefixes.csv.
    """

    grouped4 = {}
    grouped6 = {}

    #lxw    csv_reader pre-process the file? remove the resources do not exist?
    for handle, prefix in csv_reader(filename, columns = 2):
      grouped = grouped6 if ":" in prefix else grouped4
      if handle not in grouped:
        grouped[handle] = []
      grouped[handle].append(prefix)

    primary_keys = []

    for version, grouped, rset in ((4, grouped4, rpki.resource_set.resource_set_ipv4),
                                   (6, grouped6, rpki.resource_set.resource_set_ipv6)):
      for handle, prefixes in grouped.iteritems():
        try:
          child = self.resource_ca.children.get(handle = handle)
        except rpki.irdb.Child.DoesNotExist:
          if not ignore_missing_children:
            raise
        else:
          for prefix in rset(",".join(prefixes)):
            obj, created = rpki.irdb.ChildNet.objects.get_or_create(
              child    = child,
              start_ip = str(prefix.min),
              end_ip   = str(prefix.max),
              version  = version)
            primary_keys.append(obj.pk)

    q = rpki.irdb.ChildNet.objects
    q = q.filter(child__issuer__exact = self.resource_ca)
    q = q.exclude(pk__in = primary_keys)
    q.delete()


  @django.db.transaction.commit_on_success
  def load_asns(self, filename, ignore_missing_children = False):
    """
    Whack IRDB to match asns.csv.
    """

    grouped = {}

    for handle, asn in csv_reader(filename, columns = 2):
      if handle not in grouped:
        grouped[handle] = []
      grouped[handle].append(asn)

    primary_keys = []

    for handle, asns in grouped.iteritems():
      try:
        child = self.resource_ca.children.get(handle = handle)
      except rpki.irdb.Child.DoesNotExist:
        if not ignore_missing_children:
          raise
      else:
        for asn in rpki.resource_set.resource_set_as(",".join(asns)):
          obj, created = rpki.irdb.ChildASN.objects.get_or_create(
            child    = child,
            start_as = str(asn.min),
            end_as   = str(asn.max))
          primary_keys.append(obj.pk)

    q = rpki.irdb.ChildASN.objects
    q = q.filter(child__issuer__exact = self.resource_ca)
    q = q.exclude(pk__in = primary_keys)
    q.delete()


  @django.db.transaction.commit_on_success
  def load_roa_requests(self, filename):
    """
    Whack IRDB to match roa.csv.
    """

    grouped = {}

    # format:  p/n-m asn group
    for pnm, asn, group in csv_reader(filename, columns = 3):
      key = (asn, group)
      if key not in grouped:
        grouped[key] = []
      grouped[key].append(pnm)

    # Deleting and recreating all the ROA requests is inefficient,
    # but rpkid's current representation of ROA requests is wrong
    # (see #32), so it's not worth a lot of effort here as we're
    # just going to have to rewrite this soon anyway.

    self.resource_ca.roa_requests.all().delete()

    for key, pnms in grouped.iteritems():
      asn, group = key

      roa_request = self.resource_ca.roa_requests.create(asn = asn)

      for pnm in pnms:
        if ":" in pnm:
          p = rpki.resource_set.roa_prefix_ipv6.parse_str(pnm)
          v = 6
        else:
          p = rpki.resource_set.roa_prefix_ipv4.parse_str(pnm)
          v = 4
        roa_request.prefixes.create(
          version       = v,
          prefix        = str(p.prefix),
          prefixlen     = int(p.prefixlen),
          max_prefixlen = int(p.max_prefixlen))


  @django.db.transaction.commit_on_success
  def load_ghostbuster_requests(self, filename, parent = None):
    """
    Whack IRDB to match ghostbusters.vcard.

    This accepts one or more vCards from a file.
    """

    self.resource_ca.ghostbuster_requests.filter(parent = parent).delete()

    vcard = []

    for line in open(filename, "r"):
      if not vcard and not line.upper().startswith("BEGIN:VCARD"):
        continue
      vcard.append(line)
      if line.upper().startswith("END:VCARD"):
        self.resource_ca.ghostbuster_requests.create(vcard = "".join(vcard), parent = parent)
        vcard = []


  def call_rpkid(self, *pdus):
    """
    Issue a call to rpkid, return result.

    Implementation is a little silly, constructs a wrapper object,
    invokes it once, then throws it away.  Hard to do better without
    rewriting a bit of the HTTP code, as we want to be sure we're
    using the current BPKI certificate and key objects.
    """

    url = "http://%s:%s/left-right" % (
      self.cfg.get("rpkid_server_host", section = myrpki_section),
      self.cfg.get("rpkid_server_port", section = myrpki_section))

    rpkid = self.server_ca.ee_certificates.get(purpose = "rpkid")
    irbe  = self.server_ca.ee_certificates.get(purpose = "irbe")

    if len(pdus) == 1 and isinstance(pdus[0], types.GeneratorType):
      pdus = tuple(pdus[0])
    elif len(pdus) == 1 and isinstance(pdus[0], (tuple, list)):
      pdus = pdus[0]

    call_rpkid = rpki.async.sync_wrapper(
      disable_signal_handlers = self.disable_signal_handlers,
      func = rpki.http.caller(
        proto       = rpki.left_right,
        client_key  = irbe.private_key,
        client_cert = irbe.certificate,
        server_ta   = self.server_ca.certificate,
        server_cert = rpkid.certificate,
        url         = url,
        debug       = self.show_xml))

    return call_rpkid(*pdus)


  def run_rpkid_now(self):
    """
    Poke rpkid to immediately run the cron job for the current handle.

    This method is used by the GUI when a user has changed something in the
    IRDB (ghostbuster, roa) which does not require a full synchronize() call,
    to force the object to be immediately issued.
    """

    self.call_rpkid(rpki.left_right.self_elt.make_pdu(
      action = "set", self_handle = self.handle, run_now = "yes"))


  def publish_world_now(self):
    """
    Poke rpkid to (re)publish everything for the current handle.
    """

    self.call_rpkid(rpki.left_right.self_elt.make_pdu(
      action = "set", self_handle = self.handle, publish_world_now = "yes"))


  def reissue(self):
    """
    Poke rpkid to reissue everything for the current handle.
    """

    self.call_rpkid(rpki.left_right.self_elt.make_pdu(
      action = "set", self_handle = self.handle, reissue = "yes"))

  def rekey(self):
    """
    Poke rpkid to rekey all RPKI certificates received for the current
    handle.
    """

    self.call_rpkid(rpki.left_right.self_elt.make_pdu(
      action = "set", self_handle = self.handle, rekey = "yes"))


  def revoke(self):
    """
    Poke rpkid to revoke old RPKI keys for the current handle.
    """

    self.call_rpkid(rpki.left_right.self_elt.make_pdu(
      action = "set", self_handle = self.handle, revoke = "yes"))


  def revoke_forgotten(self):
    """
    Poke rpkid to revoke old forgotten RPKI keys for the current handle.
    """

    self.call_rpkid(rpki.left_right.self_elt.make_pdu(
      action = "set", self_handle = self.handle, revoke_forgotten = "yes"))


  def clear_all_sql_cms_replay_protection(self):
    """
    Tell rpkid and pubd to clear replay protection for all SQL-based
    entities.  This is a fairly blunt instrument, but as we don't
    expect this to be necessary except in the case of gross
    misconfiguration, it should suffice
    """

    self.call_rpkid(rpki.left_right.self_elt.make_pdu(action = "set", self_handle = ca.handle,
                                                      clear_replay_protection = "yes")
                    for ca in rpki.irdb.ResourceHolderCA.objects.all())
    if self.run_pubd:
      self.call_pubd(rpki.publication.client_elt.make_pdu(action = "set",
                                                          client_handle = client.handle,
                                                          clear_replay_protection = "yes")
                     for client in self.server_ca.clients.all())


  def call_pubd(self, *pdus):
    """
    Issue a call to pubd, return result.

    Implementation is a little silly, constructs a wrapper object,
    invokes it once, then throws it away.  Hard to do better without
    rewriting a bit of the HTTP code, as we want to be sure we're
    using the current BPKI certificate and key objects.
    """

    url = "http://%s:%s/control" % (
      self.cfg.get("pubd_server_host", section = myrpki_section),
      self.cfg.get("pubd_server_port", section = myrpki_section))

    pubd = self.server_ca.ee_certificates.get(purpose = "pubd")
    irbe = self.server_ca.ee_certificates.get(purpose = "irbe")

    if len(pdus) == 1 and isinstance(pdus[0], types.GeneratorType):
      pdus = tuple(pdus[0])
    elif len(pdus) == 1 and isinstance(pdus[0], (tuple, list)):
      pdus = pdus[0]

    call_pubd = rpki.async.sync_wrapper(
      disable_signal_handlers = self.disable_signal_handlers,
      func = rpki.http.caller(
        proto       = rpki.publication,
        client_key  = irbe.private_key,
        client_cert = irbe.certificate,
        server_ta   = self.server_ca.certificate,
        server_cert = pubd.certificate,
        url         = url,
        debug       = self.show_xml))

    return call_pubd(*pdus)


  def check_error_report(self, pdus):
    """
    Check a response from rpkid or pubd for error_report PDUs, log and
    throw exceptions as needed.
    """

    if any(isinstance(pdu, (rpki.left_right.report_error_elt, rpki.publication.report_error_elt)) for pdu in pdus):
      for pdu in pdus:
        if isinstance(pdu, rpki.left_right.report_error_elt):
          self.log("rpkid reported failure: %s" % pdu.error_code)
        elif isinstance(pdu, rpki.publication.report_error_elt):
          self.log("pubd reported failure: %s" % pdu.error_code)
        else:
          continue
        if pdu.error_text:
          self.log(pdu.error_text)
      raise CouldntTalkToDaemon


  @django.db.transaction.commit_on_success
  def synchronize(self, *handles_to_poke):
    """
    Configure RPKI daemons with the data built up by the other
    commands in this program.  Commands which modify the IRDB and want
    to whack everything into sync should call this when they're done,
    but be warned that this can be slow with a lot of CAs.

    Any arguments given are handles of CAs which should be poked with a
    <self run_now="yes"/> operation.
    """

    for ca in rpki.irdb.ResourceHolderCA.objects.all():
      self.synchronize_rpkid_one_ca_core(ca, ca.handle in handles_to_poke)
    self.synchronize_pubd_core()
    self.synchronize_rpkid_deleted_core()


  @django.db.transaction.commit_on_success
  def synchronize_ca(self, ca = None, poke = False):
    """
    Synchronize one CA.  Most commands which modify a CA should call
    this.  CA to synchronize defaults to the current resource CA.
    """

    if ca is None:
      ca = self.resource_ca
    self.synchronize_rpkid_one_ca_core(ca, poke)


  @django.db.transaction.commit_on_success
  def synchronize_deleted_ca(self):
    """
    Delete CAs which are present in rpkid's database but not in the
    IRDB.
    """

    self.synchronize_rpkid_deleted_core()


  @django.db.transaction.commit_on_success
  def synchronize_pubd(self):
    """
    Synchronize pubd.  Most commands which modify pubd should call this.
    """

    self.synchronize_pubd_core()


  def synchronize_rpkid_one_ca_core(self, ca, poke = False):
    """
    Synchronize one CA.  This is the core synchronization code.  Don't
    call this directly, instead call one of the methods that calls
    this inside a Django commit wrapper.

    This method configures rpkid with data built up by the other
    commands in this program.  Most commands which modify IRDB values
    related to rpkid should call this when they're done.

    If poke is True, we append a left-right run_now operation for this
    CA to the end of whatever other commands this method generates.
    """

    # We can use a single BSC for everything -- except BSC key
    # rollovers.  Drive off that bridge when we get to it.

    bsc_handle = "bsc"

    # A default RPKI CRL cycle time of six hours seems sane.  One
    # might make a case for a day instead, but we've been running with
    # six hours for a while now and haven't seen a lot of whining.

    self_crl_interval = self.cfg.getint("self_crl_interval", 6 * 60 * 60, section = myrpki_section)

    # regen_margin now just controls how long before RPKI certificate
    # expiration we should regenerate; it used to control the interval
    # before RPKI CRL staleness at which to regenerate the CRL, but
    # using the same timer value for both of these is hopeless.
    #
    # A default regeneration margin of two weeks gives enough time for
    # humans to react.  We add a two hour fudge factor in the hope
    # that this will regenerate certificates just *before* the
    # companion cron job warns of impending doom.

    self_regen_margin = self.cfg.getint("self_regen_margin", 14 * 24 * 60 * 60 + 2 * 60, section = myrpki_section)

    # See what rpkid already has on file for this entity.

    rpkid_reply = self.call_rpkid(
      rpki.left_right.self_elt.make_pdu(      action = "get",  tag = "self",       self_handle = ca.handle),
      rpki.left_right.bsc_elt.make_pdu(       action = "list", tag = "bsc",        self_handle = ca.handle),
      rpki.left_right.repository_elt.make_pdu(action = "list", tag = "repository", self_handle = ca.handle),
      rpki.left_right.parent_elt.make_pdu(    action = "list", tag = "parent",     self_handle = ca.handle),
      rpki.left_right.child_elt.make_pdu(     action = "list", tag = "child",      self_handle = ca.handle))

    self_pdu        = rpkid_reply[0]
    bsc_pdus        = dict((x.bsc_handle, x) for x in rpkid_reply if isinstance(x, rpki.left_right.bsc_elt))
    repository_pdus = dict((x.repository_handle, x) for x in rpkid_reply if isinstance(x, rpki.left_right.repository_elt))
    parent_pdus     = dict((x.parent_handle, x) for x in rpkid_reply if isinstance(x, rpki.left_right.parent_elt))
    child_pdus      = dict((x.child_handle, x) for x in rpkid_reply if isinstance(x, rpki.left_right.child_elt))

    rpkid_query = []

    self_cert, created = rpki.irdb.HostedCA.objects.get_or_certify(
      issuer = self.server_ca,
      hosted = ca)

    # There should be exactly one <self/> object per hosted entity, by definition

    if (isinstance(self_pdu, rpki.left_right.report_error_elt) or
        self_pdu.crl_interval != self_crl_interval or
        self_pdu.regen_margin != self_regen_margin or
        self_pdu.bpki_cert != self_cert.certificate):
      rpkid_query.append(rpki.left_right.self_elt.make_pdu(
        action = "create" if isinstance(self_pdu, rpki.left_right.report_error_elt) else "set",
        tag = "self",
        self_handle = ca.handle,
        bpki_cert = ca.certificate,
        crl_interval = self_crl_interval,
        regen_margin = self_regen_margin))

    # In general we only need one <bsc/> per <self/>.  BSC objects
    # are a little unusual in that the keypair and PKCS #10
    # subelement is generated by rpkid, so complete setup requires
    # two round trips.

    bsc_pdu = bsc_pdus.pop(bsc_handle, None)

    if bsc_pdu is None:
      rpkid_query.append(rpki.left_right.bsc_elt.make_pdu(
        action = "create",
        tag = "bsc",
        self_handle = ca.handle,
        bsc_handle = bsc_handle,
        generate_keypair = "yes"))

    elif bsc_pdu.pkcs10_request is None:
      rpkid_query.append(rpki.left_right.bsc_elt.make_pdu(
        action = "set",
        tag = "bsc",
        self_handle = ca.handle,
        bsc_handle = bsc_handle,
        generate_keypair = "yes"))

    rpkid_query.extend(rpki.left_right.bsc_elt.make_pdu(
      action = "destroy", self_handle = ca.handle, bsc_handle = b) for b in bsc_pdus)

    # If we've already got actions queued up, run them now, so we
    # can finish setting up the BSC before anything tries to use it.

    if rpkid_query:
      rpkid_query.append(rpki.left_right.bsc_elt.make_pdu(action = "list", tag = "bsc", self_handle = ca.handle))
      rpkid_reply = self.call_rpkid(rpkid_query)
      bsc_pdus = dict((x.bsc_handle, x)
                      for x in rpkid_reply
                      if isinstance(x, rpki.left_right.bsc_elt) and x.action == "list")
      bsc_pdu = bsc_pdus.pop(bsc_handle, None)
      self.check_error_report(rpkid_reply)

    rpkid_query = []

    assert bsc_pdu.pkcs10_request is not None

    bsc, created = rpki.irdb.BSC.objects.get_or_certify(
      issuer = ca,
      handle = bsc_handle,
      pkcs10 = bsc_pdu.pkcs10_request)

    if bsc_pdu.signing_cert != bsc.certificate or bsc_pdu.signing_cert_crl != ca.latest_crl:
      rpkid_query.append(rpki.left_right.bsc_elt.make_pdu(
        action = "set",
        tag = "bsc",
        self_handle = ca.handle,
        bsc_handle = bsc_handle,
        signing_cert = bsc.certificate,
        signing_cert_crl = ca.latest_crl))

    # At present we need one <repository/> per <parent/>, not because
    # rpkid requires that, but because pubd does.  pubd probably should
    # be fixed to support a single client allowed to update multiple
    # trees, but for the moment the easiest way forward is just to
    # enforce a 1:1 mapping between <parent/> and <repository/> objects

    for repository in ca.repositories.all():

      repository_pdu = repository_pdus.pop(repository.handle, None)

      if (repository_pdu is None or
          repository_pdu.bsc_handle != bsc_handle or
          repository_pdu.peer_contact_uri != repository.service_uri or
          repository_pdu.bpki_cert != repository.certificate):
        rpkid_query.append(rpki.left_right.repository_elt.make_pdu(
          action = "create" if repository_pdu is None else "set",
          tag = repository.handle,
          self_handle = ca.handle,
          repository_handle = repository.handle,
          bsc_handle = bsc_handle,
          peer_contact_uri = repository.service_uri,
          bpki_cert = repository.certificate))

    rpkid_query.extend(rpki.left_right.repository_elt.make_pdu(
      action = "destroy", self_handle = ca.handle, repository_handle = r) for r in repository_pdus)

    # <parent/> setup code currently assumes 1:1 mapping between
    # <repository/> and <parent/>, and further assumes that the handles
    # for an associated pair are the identical (that is:
    # parent.repository_handle == parent.parent_handle).
    #
    # If no such repository exists, our choices are to ignore the
    # parent entry or throw an error.  For now, we ignore the parent.

    for parent in ca.parents.all():

      try:

        parent_pdu = parent_pdus.pop(parent.handle, None)

        if (parent_pdu is None or
            parent_pdu.bsc_handle != bsc_handle or
            parent_pdu.repository_handle != parent.handle or
            parent_pdu.peer_contact_uri != parent.service_uri or
            parent_pdu.sia_base != parent.repository.sia_base or
            parent_pdu.sender_name != parent.child_handle or
            parent_pdu.recipient_name != parent.parent_handle or
            parent_pdu.bpki_cms_cert != parent.certificate):
          rpkid_query.append(rpki.left_right.parent_elt.make_pdu(
            action = "create" if parent_pdu is None else "set",
            tag = parent.handle,
            self_handle = ca.handle,
            parent_handle = parent.handle,
            bsc_handle = bsc_handle,
            repository_handle = parent.handle,
            peer_contact_uri = parent.service_uri,
            sia_base = parent.repository.sia_base,
            sender_name = parent.child_handle,
            recipient_name = parent.parent_handle,
            bpki_cms_cert = parent.certificate))

      except rpki.irdb.Repository.DoesNotExist:
        pass

    try:

      parent_pdu = parent_pdus.pop(ca.handle, None)

      if (parent_pdu is None or
          parent_pdu.bsc_handle != bsc_handle or
          parent_pdu.repository_handle != ca.handle or
          parent_pdu.peer_contact_uri != ca.rootd.service_uri or
          parent_pdu.sia_base != ca.rootd.repository.sia_base or
          parent_pdu.sender_name != ca.handle or
          parent_pdu.recipient_name != ca.handle or
          parent_pdu.bpki_cms_cert != ca.rootd.certificate):
        rpkid_query.append(rpki.left_right.parent_elt.make_pdu(
          action = "create" if parent_pdu is None else "set",
          tag = ca.handle,
          self_handle = ca.handle,
          parent_handle = ca.handle,
          bsc_handle = bsc_handle,
          repository_handle = ca.handle,
          peer_contact_uri = ca.rootd.service_uri,
          sia_base = ca.rootd.repository.sia_base,
          sender_name = ca.handle,
          recipient_name = ca.handle,
          bpki_cms_cert = ca.rootd.certificate))

    except rpki.irdb.Rootd.DoesNotExist:
      pass

    rpkid_query.extend(rpki.left_right.parent_elt.make_pdu(
      action = "destroy", self_handle = ca.handle, parent_handle = p) for p in parent_pdus)

    # Children are simpler than parents, because they call us, so no URL
    # to construct and figuring out what certificate to use is their
    # problem, not ours.

    for child in ca.children.all():

      child_pdu = child_pdus.pop(child.handle, None)

      if (child_pdu is None or
          child_pdu.bsc_handle != bsc_handle or
          child_pdu.bpki_cert != child.certificate):
        rpkid_query.append(rpki.left_right.child_elt.make_pdu(
          action = "create" if child_pdu is None else "set",
          tag = child.handle,
          self_handle = ca.handle,
          child_handle = child.handle,
          bsc_handle = bsc_handle,
          bpki_cert = child.certificate))

    rpkid_query.extend(rpki.left_right.child_elt.make_pdu(
      action = "destroy", self_handle = ca.handle, child_handle = c) for c in child_pdus)

    # If caller wants us to poke rpkid, add that to the very end of the message

    if poke:
      rpkid_query.append(rpki.left_right.self_elt.make_pdu(
        action = "set", self_handle = ca.handle, run_now = "yes"))

    # If we changed anything, ship updates off to rpkid

    if rpkid_query:
      rpkid_reply = self.call_rpkid(rpkid_query)
      bsc_pdus = dict((x.bsc_handle, x) for x in rpkid_reply if isinstance(x, rpki.left_right.bsc_elt))
      if bsc_handle in bsc_pdus and bsc_pdus[bsc_handle].pkcs10_request:
        bsc_req = bsc_pdus[bsc_handle].pkcs10_request
      self.check_error_report(rpkid_reply)


  def synchronize_pubd_core(self):
    """
    Configure pubd with data built up by the other commands in this
    program.  This is the core synchronization code.  Don't call this
    directly, instead call a methods that calls this inside a Django
    commit wrapper.

    This method configures pubd with data built up by the other
    commands in this program.  Commands which modify IRDB fields
    related to pubd should call this when they're done.
    """

    # If we're not running pubd, the rest of this is a waste of time

    if not self.run_pubd:
      return

    # Make sure that pubd's BPKI CRL is up to date.

    self.call_pubd(rpki.publication.config_elt.make_pdu(
      action = "set",
      bpki_crl = self.server_ca.latest_crl))

    # See what pubd already has on file

    pubd_reply = self.call_pubd(rpki.publication.client_elt.make_pdu(action = "list"))
    client_pdus = dict((x.client_handle, x) for x in pubd_reply if isinstance(x, rpki.publication.client_elt))
    pubd_query = []

    # Check all clients

    for client in self.server_ca.clients.all():

      client_pdu = client_pdus.pop(client.handle, None)

      if (client_pdu is None or
          client_pdu.base_uri != client.sia_base or
          client_pdu.bpki_cert != client.certificate):
        pubd_query.append(rpki.publication.client_elt.make_pdu(
          action = "create" if client_pdu is None else "set",
          client_handle = client.handle,
          bpki_cert = client.certificate,
          base_uri = client.sia_base))

    # Delete any unknown clients

    pubd_query.extend(rpki.publication.client_elt.make_pdu(
            action = "destroy", client_handle = p) for p in client_pdus)

    # If we changed anything, ship updates off to pubd

    if pubd_query:
      pubd_reply = self.call_pubd(pubd_query)
      self.check_error_report(pubd_reply)


  def synchronize_rpkid_deleted_core(self):
    """
    Remove any <self/> objects present in rpkid's database but not
    present in the IRDB.  This is the core synchronization code.
    Don't call this directly, instead call a methods that calls this
    inside a Django commit wrapper.
    """

    rpkid_reply = self.call_rpkid(rpki.left_right.self_elt.make_pdu(action = "list"))
    self.check_error_report(rpkid_reply)

    self_handles = set(s.self_handle for s in rpkid_reply)
    ca_handles   = set(ca.handle for ca in rpki.irdb.ResourceHolderCA.objects.all())
    assert ca_handles <= self_handles

    rpkid_query = [rpki.left_right.self_elt.make_pdu(action = "destroy", self_handle = handle)
                   for handle in (self_handles - ca_handles)]

    if rpkid_query:
      rpkid_reply = self.call_rpkid(rpkid_query)
      self.check_error_report(rpkid_reply)


  @django.db.transaction.commit_on_success
  def add_ee_certificate_request(self, pkcs10, resources):
    """
    Check a PKCS #10 request to see if it complies with the
    specification for a RPKI EE certificate; if it does, add an
    EECertificateRequest for it to the IRDB.

    Not yet sure what we want for update and delete semantics here, so
    for the moment this is straight addition.  See methods like
    .load_asns() and .load_prefixes() for other strategies.
    """

    pkcs10.check_valid_request_ee()
    ee_request = self.resource_ca.ee_certificate_requests.create(
      pkcs10      = pkcs10,
      gski        = pkcs10.gSKI(),
      valid_until = resources.valid_until)
    for r in resources.asn:
      ee_request.asns.create(start_as = str(r.min), end_as = str(r.max))
    for r in resources.v4:
      ee_request.address_ranges.create(start_ip = str(r.min), end_ip = str(r.max), version = 4)
    for r in resources.v6:
      ee_request.address_ranges.create(start_ip = str(r.min), end_ip = str(r.max), version = 6)


  @django.db.transaction.commit_on_success
  def add_router_certificate_request(self, router_certificate_request_xml, valid_until = None):
    """
    Read XML file containing one or more router certificate requests,
    attempt to add request(s) to IRDB.

    Check each PKCS #10 request to see if it complies with the
    specification for a router certificate; if it does, create an EE
    certificate request for it along with the ASN resources and
    router-ID supplied in the XML.
    """

    xml = ElementTree(file = router_certificate_request_xml).getroot()
    rpki.relaxng.router_certificate.assertValid(xml)

    for req in xml.getiterator(routercert_xmlns + "router_certificate_request"):

      pkcs10 = rpki.x509.PKCS10(Base64 = req.text)
      router_id = long(req.get("router_id"))
      asns = rpki.resource_set.resource_set_as(req.get("asn"))
      if not valid_until:
        valid_until = req.get("valid_until")

      if valid_until and isinstance(valid_until, (str, unicode)):
        valid_until = rpki.sundial.datetime.fromXMLtime(valid_until)

      if not valid_until:
        valid_until = rpki.sundial.now() + rpki.sundial.timedelta(days = 365)
      elif valid_until < rpki.sundial.now():
        raise PastExpiration("Specified expiration date %s has already passed" % valid_until)

      pkcs10.check_valid_request_router()

      cn = "ROUTER-%08x" % asns[0].min
      sn = "%08x" % router_id

      ee_request = self.resource_ca.ee_certificate_requests.create(
        pkcs10      = pkcs10,
        gski        = pkcs10.gSKI(),
        valid_until = valid_until,
        cn          = cn,
        sn          = sn,
        eku         = rpki.oids.id_kp_bgpsec_router)

      for r in asns:
        ee_request.asns.create(start_as = str(r.min), end_as = str(r.max))


  @django.db.transaction.commit_on_success
  def delete_router_certificate_request(self, gski):
    """
    Delete a router certificate request from this RPKI entity.
    """

    self.resource_ca.ee_certificate_requests.get(gski = gski).delete()
