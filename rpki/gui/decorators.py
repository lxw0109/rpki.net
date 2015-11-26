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

__version__ = '$Id: decorators.py 6065 2015-03-04 23:49:44Z melkins $'

from django import http
from django.conf import settings


def tls_required(f):
    """Decorator which returns a 500 error if the connection is not secured
    with TLS (https).

    """
    def _tls_required(request, *args, **kwargs):
        if settings.DEBUG or request.is_secure():
            return f(request, *args, **kwargs)
        return http.HttpResponseServerError(
            'This resource may only be accessed securely via https',
            content_type='text/plain')
    return _tls_required
