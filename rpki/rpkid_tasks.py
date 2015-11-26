# $Id: rpkid_tasks.py 5921 2014-08-18 23:02:36Z sra $
#
# Copyright (C) 2014  Dragon Research Labs ("DRL")
# Portions copyright (C) 2012--2013  Internet Systems Consortium ("ISC")
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
rpkid task objects.  Split out from rpki.left_right and rpki.rpkid
because interactions with rpkid scheduler were getting too complicated.
"""

import logging
import rpki.log
import rpki.rpkid
import rpki.async
import rpki.up_down
import rpki.sundial
import rpki.publication
import rpki.exceptions

logger = logging.getLogger(__name__)

task_classes = ()

def queue_task(cls):
  """
  Class decorator to add a new task class to task_classes.
  """

  global task_classes
  task_classes += (cls,)
  return cls


class CompletionHandler(object):
  """
  Track one or more scheduled rpkid tasks and execute a callback when
  the last of them terminates.
  """

  ## @var debug
  # Debug logging.

  debug = False

  def __init__(self, cb):
    self.cb = cb
    self.tasks = set()

  def register(self, task):
    if self.debug:
      logger.debug("Completion handler %r registering task %r", self, task)
    self.tasks.add(task)
    task.register_completion(self.done)

  def done(self, task):
    try:
      self.tasks.remove(task)
    except KeyError:
      logger.warning("Completion handler %r called with unregistered task %r, blundering onwards", self, task)
    else:
      if self.debug:
        logger.debug("Completion handler %r called with registered task %r", self, task)
    if not self.tasks:
      if self.debug:
        logger.debug("Completion handler %r finished, calling %r", self, self.cb)
      self.cb()

  @property
  def count(self):
    return len(self.tasks)


class AbstractTask(object):
  """
  Abstract base class for rpkid scheduler task objects.  This just
  handles the scheduler hooks, real work starts in self.start.

  NB: This assumes that the rpki.rpkid.rpkid.task_* methods have been
  rewritten to expect instances of subclasses of this class, rather
  than expecting thunks to be wrapped up in the older version of this
  class.  Rewrite, rewrite, remove this comment when done, OK!
  """

  ## @var timeslice
  # How long before a task really should consider yielding the CPU to
  # let something else run.

  timeslice = rpki.sundial.timedelta(seconds = 15)

  def __init__(self, s, description = None):
    self.self = s
    self.description = description
    self.completions = []
    self.continuation = None
    self.due_date = None
    self.clear()

  def __repr__(self):
    return rpki.log.log_repr(self, self.description)

  def register_completion(self, completion):
    self.completions.append(completion)

  def exit(self):
    self.self.gctx.sql.sweep()
    while self.completions:
      self.completions.pop(0)(self)
    self.clear()
    self.due_date = None
    self.self.gctx.task_next()

  def postpone(self, continuation):
    self.self.gctx.sql.sweep()
    self.continuation = continuation
    self.due_date = None
    self.self.gctx.task_add(self)
    self.self.gctx.task_next()

  def __call__(self):
    self.due_date = rpki.sundial.now() + self.timeslice
    if self.continuation is None:
      logger.debug("Running task %r", self)
      self.clear()
      self.start()
    else:
      logger.debug("Restarting task %r at %r", self, self.continuation)
      continuation = self.continuation
      self.continuation = None
      continuation()

  @property
  def overdue(self):
    return rpki.sundial.now() > self.due_date

  def __getattr__(self, name):
    return getattr(self.self, name)

  def start(self):
    raise NotImplementedError

  def clear(self):
    pass


@queue_task
class PollParentTask(AbstractTask):
  """
  Run the regular client poll cycle with each of this self's
  parents, in turn.
  """

  def clear(self):
    self.parent_iterator = None
    self.parent = None
    self.ca_map = None
    self.class_iterator = None

  def start(self):
    self.gctx.checkpoint()
    logger.debug("Self %s[%d] polling parents", self.self_handle, self.self_id)
    rpki.async.iterator(self.parents, self.parent_loop, self.exit)

  def parent_loop(self, parent_iterator, parent):
    self.parent_iterator = parent_iterator
    self.parent = parent
    rpki.up_down.list_pdu.query(parent, self.got_list, self.list_failed)

  def got_list(self, r_msg):
    self.ca_map = dict((ca.parent_resource_class, ca) for ca in self.parent.cas)
    self.gctx.checkpoint()
    rpki.async.iterator(r_msg.payload.classes, self.class_loop, self.class_done)

  def list_failed(self, e):
    logger.exception("Couldn't get resource class list from parent %r, skipping", self.parent)
    self.parent_iterator()

  def class_loop(self, class_iterator, rc):
    self.gctx.checkpoint()
    self.class_iterator = class_iterator
    try:
      ca = self.ca_map.pop(rc.class_name)
    except KeyError:
      rpki.rpkid.ca_obj.create(self.parent, rc, class_iterator, self.class_create_failed)
    else:
      ca.check_for_updates(self.parent, rc, class_iterator, self.class_update_failed)

  def class_update_failed(self, e):
    logger.exception("Couldn't update class, skipping")
    self.class_iterator()

  def class_create_failed(self, e):
    logger.exception("Couldn't create class, skipping")
    self.class_iterator()

  def class_done(self):
    rpki.async.iterator(self.ca_map.values(), self.ca_loop, self.ca_done)

  def ca_loop(self, iterator, ca):
    self.gctx.checkpoint()
    ca.delete(self.parent, iterator)

  def ca_done(self):
    self.gctx.checkpoint()
    self.gctx.sql.sweep()
    self.parent_iterator()


@queue_task
class UpdateChildrenTask(AbstractTask):
  """
  Check for updated IRDB data for all of this self's children and
  issue new certs as necessary.  Must handle changes both in
  resources and in expiration date.
  """

  def clear(self):
    self.now = None
    self.rsn = None
    self.publisher = None
    self.iterator = None
    self.child = None
    self.child_certs = None

  def start(self):
    self.gctx.checkpoint()
    logger.debug("Self %s[%d] updating children", self.self_handle, self.self_id)
    self.now = rpki.sundial.now()
    self.rsn = self.now + rpki.sundial.timedelta(seconds = self.regen_margin)
    self.publisher = rpki.rpkid.publication_queue()
    rpki.async.iterator(self.children, self.loop, self.done)

  def loop(self, iterator, child):
    self.gctx.checkpoint()
    self.gctx.sql.sweep()
    self.iterator = iterator
    self.child = child
    self.child_certs = child.child_certs
    if self.overdue:
      self.publisher.call_pubd(lambda: self.postpone(self.do_child), self.publication_failed)
    else:
      self.do_child()

  def do_child(self):
    if self.child_certs:
      self.gctx.irdb_query_child_resources(self.child.self.self_handle, self.child.child_handle,
                                           self.got_resources, self.lose)
    else:
      self.iterator()

  def lose(self, e):
    logger.exception("Couldn't update child %r, skipping", self.child)
    self.iterator()

  def got_resources(self, irdb_resources):
    try:
      for child_cert in self.child_certs:
        ca_detail = child_cert.ca_detail
        ca = ca_detail.ca
        if ca_detail.state == "active":
          old_resources = child_cert.cert.get_3779resources()
          new_resources = old_resources & irdb_resources & ca_detail.latest_ca_cert.get_3779resources()
          old_aia = child_cert.cert.get_AIA()[0]
          new_aia = ca_detail.ca_cert_uri

          if new_resources.empty():
            logger.debug("Resources shrank to the null set, revoking and withdrawing child %s certificate SKI %s",
                         self.child.child_handle, child_cert.cert.gSKI())
            child_cert.revoke(publisher = self.publisher)
            ca_detail.generate_crl(publisher = self.publisher)
            ca_detail.generate_manifest(publisher = self.publisher)

          elif (old_resources != new_resources or
                old_aia != new_aia or
                (old_resources.valid_until < self.rsn and
                 irdb_resources.valid_until > self.now and
                 old_resources.valid_until != irdb_resources.valid_until)):

            logger.debug("Need to reissue child %s certificate SKI %s",
                         self.child.child_handle, child_cert.cert.gSKI())
            if old_resources != new_resources:
              logger.debug("Child %s SKI %s resources changed: old %s new %s",
                           self.child.child_handle, child_cert.cert.gSKI(),
                           old_resources, new_resources)
            if old_resources.valid_until != irdb_resources.valid_until:
              logger.debug("Child %s SKI %s validity changed: old %s new %s",
                           self.child.child_handle, child_cert.cert.gSKI(),
                           old_resources.valid_until, irdb_resources.valid_until)

            new_resources.valid_until = irdb_resources.valid_until
            child_cert.reissue(
              ca_detail = ca_detail,
              resources = new_resources,
              publisher = self.publisher)

          elif old_resources.valid_until < self.now:
            logger.debug("Child %s certificate SKI %s has expired: cert.valid_until %s, irdb.valid_until %s",
                         self.child.child_handle, child_cert.cert.gSKI(),
                         old_resources.valid_until, irdb_resources.valid_until)
            child_cert.sql_delete()
            self.publisher.withdraw(
              cls = rpki.publication.certificate_elt,
              uri = child_cert.uri,
              obj = child_cert.cert,
              repository = ca.parent.repository)
            ca_detail.generate_manifest(publisher = self.publisher)

    except (SystemExit, rpki.async.ExitNow):
      raise
    except Exception, e:
      self.gctx.checkpoint()
      self.lose(e)
    else:
      self.gctx.checkpoint()
      self.gctx.sql.sweep()
      self.iterator()

  def done(self):
    self.gctx.checkpoint()
    self.gctx.sql.sweep()
    self.publisher.call_pubd(self.exit, self.publication_failed)

  def publication_failed(self, e):
    logger.exception("Couldn't publish for %s, skipping", self.self_handle)
    self.gctx.checkpoint()
    self.exit()


@queue_task
class UpdateROAsTask(AbstractTask):
  """
  Generate or update ROAs for this self.
  """

  def clear(self):
    self.orphans = None
    self.updates = None
    self.publisher = None
    self.ca_details = None
    self.count = None

  def start(self):
    self.gctx.checkpoint()
    self.gctx.sql.sweep()
    logger.debug("Self %s[%d] updating ROAs", self.self_handle, self.self_id)

    logger.debug("Issuing query for ROA requests")
    self.gctx.irdb_query_roa_requests(self.self_handle, self.got_roa_requests, self.roa_requests_failed)

  def got_roa_requests(self, roa_requests):
    self.gctx.checkpoint()
    logger.debug("Received response to query for ROA requests")

    if self.gctx.sql.dirty:
      logger.warning("Unexpected dirty SQL cache, flushing")
      self.gctx.sql.sweep()

    roas = {}
    seen = set()
    self.orphans = []
    self.updates = []
    self.publisher = rpki.rpkid.publication_queue()
    self.ca_details = set()

    for roa in self.roas:
      k = (roa.asn, str(roa.ipv4), str(roa.ipv6))
      if k not in roas:
        roas[k] = roa
      elif (roa.roa is not None and roa.cert is not None and roa.ca_detail is not None and roa.ca_detail.state == "active" and
            (roas[k].roa is None or roas[k].cert is None or roas[k].ca_detail is None or roas[k].ca_detail.state != "active")):
        self.orphans.append(roas[k])
        roas[k] = roa
      else:
        self.orphans.append(roa)

    for roa_request in roa_requests:
      k = (roa_request.asn, str(roa_request.ipv4), str(roa_request.ipv6))
      if k in seen:
        logger.warning("Skipping duplicate ROA request %r", roa_request)
      else:
        seen.add(k)
        roa = roas.pop(k, None)
        if roa is None:
          roa = rpki.rpkid.roa_obj(self.gctx, self.self_id, roa_request.asn, roa_request.ipv4, roa_request.ipv6)
          logger.debug("Created new %r", roa)
        else:
          logger.debug("Found existing %r", roa)
        self.updates.append(roa)

    self.orphans.extend(roas.itervalues())

    if self.overdue:
      self.postpone(self.begin_loop)
    else:
      self.begin_loop()

  def begin_loop(self):
    self.count = 0
    rpki.async.iterator(self.updates, self.loop, self.done, pop_list = True)

  def loop(self, iterator, roa):
    self.gctx.checkpoint()
    try:
      roa.update(publisher = self.publisher, fast = True)
      self.ca_details.add(roa.ca_detail)
      self.gctx.sql.sweep()
    except (SystemExit, rpki.async.ExitNow):
      raise
    except rpki.exceptions.NoCoveringCertForROA:
      logger.warning("No covering certificate for %r, skipping", roa)
    except Exception:
      logger.exception("Could not update %r, skipping", roa)
    self.count += 1
    if self.overdue:
      self.publish(lambda: self.postpone(iterator))
    else:
      iterator()

  def publish(self, done):
    if not self.publisher.empty():
      for ca_detail in self.ca_details:
        logger.debug("Generating new CRL for %r", ca_detail)
        ca_detail.generate_crl(publisher = self.publisher)
        logger.debug("Generating new manifest for %r", ca_detail)
        ca_detail.generate_manifest(publisher = self.publisher)
    self.ca_details.clear()
    self.gctx.sql.sweep()
    self.gctx.checkpoint()
    self.publisher.call_pubd(done, self.publication_failed)

  def publication_failed(self, e):
    logger.exception("Couldn't publish for %s, skipping", self.self_handle)
    self.gctx.checkpoint()
    self.exit()

  def done(self):
    for roa in self.orphans:
      try:
        self.ca_details.add(roa.ca_detail)
        roa.revoke(publisher = self.publisher, fast = True)
      except (SystemExit, rpki.async.ExitNow):
        raise
      except Exception:
        logger.exception("Could not revoke %r", roa)
    self.gctx.sql.sweep()
    self.gctx.checkpoint()
    self.publish(self.exit)

  def roa_requests_failed(self, e):
    logger.exception("Could not fetch ROA requests for %s, skipping", self.self_handle)
    self.exit()


@queue_task
class UpdateGhostbustersTask(AbstractTask):
  """
  Generate or update Ghostbuster records for this self.

  This was originally based on the ROA update code.  It's possible
  that both could benefit from refactoring, but at this point the
  potential scaling issues for ROAs completely dominate structure of
  the ROA code, and aren't relevant here unless someone is being
  exceptionally silly.
  """

  def start(self):
    self.gctx.checkpoint()
    logger.debug("Self %s[%d] updating Ghostbuster records",
                 self.self_handle, self.self_id)

    self.gctx.irdb_query_ghostbuster_requests(self.self_handle,
                                              (p.parent_handle for p in self.parents),
                                              self.got_ghostbuster_requests,
                                              self.ghostbuster_requests_failed)

  def got_ghostbuster_requests(self, ghostbuster_requests):

    try:
      self.gctx.checkpoint()
      if self.gctx.sql.dirty:
        logger.warning("Unexpected dirty SQL cache, flushing")
        self.gctx.sql.sweep()

      ghostbusters = {}
      orphans = []
      publisher = rpki.rpkid.publication_queue()
      ca_details = set()
      seen = set()

      parents = dict((p.parent_handle, p) for p in self.parents)

      for ghostbuster in self.ghostbusters:
        k = (ghostbuster.ca_detail_id, ghostbuster.vcard)
        if ghostbuster.ca_detail.state != "active" or k in ghostbusters:
          orphans.append(ghostbuster)
        else:
          ghostbusters[k] = ghostbuster

      for ghostbuster_request in ghostbuster_requests:
        if ghostbuster_request.parent_handle not in parents:
          logger.warning("Unknown parent_handle %r in Ghostbuster request, skipping", ghostbuster_request.parent_handle)
          continue
        k = (ghostbuster_request.parent_handle, ghostbuster_request.vcard)
        if k in seen:
          logger.warning("Skipping duplicate Ghostbuster request %r", ghostbuster_request)
          continue
        seen.add(k)
        for ca in parents[ghostbuster_request.parent_handle].cas:
          ca_detail = ca.active_ca_detail
          if ca_detail is not None:
            ghostbuster = ghostbusters.pop((ca_detail.ca_detail_id, ghostbuster_request.vcard), None)
            if ghostbuster is None:
              ghostbuster = rpki.rpkid.ghostbuster_obj(self.gctx, self.self_id, ca_detail.ca_detail_id, ghostbuster_request.vcard)
              logger.debug("Created new %r for %r", ghostbuster, ghostbuster_request.parent_handle)
            else:
              logger.debug("Found existing %r for %s", ghostbuster, ghostbuster_request.parent_handle)
            ghostbuster.update(publisher = publisher, fast = True)
            ca_details.add(ca_detail)

      orphans.extend(ghostbusters.itervalues())
      for ghostbuster in orphans:
        ca_details.add(ghostbuster.ca_detail)
        ghostbuster.revoke(publisher = publisher, fast = True)

      for ca_detail in ca_details:
        ca_detail.generate_crl(publisher = publisher)
        ca_detail.generate_manifest(publisher = publisher)

      self.gctx.sql.sweep()

      self.gctx.checkpoint()
      publisher.call_pubd(self.exit, self.publication_failed)

    except (SystemExit, rpki.async.ExitNow):
      raise
    except Exception:
      logger.exception("Could not update Ghostbuster records for %s, skipping", self.self_handle)
      self.exit()

  def publication_failed(self, e):
    logger.exception("Couldn't publish Ghostbuster updates for %s, skipping", self.self_handle)
    self.gctx.checkpoint()
    self.exit()

  def ghostbuster_requests_failed(self, e):
    logger.exception("Could not fetch Ghostbuster record requests for %s, skipping", self.self_handle)
    self.exit()


@queue_task
class UpdateEECertificatesTask(AbstractTask):
  """
  Generate or update EE certificates for this self.

  Not yet sure what kind of scaling constraints this task might have,
  so keeping it simple for initial version, we can optimize later.
  """

  def start(self):
    self.gctx.checkpoint()
    logger.debug("Self %s[%d] updating EE certificates", self.self_handle, self.self_id)

    self.gctx.irdb_query_ee_certificate_requests(self.self_handle,
                                                 self.got_requests,
                                                 self.get_requests_failed)

  def got_requests(self, requests):

    try:
      self.gctx.checkpoint()
      if self.gctx.sql.dirty:
        logger.warning("Unexpected dirty SQL cache, flushing")
        self.gctx.sql.sweep()

      publisher = rpki.rpkid.publication_queue()

      existing = dict()
      for ee in self.ee_certificates:
        gski = ee.gski
        if gski not in existing:
          existing[gski] = set()
        existing[gski].add(ee)

      ca_details = set()

      for req in requests:
        ees = existing.pop(req.gski, ())
        resources = rpki.resource_set.resource_bag(
          asn         = req.asn,
          v4          = req.ipv4,
          v6          = req.ipv6,
          valid_until = req.valid_until)
        covering = self.find_covering_ca_details(resources)
        ca_details.update(covering)

        for ee in ees:
          if ee.ca_detail in covering:
            logger.debug("Updating existing EE certificate for %s %s",
                         req.gski, resources)
            ee.reissue(
              resources = resources,
              publisher = publisher)
            covering.remove(ee.ca_detail)
          else:
            logger.debug("Existing EE certificate for %s %s is no longer covered",
                         req.gski, resources)
            ee.revoke(publisher = publisher)

        for ca_detail in covering:
          logger.debug("No existing EE certificate for %s %s",
                       req.gski, resources)
          rpki.rpkid.ee_cert_obj.create(
            ca_detail    = ca_detail,
            subject_name = rpki.x509.X501DN.from_cn(req.cn, req.sn),
            subject_key  = req.pkcs10.getPublicKey(),
            resources    = resources,
            publisher    = publisher,
            eku          = req.eku or None)

      # Anything left is an orphan
      for ees in existing.values():
        for ee in ees:
          ca_details.add(ee.ca_detail)
          ee.revoke(publisher = publisher)

      self.gctx.sql.sweep()

      for ca_detail in ca_details:
        ca_detail.generate_crl(publisher = publisher)
        ca_detail.generate_manifest(publisher = publisher)

      self.gctx.sql.sweep()

      self.gctx.checkpoint()
      publisher.call_pubd(self.exit, self.publication_failed)

    except (SystemExit, rpki.async.ExitNow):
      raise
    except Exception:
      logger.exception("Could not update EE certificates for %s, skipping", self.self_handle)
      self.exit()

  def publication_failed(self, e):
    logger.exception("Couldn't publish EE certificate updates for %s, skipping", self.self_handle)
    self.gctx.checkpoint()
    self.exit()

  def get_requests_failed(self, e):
    logger.exception("Could not fetch EE certificate requests for %s, skipping", self.self_handle)
    self.exit()


@queue_task
class RegenerateCRLsAndManifestsTask(AbstractTask):
  """
  Generate new CRLs and manifests as necessary for all of this self's
  CAs.  Extracting nextUpdate from a manifest is hard at the moment
  due to implementation silliness, so for now we generate a new
  manifest whenever we generate a new CRL

  This code also cleans up tombstones left behind by revoked ca_detail
  objects, since we're walking through the relevant portions of the
  database anyway.
  """

  def start(self):
    self.gctx.checkpoint()
    logger.debug("Self %s[%d] regenerating CRLs and manifests",
                 self.self_handle, self.self_id)

    now = rpki.sundial.now()
    crl_interval = rpki.sundial.timedelta(seconds = self.crl_interval)
    regen_margin = max(self.gctx.cron_period * 2, crl_interval / 4)
    publisher = rpki.rpkid.publication_queue()

    for parent in self.parents:
      for ca in parent.cas:
        try:
          for ca_detail in ca.revoked_ca_details:
            if now > ca_detail.latest_crl.getNextUpdate():
              ca_detail.delete(ca = ca, publisher = publisher)
          for ca_detail in ca.active_or_deprecated_ca_details:
            if now + regen_margin > ca_detail.latest_crl.getNextUpdate():
              ca_detail.generate_crl(publisher = publisher)
              ca_detail.generate_manifest(publisher = publisher)
        except (SystemExit, rpki.async.ExitNow):
          raise
        except Exception:
          logger.exception("Couldn't regenerate CRLs and manifests for CA %r, skipping", ca)

    self.gctx.checkpoint()
    self.gctx.sql.sweep()
    publisher.call_pubd(self.exit, self.lose)

  def lose(self, e):
    logger.exception("Couldn't publish updated CRLs and manifests for self %r, skipping", self.self_handle)
    self.gctx.checkpoint()
    self.exit()


@queue_task
class CheckFailedPublication(AbstractTask):
  """
  Periodic check for objects we tried to publish but failed (eg, due
  to pubd being down or unreachable).
  """

  def start(self):
    publisher = rpki.rpkid.publication_queue()
    for parent in self.parents:
      for ca in parent.cas:
        ca_detail = ca.active_ca_detail
        if ca_detail is not None:
          ca_detail.check_failed_publication(publisher)
        self.gctx.checkpoint()
    self.gctx.sql.sweep()
    publisher.call_pubd(self.exit, self.publication_failed)

  def publication_failed(self, e):
    logger.exception("Couldn't publish for %s, skipping", self.self_handle)
    self.gctx.checkpoint()
    self.exit()
