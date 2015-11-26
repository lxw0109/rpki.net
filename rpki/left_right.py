# $Id: left_right.py 6045 2014-12-19 17:38:55Z sra $
#
# Copyright (C) 2013--2014  Dragon Research Labs ("DRL")
# Portions copyright (C) 2009--2012  Internet Systems Consortium ("ISC")
# Portions copyright (C) 2007--2008  American Registry for Internet Numbers ("ARIN")
#
# Permission to use, copy, modify, and distribute this software for any
# purpose with or without fee is hereby granted, provided that the above
# copyright notices and this permission notice appear in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND DRL, ISC, AND ARIN DISCLAIM ALL
# WARRANTIES WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS.  IN NO EVENT SHALL DRL,
# ISC, OR ARIN BE LIABLE FOR ANY SPECIAL, DIRECT, INDIRECT, OR
# CONSEQUENTIAL DAMAGES OR ANY DAMAGES WHATSOEVER RESULTING FROM LOSS
# OF USE, DATA OR PROFITS, WHETHER IN AN ACTION OF CONTRACT,
# NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF OR IN CONNECTION
# WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.

"""
RPKI "left-right" protocol.
"""

import logging
import rpki.resource_set
import rpki.x509
import rpki.sql
import rpki.exceptions
import rpki.xml_utils
import rpki.http
import rpki.up_down
import rpki.relaxng
import rpki.sundial
import rpki.log
import rpki.publication
import rpki.async
import rpki.rpkid_tasks

logger = logging.getLogger(__name__)

## @var enforce_strict_up_down_xml_sender
# Enforce strict checking of XML "sender" field in up-down protocol

enforce_strict_up_down_xml_sender = False

class left_right_namespace(object):
  """
  XML namespace parameters for left-right protocol.
  """

  xmlns = rpki.relaxng.left_right.xmlns
  nsmap = rpki.relaxng.left_right.nsmap

class data_elt(rpki.xml_utils.data_elt, rpki.sql.sql_persistent, left_right_namespace):
  """
  Virtual class for top-level left-right protocol data elements.
  """

  handles = ()

  self_id = None
  self_handle = None

  @property
  @rpki.sql.cache_reference
  def self(self):
    """
    Fetch self object to which this object links.
    """
    return self_elt.sql_fetch(self.gctx, self.self_id)

  @property
  @rpki.sql.cache_reference
  def bsc(self):
    """
    Return BSC object to which this object links.
    """
    return bsc_elt.sql_fetch(self.gctx, self.bsc_id)

  def make_reply_clone_hook(self, r_pdu):
    """
    Set handles when cloning, including _id -> _handle translation.
    """
    if r_pdu.self_handle is None:
      r_pdu.self_handle = self.self_handle
    for tag, elt in self.handles:
      id_name = tag + "_id"
      handle_name = tag + "_handle"
      if getattr(r_pdu, handle_name, None) is None:
        try:
          setattr(r_pdu, handle_name, getattr(elt.sql_fetch(self.gctx, getattr(r_pdu, id_name)), handle_name))
        except AttributeError:
          continue

  @classmethod
  def serve_fetch_handle(cls, gctx, self_id, handle):
    """
    Find an object based on its handle.
    """
    return cls.sql_fetch_where1(gctx, cls.element_name + "_handle = %s AND self_id = %s", (handle, self_id))

  def serve_fetch_one_maybe(self):
    """
    Find the object on which a get, set, or destroy method should
    operate, or which would conflict with a create method.
    """
    where = "%s.%s_handle = %%s AND %s.self_id = self.self_id AND self.self_handle = %%s" % ((self.element_name,) * 3)
    args = (getattr(self, self.element_name + "_handle"), self.self_handle)
    return self.sql_fetch_where1(self.gctx, where, args, "self")

  def serve_fetch_all(self):
    """
    Find the objects on which a list method should operate.
    """
    where = "%s.self_id = self.self_id and self.self_handle = %%s" % self.element_name
    return self.sql_fetch_where(self.gctx, where, (self.self_handle,), "self")

  def serve_pre_save_hook(self, q_pdu, r_pdu, cb, eb):
    """
    Hook to do _handle => _id translation before saving.

    self is always the object to be saved to SQL.  For create
    operations, self and q_pdu are be the same object; for set
    operations, self is the pre-existing object from SQL and q_pdu is
    the set request received from the the IRBE.
    """
    for tag, elt in self.handles:
      id_name = tag + "_id"
      if getattr(self, id_name, None) is None:
        x = elt.serve_fetch_handle(self.gctx, self.self_id, getattr(q_pdu, tag + "_handle"))
        if x is None:
          raise rpki.exceptions.HandleTranslationError("Could not translate %r %s_handle" % (self, tag))
        setattr(self, id_name, getattr(x, id_name))
    cb()

