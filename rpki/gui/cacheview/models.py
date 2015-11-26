# Copyright (C) 2011  SPARTA, Inc. dba Cobham Analytic Solutions
# Copyright (C) 2012  SPARTA, Inc. a Parsons Company
#
# Permission to use, copy, modify, and distribute this software for any
# purpose with or without fee is hereby granted, provided that the above
# copyright notice and this permission notice appear in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND SPARTA DISCLAIMS ALL WARRANTIES WITH
# REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF MERCHANTABILITY
# AND FITNESS.  IN NO EVENT SHALL SPARTA BE LIABLE FOR ANY SPECIAL, DIRECT,
# INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES WHATSOEVER RESULTING FROM
# LOSS OF USE, DATA OR PROFITS, WHETHER IN AN ACTION OF CONTRACT, NEGLIGENCE
# OR OTHER TORTIOUS ACTION, ARISING OUT OF OR IN CONNECTION WITH THE USE OR
# PERFORMANCE OF THIS SOFTWARE.

__version__ = '$Id: models.py 5497 2013-09-19 18:32:48Z melkins $'

from datetime import datetime
import time

from django.db import models
from django.core.urlresolvers import reverse

import rpki.resource_set
import rpki.gui.models


class TelephoneField(models.CharField):
    def __init__(self, *args, **kwargs):
        kwargs['max_length'] = 255
        models.CharField.__init__(self, *args, **kwargs)


class AddressRange(rpki.gui.models.PrefixV4):
    @models.permalink
    def get_absolute_url(self):
        return ('rpki.gui.cacheview.views.addressrange_detail', [str(self.pk)])


class AddressRangeV6(rpki.gui.models.PrefixV6):
    @models.permalink
    def get_absolute_url(self):
        return ('rpki.gui.cacheview.views.addressrange_detail_v6',
                [str(self.pk)])


class ASRange(rpki.gui.models.ASN):
    @models.permalink
    def get_absolute_url(self):
        return ('rpki.gui.cacheview.views.asrange_detail', [str(self.pk)])

kinds = list(enumerate(('good', 'warn', 'bad')))
kinds_dict = dict((v, k) for k, v in kinds)


class ValidationLabel(models.Model):
    """
    Represents a specific error condition defined in the rcynic XML
    output file.
    """
    label = models.CharField(max_length=79, db_index=True, unique=True)
    status = models.CharField(max_length=255)
    kind = models.PositiveSmallIntegerField(choices=kinds)

    def __unicode__(self):
        return self.label


class RepositoryObject(models.Model):
    """
    Represents a globally unique RPKI repository object, specified by its URI.
    """
    uri = models.URLField(unique=True, db_index=True)

generations = list(enumerate(('current', 'backup')))
generations_dict = dict((val, key) for (key, val) in generations)


class ValidationStatus(models.Model):
    timestamp = models.DateTimeField()
    generation = models.PositiveSmallIntegerField(choices=generations, null=True)
    status = models.ForeignKey(ValidationLabel)
    repo = models.ForeignKey(RepositoryObject, related_name='statuses')


class SignedObject(models.Model):
    """
    Abstract class to hold common metadata for all signed objects.
    The signing certificate is ommitted here in order to give a proper
    value for the 'related_name' attribute.
    """
    repo = models.ForeignKey(RepositoryObject, related_name='cert', unique=True)

    # on-disk file modification time
    mtime = models.PositiveIntegerField(default=0)

    # SubjectName
    name = models.CharField(max_length=255)

    # value from the SKI extension
    keyid = models.CharField(max_length=60, db_index=True)

    # validity period from EE cert which signed object
    not_before = models.DateTimeField()
    not_after = models.DateTimeField()

    def mtime_as_datetime(self):
        """
        convert the local timestamp to UTC and convert to a datetime object
        """
        return datetime.utcfromtimestamp(self.mtime + time.timezone)

    def status_id(self):
        """
        Returns a HTML class selector for the current object based on its validation status.
        The selector is chosen based on the current generation only.  If there is any bad status,
        return bad, else if there are any warn status, return warn, else return good.
        """
        for x in reversed(kinds):
            if self.repo.statuses.filter(generation=generations_dict['current'], status__kind=x[0]):
                return x[1]
        return None  # should not happen

    def __unicode__(self):
        return u'%s' % self.name


