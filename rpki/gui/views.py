# Copyright (C) 2013  SPARTA, Inc. a Parsons Company
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

__version__ = '$Id: views.py 5043 2013-02-20 00:14:25Z melkins $'

import django.contrib.auth.views
from rpki.gui.decorators import tls_required


@tls_required
def login(request, *args, **kwargs):
    "Wrapper around django.contrib.auth.views.login to force use of TLS."
    return django.contrib.auth.views.login(request, *args, **kwargs)


@tls_required
def logout(request, *args, **kwargs):
    "Wrapper around django.contrib.auth.views.logout to force use of TLS."
    return django.contrib.auth.views.logout(request, *args, **kwargs)