class self_elt(data_elt):
  """
  <self/> element.
  """

  element_name = "self"
  attributes = ("action", "tag", "self_handle", "crl_interval", "regen_margin")
  elements = ("bpki_cert", "bpki_glue")
  booleans = ("rekey", "reissue", "revoke", "run_now", "publish_world_now", "revoke_forgotten",
              "clear_replay_protection")

  sql_template = rpki.sql.template(
    "self",
    "self_id",
    "self_handle",
    "use_hsm",
    "crl_interval",
    "regen_margin",
    ("bpki_cert", rpki.x509.X509),
    ("bpki_glue", rpki.x509.X509))

  handles = ()

  use_hsm = False
  crl_interval = None
  regen_margin = None
  bpki_cert = None
  bpki_glue = None
  cron_tasks = None

  def __repr__(self):
    return rpki.log.log_repr(self)

  @property
  def bscs(self):
    """
    Fetch all BSC objects that link to this self object.
    """
    return bsc_elt.sql_fetch_where(self.gctx, "self_id = %s", (self.self_id,))

  @property
  def repositories(self):
    """
    Fetch all repository objects that link to this self object.
    """
    return repository_elt.sql_fetch_where(self.gctx, "self_id = %s", (self.self_id,))

  @property
  def parents(self):
    """
    Fetch all parent objects that link to this self object.
    """
    return parent_elt.sql_fetch_where(self.gctx, "self_id = %s", (self.self_id,))

  @property
  def children(self):
    """
    Fetch all child objects that link to this self object.
    """
    return child_elt.sql_fetch_where(self.gctx, "self_id = %s", (self.self_id,))

  @property
  def roas(self):
    """
    Fetch all ROA objects that link to this self object.
    """
    return rpki.rpkid.roa_obj.sql_fetch_where(self.gctx, "self_id = %s", (self.self_id,))

  @property
  def ghostbusters(self):
    """
    Fetch all Ghostbuster record objects that link to this self object.
    """
    return rpki.rpkid.ghostbuster_obj.sql_fetch_where(self.gctx, "self_id = %s", (self.self_id,))

  @property
  def ee_certificates(self):
    """
    Fetch all EE certificate objects that link to this self object.
    """
    return rpki.rpkid.ee_cert_obj.sql_fetch_where(self.gctx, "self_id = %s", (self.self_id,))


  def serve_post_save_hook(self, q_pdu, r_pdu, cb, eb):
    """
    Extra server actions for self_elt.
    """
    actions = []
    if q_pdu.rekey:
      actions.append(self.serve_rekey)
    if q_pdu.revoke:
      actions.append(self.serve_revoke)
    if q_pdu.reissue:
      actions.append(self.serve_reissue)
    if q_pdu.revoke_forgotten:
      actions.append(self.serve_revoke_forgotten)
    if q_pdu.publish_world_now:
      actions.append(self.serve_publish_world_now)
    if q_pdu.run_now:
      actions.append(self.serve_run_now)
    if q_pdu.clear_replay_protection:
      actions.append(self.serve_clear_replay_protection)
    def loop(iterator, action):
      action(iterator, eb)
    rpki.async.iterator(actions, loop, cb)

  def serve_rekey(self, cb, eb):
    """
    Handle a left-right rekey action for this self.
    """
    def loop(iterator, parent):
      parent.serve_rekey(iterator, eb)
    rpki.async.iterator(self.parents, loop, cb)

  def serve_revoke(self, cb, eb):
    """
    Handle a left-right revoke action for this self.
    """
    def loop(iterator, parent):
      parent.serve_revoke(iterator, eb)
    rpki.async.iterator(self.parents, loop, cb)

  def serve_reissue(self, cb, eb):
    """
    Handle a left-right reissue action for this self.
    """
    def loop(iterator, parent):
      parent.serve_reissue(iterator, eb)
    rpki.async.iterator(self.parents, loop, cb)

  def serve_revoke_forgotten(self, cb, eb):
    """
    Handle a left-right revoke_forgotten action for this self.
    """
    def loop(iterator, parent):
      parent.serve_revoke_forgotten(iterator, eb)
    rpki.async.iterator(self.parents, loop, cb)

  def serve_clear_replay_protection(self, cb, eb):
    """
    Handle a left-right clear_replay_protection action for this self.
    """
    def loop(iterator, obj):
      obj.serve_clear_replay_protection(iterator, eb)
    rpki.async.iterator(self.parents + self.children + self.repositories, loop, cb)

  def serve_destroy_hook(self, cb, eb):
    """
    Extra cleanup actions when destroying a self_elt.
    """
    def loop(iterator, parent):
      parent.delete(iterator)
    rpki.async.iterator(self.parents, loop, cb)


  def serve_publish_world_now(self, cb, eb):
    """
    Handle a left-right publish_world_now action for this self.

    The publication stuff needs refactoring, right now publication is
    interleaved with local operations in a way that forces far too
    many bounces through the task system for any complex update.  The
    whole thing ought to be rewritten to queue up outgoing publication
    PDUs and only send them when we're all done or when we need to
    force publication at a particular point in a multi-phase operation.

    Once that reorganization has been done, this method should be
    rewritten to reuse the low-level publish() methods that each
    object will have...but we're not there yet.  So, for now, we just
    do this via brute force.  Think of it as a trial version to see
    whether we've identified everything that needs to be republished
    for this operation.
    """

    def loop(iterator, parent):
      q_msg = rpki.publication.msg.query()
      for ca in parent.cas:
        ca_detail = ca.active_ca_detail
        if ca_detail is not None:
          q_msg.append(rpki.publication.crl_elt.make_publish(
            ca_detail.crl_uri, ca_detail.latest_crl))
          q_msg.append(rpki.publication.manifest_elt.make_publish(
            ca_detail.manifest_uri, ca_detail.latest_manifest))
          q_msg.extend(rpki.publication.certificate_elt.make_publish(
            c.uri, c.cert) for c in ca_detail.child_certs)
          q_msg.extend(rpki.publication.roa_elt.make_publish(
            r.uri, r.roa) for r in ca_detail.roas if r.roa is not None)
          q_msg.extend(rpki.publication.ghostbuster_elt.make_publish(
            g.uri, g.ghostbuster) for g in ca_detail.ghostbusters)
      parent.repository.call_pubd(iterator, eb, q_msg)

    rpki.async.iterator(self.parents, loop, cb)

  def serve_run_now(self, cb, eb):
    """
    Handle a left-right run_now action for this self.
    """
    logger.debug("Forced immediate run of periodic actions for self %s[%d]",
                 self.self_handle, self.self_id)
    completion = rpki.rpkid_tasks.CompletionHandler(cb)
    self.schedule_cron_tasks(completion)
    assert completion.count > 0
    self.gctx.task_run()

  def serve_fetch_one_maybe(self):
    """
    Find the self object upon which a get, set, or destroy action
    should operate, or which would conflict with a create method.
    """
    return self.serve_fetch_handle(self.gctx, None, self.self_handle)

  @classmethod
  def serve_fetch_handle(cls, gctx, self_id, self_handle):
    """
    Find a self object based on its self_handle.
    """
    return cls.sql_fetch_where1(gctx, "self_handle = %s", (self_handle,))

  def serve_fetch_all(self):
    """
    Find the self objects upon which a list action should operate.
    This is different from the list action for all other objects,
    where list only works within a given self_id context.
    """
    return self.sql_fetch_all(self.gctx)

  def schedule_cron_tasks(self, completion):
    """
    Schedule periodic tasks.
    """

    if self.cron_tasks is None:
      self.cron_tasks = tuple(task(self) for task in rpki.rpkid_tasks.task_classes)

    for task in self.cron_tasks:
      self.gctx.task_add(task)
      completion.register(task)

  def find_covering_ca_details(self, resources):
    """
    Return all active ca_detail_objs for this <self/> which cover a
    particular set of resources.

    If we expected there to be a large number of ca_detail_objs, we
    could add index tables and write fancy SQL query to do this, but
    for the expected common case where there are only one or two
    active ca_detail_objs per <self/>, it's probably not worth it.  In
    any case, this is an optimization we can leave for later.
    """

    results = set()
    for parent in self.parents:
      for ca in parent.cas:
        ca_detail = ca.active_ca_detail
        if ca_detail is not None and ca_detail.covers(resources):
          results.add(ca_detail)
    return results


