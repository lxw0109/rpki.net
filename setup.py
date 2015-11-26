# $Id: setup.py 5826 2014-05-09 01:49:48Z sra $
# 
# Copyright (C) 2014  Dragon Research Labs ("DRL")
# Portions copyright (C) 2011--2013  Internet Systems Consortium ("ISC")
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

from distutils.core import setup, Extension
from glob import glob
import setup_extensions

try:
  import setup_autoconf as autoconf

except ImportError:
  class autoconf:
    "Fake autoconf object to let --help work without autoconf."
    sbindir = libexecdir = datarootdir = sysconfdir = ""
    CFLAGS = LDFLAGS = LIBS = CA_TARGET = RP_TARGET = ""

try:
  from rpki.version import VERSION

except ImportError:
  VERSION = "0.0"

# pylint: disable=W0622

setup_args = dict(
  name          = "rpki",
  version       = VERSION,
  description   = "RPKI Toolkit",
  license       = "BSD",
  url           = "http://rpki.net/",
  cmdclass      = {"build_scripts"   : setup_extensions.build_scripts,
                   "install_scripts" : setup_extensions.install_scripts})

scripts         = []

# I keep forgetting to update the packages list here.  Could we
# automate this by looking for __init__.py files in the rpki/ tree?
# Might have to filter out some rpki.gui.app subdirs.

if autoconf.RP_TARGET == "rp":
  setup_args.update(
    packages    = ["rpki",
                   "rpki.POW",
                   "rpki.rtr",
                   "rpki.irdb",
                   "rpki.gui",
                   "rpki.gui.app",
                   "rpki.gui.cacheview",
                   "rpki.gui.api",
                   "rpki.gui.routeview"],
    ext_modules = [Extension("rpki.POW._POW", ["ext/POW.c"], 
                             extra_compile_args =  autoconf.CFLAGS.split(),
                             extra_link_args    = (autoconf.LDFLAGS + " " +
                                                   autoconf.LIBS).split())],
    package_data = {"rpki.gui.app" :
                    ["migrations/*.py",
                     "static/*/*",
                     "templates/*.html",
                     "templates/*/*.html",
                     "templatetags/*.py"],
                    "rpki.gui.cacheview" :
                    ["templates/*/*.html"]})

  scripts      += [(autoconf.bindir,
                    ["rp/rcynic/rcynic-cron",
                     "rp/rcynic/rcynic-html",
                     "rp/rcynic/rcynic-svn",
                     "rp/rcynic/rcynic-text",
                     "rp/rcynic/validation_status",
                     "rp/rpki-rtr/rpki-rtr",
                     "rp/utils/find_roa",
                     "rp/utils/hashdir",
                     "rp/utils/print_roa",
                     "rp/utils/print_rpki_manifest",
                     "rp/utils/scan_roas",
                     "rp/utils/scan_routercerts",
                     "rp/utils/uri"])]

if autoconf.CA_TARGET == "ca":
  setup_args.update(
    data_files  = [(autoconf.sysconfdir  + "/rpki",
                    ["ca/rpki-confgen.xml"]),
                   (autoconf.datarootdir + "/rpki/wsgi",
                    ["ca/rpki.wsgi"]),
                   (autoconf.datarootdir + "/rpki/media/css",
                    glob("rpki/gui/app/static/css/*")),
                   (autoconf.datarootdir + "/rpki/media/js",
                    glob("rpki/gui/app/static/js/*")),
                   (autoconf.datarootdir + "/rpki/media/img",
                    glob("rpki/gui/app/static/img/*")),
                   (autoconf.datarootdir + "/rpki/upgrade-scripts",
                    glob("ca/upgrade-scripts/*"))])

  scripts      += [(autoconf.sbindir,
                    ["ca/rpkic",
                     "ca/rpki-confgen",
                     "ca/rpki-start-servers",
                     "ca/rpki-sql-backup",
                     "ca/rpki-sql-setup",
                     "ca/rpki-manage",
                     "ca/rpkigui-query-routes",
                     "ca/irbe_cli"]),
                   (autoconf.libexecdir,
                    ["ca/irdbd",
                     "ca/pubd",
                     "ca/rootd",
                     "ca/rpkid",
                     "ca/rpkigui-import-routes",
                     "ca/rpkigui-check-expired",
                     "ca/rpkigui-rcynic",
                     "ca/rpkigui-apache-conf-gen"])]

setup_args.update(scripts = scripts)
setup(**setup_args)
