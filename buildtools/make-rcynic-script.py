# $Id: make-rcynic-script.py 5387 2013-06-10 19:16:35Z sra $
#
# Copyright (C) 2011-2013  Internet Systems Consortium ("ISC")
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

import os
import sys

sys.stdout.write('''\
#!%(AC_PYTHON_INTERPRETER)s
# Automatically constructed script header

''' % os.environ)

for k, v in os.environ.iteritems():
  if k.startswith("AC_") and k != "AC_PYTHON_INTERPRETER":
    sys.stdout.write("%s = '''%s'''\n" % (k.lower(), v))

sys.stdout.write('''\

# Original script starts here

''')

sys.stdout.write(sys.stdin.read())