class bsc_elt(data_elt):
  """
  <bsc/> (Business Signing Context) element.
  """

  element_name = "bsc"
  attributes = ("action", "tag", "self_handle", "bsc_handle", "key_type", "hash_alg", "key_length")
  elements = ("signing_cert", "signing_cert_crl", "pkcs10_request")
  booleans = ("generate_keypair",)

  sql_template = rpki.sql.template(
    "bsc",
    "bsc_id",
    "bsc_handle",
    "self_id",
    "hash_alg",
    ("private_key_id", rpki.x509.RSA),
    ("pkcs10_request", rpki.x509.PKCS10),
    ("signing_cert", rpki.x509.X509),
    ("signing_cert_crl", rpki.x509.CRL))

  handles = (("self", self_elt),)

  private_key_id = None
  pkcs10_request = None
  signing_cert = None
  signing_cert_crl = None

  def __repr__(self):
    return rpki.log.log_repr(self, self.bsc_handle)

  @property
  def repositories(self):
    """
    Fetch all repository objects that link to this BSC object.
    """
    return repository_elt.sql_fetch_where(self.gctx, "bsc_id = %s", (self.bsc_id,))

  @property
  def parents(self):
    """
    Fetch all parent objects that link to this BSC object.
    """
    return parent_elt.sql_fetch_where(self.gctx, "bsc_id = %s", (self.bsc_id,))

  @property
  def children(self):
    """
    Fetch all child objects that link to this BSC object.
    """
    return child_elt.sql_fetch_where(self.gctx, "bsc_id = %s", (self.bsc_id,))

  def serve_pre_save_hook(self, q_pdu, r_pdu, cb, eb):
    """
    Extra server actions for bsc_elt -- handle key generation.  For
    now this only allows RSA with SHA-256.
    """
    if q_pdu.generate_keypair:
      assert q_pdu.key_type in (None, "rsa") and q_pdu.hash_alg in (None, "sha256")
      self.private_key_id = rpki.x509.RSA.generate(keylength = q_pdu.key_length or 2048)
      self.pkcs10_request = rpki.x509.PKCS10.create(keypair = self.private_key_id)
      r_pdu.pkcs10_request = self.pkcs10_request
    data_elt.serve_pre_save_hook(self, q_pdu, r_pdu, cb, eb)

