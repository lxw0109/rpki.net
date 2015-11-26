#!/bin/sh -
# $Id: application-x-rpki-mailcap-handler.sh 2921 2010-01-01 22:25:43Z sra $
#
# Copyright (C) 2010  Internet Systems Consortium ("ISC")
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

# Given the Maildir dump format, one can use Mutt as a viewer with two
# tweaks:
# 
# 1) Add to ~/.muttrc
# 
#     auto_view application/x-rpki
# 
# 2) Add to ~/.mailcap
# 
#     application/x-rpki; /path/to/this/script.sh ; copiousoutput
# 
# "copiousoutput" is required by mutt to enable auto_view (inline
# display) behavior.
# 
# This script could do fancier things (pretty XML formatting,
# verification checks of the CMS, etcetera) if anybody cared.
# For the moment the main use for this script is debugging.

# We have to jump through some hoops to figure out where our OpenSSL
# binary is.  If you have already installed an OpenSSL binary that
# understands CMS, feel free to use that instead.

#exec 2>&1; set -x

: ${AWK=/usr/bin/awk}
: ${OPENSSL=$(/usr/bin/dirname $0)/../openssl/openssl/apps/openssl}
: ${SPLITBASE64=$(/usr/bin/dirname $0)/splitbase64.xsl}
: ${XMLINDENT=/usr/local/bin/xmlindent}
: ${XMLLINT=/usr/local/bin/xmllint}
: ${XSLTPROC=/usr/local/bin/xsltproc}

# This produces prettier output, but also hangs sometimes, apparently some xmlindent bug dealing with really long XML attributes
#OPENSSL_CONF=/dev/null $OPENSSL cms -verify -nosigs -noverify -inform DER 2>/dev/null | $XSLTPROC $SPLITBASE64 - | $XMLINDENT -i 2 | $AWK NF

# So we do this instead
OPENSSL_CONF=/dev/null $OPENSSL cms -verify -nosigs -noverify -inform DER 2>/dev/null | $XSLTPROC $SPLITBASE64 - | $XMLLINT -format -
