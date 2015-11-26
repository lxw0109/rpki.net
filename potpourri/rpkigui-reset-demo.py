# Copyright (C) 2012, 2013, 2014  SPARTA, Inc. a Parsons Company
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

"""
This script is used to reset all of the labuser* accounts on demo.rpki.net back
to a state suitable for a new workshop.  It removes all ROAs and Ghostbuster
issued by the labuser accounts.

"""

__version__ = '$Id: rpkigui-reset-demo.py 5757 2014-04-05 22:42:12Z sra $'

from rpki.gui.script_util import setup
setup()

import sys

from rpki.gui.app.models import Conf
from rpki.irdb.models import ROARequest, GhostbusterRequest
from rpki.gui.app.glue import list_received_resources

for n in xrange(1, 33):
    username = 'labuser%02d' % n
    print 'removing objects for ' + username
    for cls in (ROARequest, GhostbusterRequest):
        cls.objects.filter(issuer__handle=username).delete()
    conf = Conf.objects.get(handle=username)
    conf.clear_alerts()
    print '... updating resource certificate cache'
    list_received_resources(sys.stdout, conf)

    # Remove delegated resources (see https://trac.rpki.net/ticket/544)
    # Note that we do not remove the parent-child relationship, just the
    # resources.
    for child in conf.children():
        child.asns.delete()
        child.address_ranges.delete()