class repository_elt(data_elt):
  """
  <repository/> element.
  """

  element_name = "repository"
  attributes = ("action", "tag", "self_handle", "repository_handle", "bsc_handle", "peer_contact_uri")
  elements = ("bpki_cert", "bpki_glue")
  booleans = ("clear_replay_protection",)

  sql_template = rpki.sql.template(
    "repository",
    "repository_id",
    "repository_handle",
    "self_id",
    "bsc_id",
    "peer_contact_uri",
    ("bpki_cert", rpki.x509.X509),
    ("bpki_glue", rpki.x509.X509),
    ("last_cms_timestamp", rpki.sundial.datetime))

  handles = (("self", self_elt),
             ("bsc", bsc_elt))

  bpki_cert = None
  bpki_glue = None
  last_cms_timestamp = None

  def __repr__(self):
    return rpki.log.log_repr(self, self.repository_handle)

  @property
  def parents(self):
    """
    Fetch all parent objects that link to this repository object.
    """
    return parent_elt.sql_fetch_where(self.gctx, "repository_id = %s", (self.repository_id,))

  def serve_post_save_hook(self, q_pdu, r_pdu, cb, eb):
    """
    Extra server actions for repository_elt.
    """
    actions = []
    if q_pdu.clear_replay_protection:
      actions.append(self.serve_clear_replay_protection)
    def loop(iterator, action):
      action(iterator, eb)
    rpki.async.iterator(actions, loop, cb)

  def serve_clear_replay_protection(self, cb, eb):
    """
    Handle a left-right clear_replay_protection action for this repository.
    """
    self.last_cms_timestamp = None
    self.sql_mark_dirty()
    cb()

  @staticmethod
  def default_pubd_handler(pdu):
    """
    Default handler for publication response PDUs.
    """
    pdu.raise_if_error()

  def call_pubd(self, callback, errback, q_msg, handlers = None):
    """
    Send a message to publication daemon and return the response.

    As a convenience, attempting to send an empty message returns
    immediate success without sending anything.

    Handlers is a dict of handler functions to process the response
    PDUs.  If the tag value in the response PDU appears in the dict,
    the associated handler is called to process the PDU.  If no tag
    matches, default_pubd_handler() is called.  A handler value of
    False suppresses calling of the default handler.
    """

    try:
      self.gctx.sql.sweep()

      if not q_msg:
        return callback()

      if handlers is None:
        handlers = {}

      for q_pdu in q_msg:
        logger.info("Sending %s %s to pubd", q_pdu.action, q_pdu.uri)

      bsc = self.bsc
      q_der = rpki.publication.cms_msg().wrap(q_msg, bsc.private_key_id, bsc.signing_cert, bsc.signing_cert_crl)
      bpki_ta_path = (self.gctx.bpki_ta, self.self.bpki_cert, self.self.bpki_glue, self.bpki_cert, self.bpki_glue)

      def done(r_der):
        try:
          logger.debug("Received response from pubd")
          r_cms = rpki.publication.cms_msg(DER = r_der)
          r_msg = r_cms.unwrap(bpki_ta_path)
          r_cms.check_replay_sql(self, self.peer_contact_uri)
          for r_pdu in r_msg:
            handler = handlers.get(r_pdu.tag, self.default_pubd_handler)
            if handler:
              logger.debug("Calling pubd handler %r", handler)
              handler(r_pdu)
          if len(q_msg) != len(r_msg):
            raise rpki.exceptions.BadPublicationReply("Wrong number of response PDUs from pubd: sent %r, got %r" % (q_msg, r_msg))
          callback()
        except (rpki.async.ExitNow, SystemExit):
          raise
        except Exception, e:
          errback(e)

      logger.debug("Sending request to pubd")
      rpki.http.client(
        url          = self.peer_contact_uri,
        msg          = q_der,
        callback     = done,
        errback      = errback)

    except (rpki.async.ExitNow, SystemExit):
      raise
    except Exception, e:
      errback(e)