class Cert(SignedObject):
    """
    Object representing a resource certificate.
    """
    addresses = models.ManyToManyField(AddressRange, related_name='certs')
    addresses_v6 = models.ManyToManyField(AddressRangeV6, related_name='certs')
    asns = models.ManyToManyField(ASRange, related_name='certs')
    issuer = models.ForeignKey('self', related_name='children', null=True)
    sia = models.CharField(max_length=255)

    def get_absolute_url(self):
        return reverse('cert-detail', args=[str(self.pk)])

    def get_cert_chain(self):
        """Return a list containing the complete certificate chain for this
        certificate."""
        cert = self
        x = [cert]
        while cert != cert.issuer:
            cert = cert.issuer
            x.append(cert)
        x.reverse()
        return x
    cert_chain = property(get_cert_chain)


class ROAPrefix(models.Model):
    "Abstract base class for ROA mixin."

    max_length = models.PositiveSmallIntegerField()

    class Meta:
        abstract = True

    def as_roa_prefix(self):
        "Return value as a rpki.resource_set.roa_prefix_ip object."
        rng = self.as_resource_range()
        return self.roa_cls(rng.min, rng.prefixlen(), self.max_length)

    def __unicode__(self):
        p = self.as_resource_range()
        if p.prefixlen() == self.max_length:
            return str(p)
        return '%s-%s' % (str(p), self.max_length)


# ROAPrefix is declared first, so subclass picks up __unicode__ from it.
class ROAPrefixV4(ROAPrefix, rpki.gui.models.PrefixV4):
    "One v4 prefix in a ROA."

    roa_cls = rpki.resource_set.roa_prefix_ipv4

    @property
    def routes(self):
        """return all routes covered by this roa prefix"""
        return RouteOrigin.objects.filter(prefix_min__gte=self.prefix_min,
                                          prefix_max__lte=self.prefix_max)

    class Meta:
        ordering = ('prefix_min',)


# ROAPrefix is declared first, so subclass picks up __unicode__ from it.
class ROAPrefixV6(ROAPrefix, rpki.gui.models.PrefixV6):
    "One v6 prefix in a ROA."

    roa_cls = rpki.resource_set.roa_prefix_ipv6

    class Meta:
        ordering = ('prefix_min',)


class ROA(SignedObject):
    asid = models.PositiveIntegerField()
    prefixes = models.ManyToManyField(ROAPrefixV4, related_name='roas')
    prefixes_v6 = models.ManyToManyField(ROAPrefixV6, related_name='roas')
    issuer = models.ForeignKey('Cert', related_name='roas')

    def get_absolute_url(self):
        return reverse('roa-detail', args=[str(self.pk)])

    class Meta:
        ordering = ('asid',)

    def __unicode__(self):
        return u'ROA for AS%d' % self.asid


class Ghostbuster(SignedObject):
    full_name = models.CharField(max_length=40)
    email_address = models.EmailField(blank=True, null=True)
    organization = models.CharField(blank=True, null=True, max_length=255)
    telephone = TelephoneField(blank=True, null=True)
    issuer = models.ForeignKey('Cert', related_name='ghostbusters')

    def get_absolute_url(self):
        # note that ghostbuster-detail is different from gbr-detail! sigh
        return reverse('ghostbuster-detail', args=[str(self.pk)])

    def __unicode__(self):
        if self.full_name:
            return self.full_name
        if self.organization:
            return self.organization
        if self.email_address:
            return self.email_address
        return self.telephone


from rpki.gui.routeview.models import RouteOrigin