class parent_elt(data_elt):
  """
  <parent/> element.
  """

  element_name = "parent"
  attributes = ("action", "tag", "self_handle", "parent_handle", "bsc_handle", "repository_handle",
                "peer_contact_uri", "sia_base", "sender_name", "recipient_name")
  elements = ("bpki_cms_cert", "bpki_cms_glue")
  booleans = ("rekey", "reissue", "revoke", "revoke_forgotten", "clear_replay_protection")

  sql_template = rpki.sql.template(
    "parent",
    "parent_id",
    "parent_handle",
    "self_id",
    "bsc_id",
    "repository_id",
    "peer_contact_uri",
    "sia_base",
    "sender_name",
    "recipient_name",
    ("bpki_cms_cert", rpki.x509.X509),
    ("bpki_cms_glue", rpki.x509.X509),
    ("last_cms_timestamp", rpki.sundial.datetime))

  handles = (("self", self_elt),
             ("bsc", bsc_elt),
             ("repository", repository_elt))

  bpki_cms_cert = None
  bpki_cms_glue = None
  last_cms_timestamp = None

  def __repr__(self):
    return rpki.log.log_repr(self, self.parent_handle)

  @property
  @rpki.sql.cache_reference
  def repository(self):
    """
    Fetch repository object to which this parent object links.
    """
    return repository_elt.sql_fetch(self.gctx, self.repository_id)

  @property
  def cas(self):
    """
    Fetch all CA objects that link to this parent object.
    """
    return rpki.rpkid.ca_obj.sql_fetch_where(self.gctx, "parent_id = %s", (self.parent_id,))

  def serve_post_save_hook(self, q_pdu, r_pdu, cb, eb):
    """
    Extra server actions for parent_elt.
    """
    actions = []
    if q_pdu.rekey:
      actions.append(self.serve_rekey)
    if q_pdu.revoke:
      actions.append(self.serve_revoke)
    if q_pdu.reissue:
      actions.append(self.serve_reissue)
    if q_pdu.revoke_forgotten:
      actions.append(self.serve_revoke_forgotten)
    if q_pdu.clear_replay_protection:
      actions.append(self.serve_clear_replay_protection)
    def loop(iterator, action):
      action(iterator, eb)
    rpki.async.iterator(actions, loop, cb)

  def serve_rekey(self, cb, eb):
    """
    Handle a left-right rekey action for this parent.
    """
    def loop(iterator, ca):
      ca.rekey(iterator, eb)
    rpki.async.iterator(self.cas, loop, cb)

  def serve_revoke(self, cb, eb):
    """
    Handle a left-right revoke action for this parent.
    """
    def loop(iterator, ca):
      ca.revoke(cb = iterator, eb = eb)
    rpki.async.iterator(self.cas, loop, cb)

  def serve_reissue(self, cb, eb):
    """
    Handle a left-right reissue action for this parent.
    """
    def loop(iterator, ca):
      ca.reissue(cb = iterator, eb = eb)
    rpki.async.iterator(self.cas, loop, cb)

  def serve_clear_replay_protection(self, cb, eb):
    """
    Handle a left-right clear_replay_protection action for this parent.
    """
    self.last_cms_timestamp = None
    self.sql_mark_dirty()
    cb()


  def get_skis(self, cb, eb):
    """
    Fetch SKIs that this parent thinks we have.  In theory this should
    agree with our own database, but in practice stuff can happen, so
    sometimes we need to know what our parent thinks.

    Result is a dictionary with the resource class name as key and a
    set of SKIs as value.
    """

    def done(r_msg):
      cb(dict((rc.class_name, set(c.cert.gSKI() for c in rc.certs))
              for rc in r_msg.payload.classes))

    rpki.up_down.list_pdu.query(self, done, eb)


  def revoke_skis(self, rc_name, skis_to_revoke, cb, eb):
    """
    Revoke a set of SKIs within a particular resource class.
    """

    def loop(iterator, ski):
      logger.debug("Asking parent %r to revoke class %r, SKI %s", self, rc_name, ski)
      q_pdu = rpki.up_down.revoke_pdu()
      q_pdu.class_name = rc_name
      q_pdu.ski = ski
      self.query_up_down(q_pdu, lambda r_pdu: iterator(), eb)

    rpki.async.iterator(skis_to_revoke, loop, cb)


  def serve_revoke_forgotten(self, cb, eb):
    """
    Handle a left-right revoke_forgotten action for this parent.

    This is a bit fiddly: we have to compare the result of an up-down
    list query with what we have locally and identify the SKIs of any
    certificates that have gone missing.  This should never happen in
    ordinary operation, but can arise if we have somehow lost a
    private key, in which case there is nothing more we can do with
    the issued cert, so we have to clear it.  As this really is not
    supposed to happen, we don't clear it automatically, instead we
    require an explicit trigger.
    """

    def got_skis(skis_from_parent):

      def loop(iterator, item):
        rc_name, skis_to_revoke = item
        if rc_name in ca_map:
          for ca_detail in ca_map[rc_name].issue_response_candidate_ca_details:
            skis_to_revoke.discard(ca_detail.latest_ca_cert.gSKI())
        self.revoke_skis(rc_name, skis_to_revoke, iterator, eb)

      ca_map = dict((ca.parent_resource_class, ca) for ca in self.cas)
      rpki.async.iterator(skis_from_parent.items(), loop, cb)

    self.get_skis(got_skis, eb)


  def delete(self, cb, delete_parent = True):
    """
    Delete all the CA stuff under this parent, and perhaps the parent
    itself.
    """

    def loop(iterator, ca):
      self.gctx.checkpoint()
      ca.delete(self, iterator)

    def revoke():
      self.gctx.checkpoint()
      self.serve_revoke_forgotten(done, fail)

    def fail(e):
      logger.warning("Trouble getting parent to revoke certificates, blundering onwards: %s", e)
      done()

    def done():
      self.gctx.checkpoint()
      self.gctx.sql.sweep()
      if delete_parent:
        self.sql_delete()
      cb()

    rpki.async.iterator(self.cas, loop, revoke)


  def serve_destroy_hook(self, cb, eb):
    """
    Extra server actions when destroying a parent_elt.
    """

    self.delete(cb, delete_parent = False)


  def query_up_down(self, q_pdu, cb, eb):
    """
    Client code for sending one up-down query PDU to this parent.
    """

    bsc = self.bsc
    if bsc is None:
      raise rpki.exceptions.BSCNotFound("Could not find BSC %s" % self.bsc_id)

    if bsc.signing_cert is None:
      raise rpki.exceptions.BSCNotReady("BSC %r[%s] is not yet usable" % (bsc.bsc_handle, bsc.bsc_id))

    q_msg = rpki.up_down.message_pdu.make_query(
      payload = q_pdu,
      sender = self.sender_name,
      recipient = self.recipient_name)

    q_der = rpki.up_down.cms_msg().wrap(q_msg, bsc.private_key_id,
                                        bsc.signing_cert,
                                        bsc.signing_cert_crl)

    def unwrap(r_der):
      try:
        r_cms = rpki.up_down.cms_msg(DER = r_der)
        r_msg = r_cms.unwrap((self.gctx.bpki_ta,
                              self.self.bpki_cert,
                              self.self.bpki_glue,
                              self.bpki_cms_cert,
                              self.bpki_cms_glue))
        r_cms.check_replay_sql(self, self.peer_contact_uri)
        r_msg.payload.check_response()
      except (SystemExit, rpki.async.ExitNow):
        raise
      except Exception, e:
        eb(e)
      else:
        cb(r_msg)

    rpki.http.client(
      msg          = q_der,
      url          = self.peer_contact_uri,
      callback     = unwrap,
      errback      = eb,
      content_type = rpki.up_down.content_type)

class child_elt(data_elt):
  """
  <child/> element.
  """

  element_name = "child"
  attributes = ("action", "tag", "self_handle", "child_handle", "bsc_handle")
  elements = ("bpki_cert", "bpki_glue")
  booleans = ("reissue", "clear_replay_protection")

  sql_template = rpki.sql.template(
    "child",
    "child_id",
    "child_handle",
    "self_id",
    "bsc_id",
    ("bpki_cert", rpki.x509.X509),
    ("bpki_glue", rpki.x509.X509),
    ("last_cms_timestamp", rpki.sundial.datetime))

  handles = (("self", self_elt),
             ("bsc", bsc_elt))

  bpki_cert = None
  bpki_glue = None
  last_cms_timestamp = None

  def __repr__(self):
    return rpki.log.log_repr(self, self.child_handle)

  def fetch_child_certs(self, ca_detail = None, ski = None, unique = False):
    """
    Fetch all child_cert objects that link to this child object.
    """
    return rpki.rpkid.child_cert_obj.fetch(self.gctx, self, ca_detail, ski, unique)

  @property
  def child_certs(self):
    """
    Fetch all child_cert objects that link to this child object.
    """
    return self.fetch_child_certs()

  @property
  def parents(self):
    """
    Fetch all parent objects that link to self object to which this child object links.
    """
    return parent_elt.sql_fetch_where(self.gctx, "self_id = %s", (self.self_id,))

  def serve_post_save_hook(self, q_pdu, r_pdu, cb, eb):
    """
    Extra server actions for child_elt.
    """
    actions = []
    if q_pdu.reissue:
      actions.append(self.serve_reissue)
    if q_pdu.clear_replay_protection:
      actions.append(self.serve_clear_replay_protection)
    def loop(iterator, action):
      action(iterator, eb)
    rpki.async.iterator(actions, loop, cb)

  def serve_reissue(self, cb, eb):
    """
    Handle a left-right reissue action for this child.
    """
    publisher = rpki.rpkid.publication_queue()
    for child_cert in self.child_certs:
      child_cert.reissue(child_cert.ca_detail, publisher, force = True)
    publisher.call_pubd(cb, eb)

  def serve_clear_replay_protection(self, cb, eb):
    """
    Handle a left-right clear_replay_protection action for this child.
    """
    self.last_cms_timestamp = None
    self.sql_mark_dirty()
    cb()

  def ca_from_class_name(self, class_name):
    """
    Fetch the CA corresponding to an up-down class_name.
    """
    if not class_name.isdigit():
      raise rpki.exceptions.BadClassNameSyntax("Bad class name %s" % class_name)
    ca = rpki.rpkid.ca_obj.sql_fetch(self.gctx, long(class_name))
    if ca is None:
      raise rpki.exceptions.ClassNameUnknown("Unknown class name %s" % class_name)
    parent = ca.parent
    if self.self_id != parent.self_id:
      raise rpki.exceptions.ClassNameMismatch(
        "Class name mismatch: child.self_id = %d, parent.self_id = %d" % (
        self.self_id, parent.self_id))
    return ca

  def serve_destroy_hook(self, cb, eb):
    """
    Extra server actions when destroying a child_elt.
    """
    publisher = rpki.rpkid.publication_queue()
    for child_cert in self.child_certs:
      child_cert.revoke(publisher = publisher,
                        generate_crl_and_manifest = True)
    publisher.call_pubd(cb, eb)

  def serve_up_down(self, query, callback):
    """
    Outer layer of server handling for one up-down PDU from this child.
    """

    bsc = self.bsc
    if bsc is None:
      raise rpki.exceptions.BSCNotFound("Could not find BSC %s" % self.bsc_id)
    q_cms = rpki.up_down.cms_msg(DER = query)
    q_msg = q_cms.unwrap((self.gctx.bpki_ta,
                          self.self.bpki_cert,
                          self.self.bpki_glue,
                          self.bpki_cert,
                          self.bpki_glue))
    q_cms.check_replay_sql(self, "child", self.child_handle)
    q_msg.payload.gctx = self.gctx
    if enforce_strict_up_down_xml_sender and q_msg.sender != self.child_handle:
      raise rpki.exceptions.BadSender("Unexpected XML sender %s" % q_msg.sender)
    self.gctx.sql.sweep()

    def done(r_msg):
      #
      # Exceptions from this point on are problematic, as we have no
      # sane way of reporting errors in the error reporting mechanism.
      # May require refactoring, ignore the issue for now.
      #
      reply = rpki.up_down.cms_msg().wrap(r_msg, bsc.private_key_id,
                                          bsc.signing_cert, bsc.signing_cert_crl)
      callback(reply)

    try:
      q_msg.serve_top_level(self, done)
    except (rpki.async.ExitNow, SystemExit):
      raise
    except rpki.exceptions.NoActiveCA, data:
      done(q_msg.serve_error(data))
    except Exception, e:
      logger.exception("Unhandled exception serving up-down request from %r", self)
      done(q_msg.serve_error(e))

class list_resources_elt(rpki.xml_utils.base_elt, left_right_namespace):
  """
  <list_resources/> element.
  """

  element_name = "list_resources"
  attributes = ("self_handle", "tag", "child_handle", "valid_until", "asn", "ipv4", "ipv6")
  valid_until = None

  def __repr__(self):
    return rpki.log.log_repr(self, self.self_handle, self.child_handle, self.asn, self.ipv4, self.ipv6)

  def startElement(self, stack, name, attrs):
    """
    Handle <list_resources/> element.  This requires special handling
    due to the data types of some of the attributes.
    """
    assert name == "list_resources", "Unexpected name %s, stack %s" % (name, stack)
    self.read_attrs(attrs)
    if isinstance(self.valid_until, str):
      self.valid_until = rpki.sundial.datetime.fromXMLtime(self.valid_until)
    if self.asn is not None:
      self.asn = rpki.resource_set.resource_set_as(self.asn)
    if self.ipv4 is not None:
      self.ipv4 = rpki.resource_set.resource_set_ipv4(self.ipv4)
    if self.ipv6 is not None:
      self.ipv6 = rpki.resource_set.resource_set_ipv6(self.ipv6)

  def toXML(self):
    """
    Generate <list_resources/> element.  This requires special
    handling due to the data types of some of the attributes.
    """
    elt = self.make_elt()
    if isinstance(self.valid_until, int):
      elt.set("valid_until", self.valid_until.toXMLtime())
    return elt

class list_roa_requests_elt(rpki.xml_utils.base_elt, left_right_namespace):
  """
  <list_roa_requests/> element.
  """

  element_name = "list_roa_requests"
  attributes = ("self_handle", "tag", "asn", "ipv4", "ipv6")

  def startElement(self, stack, name, attrs):
    """
    Handle <list_roa_requests/> element.  This requires special handling
    due to the data types of some of the attributes.
    """
    assert name == "list_roa_requests", "Unexpected name %s, stack %s" % (name, stack)
    self.read_attrs(attrs)
    if self.ipv4 is not None:
      self.ipv4 = rpki.resource_set.roa_prefix_set_ipv4(self.ipv4)
    if self.ipv6 is not None:
      self.ipv6 = rpki.resource_set.roa_prefix_set_ipv6(self.ipv6)

  def __repr__(self):
    return rpki.log.log_repr(self, self.self_handle, self.asn, self.ipv4, self.ipv6)

class list_ghostbuster_requests_elt(rpki.xml_utils.text_elt, left_right_namespace):
  """
  <list_ghostbuster_requests/> element.
  """

  element_name = "list_ghostbuster_requests"
  attributes = ("self_handle", "tag", "parent_handle")
  text_attribute = "vcard"

  vcard = None

  def __repr__(self):
    return rpki.log.log_repr(self, self.self_handle, self.parent_handle)

class list_ee_certificate_requests_elt(rpki.xml_utils.base_elt, left_right_namespace):
  """
  <list_ee_certificate_requests/> element.
  """

  element_name = "list_ee_certificate_requests"
  attributes = ("self_handle", "tag", "gski", "valid_until", "asn", "ipv4", "ipv6", "cn", "sn", "eku")
  elements = ("pkcs10",)

  pkcs10 = None
  valid_until = None
  eku = None

  def __repr__(self):
    return rpki.log.log_repr(self, self.self_handle, self.gski, self.cn, self.sn, self.asn, self.ipv4, self.ipv6)

  def startElement(self, stack, name, attrs):
    """
    Handle <list_ee_certificate_requests/> element.  This requires special
    handling due to the data types of some of the attributes.
    """
    if name not in self.elements:
      assert name == self.element_name, "Unexpected name %s, stack %s" % (name, stack)
      self.read_attrs(attrs)
      if isinstance(self.valid_until, str):
        self.valid_until = rpki.sundial.datetime.fromXMLtime(self.valid_until)
      if self.asn is not None:
        self.asn = rpki.resource_set.resource_set_as(self.asn)
      if self.ipv4 is not None:
        self.ipv4 = rpki.resource_set.resource_set_ipv4(self.ipv4)
      if self.ipv6 is not None:
        self.ipv6 = rpki.resource_set.resource_set_ipv6(self.ipv6)
      if self.eku is not None:
        self.eku = self.eku.split(",")

  def endElement(self, stack, name, text):
    """
    Handle <pkcs10/> sub-element.
    """
    assert len(self.elements) == 1
    if name == self.elements[0]:
      self.pkcs10 = rpki.x509.PKCS10(Base64 = text)
    else:
      assert name == self.element_name, "Unexpected name %s, stack %s" % (name, stack)
      stack.pop()

  def toXML(self):
    """
    Generate <list_ee_certificate_requests/> element.  This requires special
    handling due to the data types of some of the attributes.
    """
    if isinstance(self.eku, (tuple, list)):
      self.eku = ",".join(self.eku)
    elt = self.make_elt()
    for i in self.elements:
      self.make_b64elt(elt, i, getattr(self, i, None))
    if isinstance(self.valid_until, int):
      elt.set("valid_until", self.valid_until.toXMLtime())
    return elt

class list_published_objects_elt(rpki.xml_utils.text_elt, left_right_namespace):
  """
  <list_published_objects/> element.
  """

  element_name = "list_published_objects"
  attributes = ("self_handle", "tag", "uri", "child_handle")
  text_attribute = "obj"

  obj = None
  child_handle = None

  def __repr__(self):
    return rpki.log.log_repr(self, self.self_handle, self.child_handle, self.uri)

  def serve_dispatch(self, r_msg, cb, eb):
    """
    Handle a <list_published_objects/> query.  The method name is a
    misnomer here, there's no action attribute and no dispatch, we
    just dump every published object for the specified <self/> and return.
    """
    for parent in self_elt.serve_fetch_handle(self.gctx, None, self.self_handle).parents:
      for ca in parent.cas:
        ca_detail = ca.active_ca_detail
        if ca_detail is not None:
          r_msg.append(self.make_reply(ca_detail.crl_uri, ca_detail.latest_crl))
          r_msg.append(self.make_reply(ca_detail.manifest_uri, ca_detail.latest_manifest))
          r_msg.extend(self.make_reply(c.uri, c.cert, c.child.child_handle)
                       for c in ca_detail.child_certs)
          r_msg.extend(self.make_reply(r.uri, r.roa)
                       for r in ca_detail.roas if r.roa is not None)
          r_msg.extend(self.make_reply(g.uri, g.ghostbuster)
                       for g in ca_detail.ghostbusters)
          r_msg.extend(self.make_reply(c.uri, c.cert)
                       for c in ca_detail.ee_certificates)
    cb()

  def make_reply(self, uri, obj, child_handle = None):
    """
    Generate one reply PDU.
    """
    r_pdu = self.make_pdu(tag = self.tag, self_handle = self.self_handle,
                          uri = uri, child_handle = child_handle)
    r_pdu.obj = obj.get_Base64()
    return r_pdu

class list_received_resources_elt(rpki.xml_utils.base_elt, left_right_namespace):
  """
  <list_received_resources/> element.
  """

  element_name = "list_received_resources"
  attributes = ("self_handle", "tag", "parent_handle",
                "notBefore", "notAfter", "uri", "sia_uri", "aia_uri", "asn", "ipv4", "ipv6")

  def __repr__(self):
    return rpki.log.log_repr(self, self.self_handle, self.parent_handle, self.uri, self.notAfter)

  def serve_dispatch(self, r_msg, cb, eb):
    """
    Handle a <list_received_resources/> query.  The method name is a
    misnomer here, there's no action attribute and no dispatch, we
    just dump a bunch of data about every certificate issued to us by
    one of our parents, then return.
    """
    for parent in self_elt.serve_fetch_handle(self.gctx, None, self.self_handle).parents:
      for ca in parent.cas:
        ca_detail = ca.active_ca_detail
        if ca_detail is not None and ca_detail.latest_ca_cert is not None:
          r_msg.append(self.make_reply(parent.parent_handle, ca_detail.ca_cert_uri, ca_detail.latest_ca_cert))
    cb()

  def make_reply(self, parent_handle, uri, cert):
    """
    Generate one reply PDU.
    """
    resources = cert.get_3779resources()
    return self.make_pdu(
      tag = self.tag,
      self_handle = self.self_handle,
      parent_handle = parent_handle,
      notBefore = str(cert.getNotBefore()),
      notAfter = str(cert.getNotAfter()),
      uri = uri,
      sia_uri = cert.get_sia_directory_uri(),
      aia_uri = cert.get_aia_uri(),
      asn = resources.asn,
      ipv4 = resources.v4,
      ipv6 = resources.v6)

class report_error_elt(rpki.xml_utils.text_elt, left_right_namespace):
  """
  <report_error/> element.
  """

  element_name = "report_error"
  attributes = ("tag", "self_handle", "error_code")
  text_attribute = "error_text"

  error_text = None

  def __repr__(self):
    return rpki.log.log_repr(self, self.self_handle, self.error_code)

  @classmethod
  def from_exception(cls, e, self_handle = None, tag = None):
    """
    Generate a <report_error/> element from an exception.
    """
    self = cls()
    self.self_handle = self_handle
    self.tag = tag
    self.error_code = e.__class__.__name__
    self.error_text = str(e)
    return self

class msg(rpki.xml_utils.msg, left_right_namespace):
  """
  Left-right PDU.
  """

  ## @var version
  # Protocol version
  version = int(rpki.relaxng.left_right.version)

  ## @var pdus
  # Dispatch table of PDUs for this protocol.
  pdus = dict((x.element_name, x)
              for x in (self_elt, child_elt, parent_elt, bsc_elt,
                        repository_elt, list_resources_elt,
                        list_roa_requests_elt, list_ghostbuster_requests_elt,
                        list_ee_certificate_requests_elt,
                        list_published_objects_elt,
                        list_received_resources_elt, report_error_elt))

  def serve_top_level(self, gctx, cb):
    """
    Serve one msg PDU.
    """

    r_msg = self.__class__.reply()

    def loop(iterator, q_pdu):

      def fail(e):
        if not isinstance(e, rpki.exceptions.NotFound):
          logger.exception("Unhandled exception serving left-right PDU %r", q_pdu)
        r_msg.append(report_error_elt.from_exception(
          e, self_handle = q_pdu.self_handle, tag = q_pdu.tag))
        cb(r_msg)

      try:
        q_pdu.gctx = gctx
        q_pdu.serve_dispatch(r_msg, iterator, fail)
      except (rpki.async.ExitNow, SystemExit):
        raise
      except Exception, e:
        fail(e)

    def done():
      cb(r_msg)

    rpki.async.iterator(self, loop, done)

class sax_handler(rpki.xml_utils.sax_handler):
  """
  SAX handler for Left-Right protocol.
  """

  pdu = msg
  name = "msg"
  version = rpki.relaxng.left_right.version

class cms_msg(rpki.x509.XML_CMS_object):
  """
  Class to hold a CMS-signed left-right PDU.
  """

  encoding = "us-ascii"
  schema = rpki.relaxng.left_right
  saxify = sax_handler.saxify
