# $Id: format-application-x-rpki.py 5630 2014-01-11 01:26:59Z sra $
# 
# Copyright (C) 2014  Dragon Research Labs ("DRL")
# Portions copyright (C) 2010--2012  Internet Systems Consortium ("ISC")
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
Take the basic application/x-rpki messages that rpkid and friends
log and translate them into a text version that's easier to search,
without losing any of the original data.  We use MH for the output
format because nmh makes a handy viewer.
"""

import email.mime
import email.mime.application
import email.mime.text
import email.mime.multipart
import email.utils
import email.encoders
import mailbox
import rpki.POW
import lxml.etree
import argparse
import sys
import base64

parser = argparse.ArgumentParser(description = __doc__)
parser.add_argument("-i", "--input", required = True,
                    help = "input Maildir")
parser.add_argument("-m", "--mark", action = "store_true",
                    help = "mark seen messages")
parser.add_argument("-k", "--kill", action = "store_true",
                    help = "kill seen messages")
parser.add_argument("-o", "--output", required = True,
                    help = "output MH folder")
parser.add_argument("-t", "--tag",
                    default = "{http://www.apnic.net/specs/rescerts/up-down/}message",
                    help = "XML namespace tag for an input message")
parser.add_argument("-u", "--unseen", action = "store_true",
                    help = "only process unseen messages")
args = parser.parse_args()

def pprint_cert(b64):
  return rpki.POW.X509.derRead(base64.b64decode(b64)).pprint()
  
def up_down():
  msg["X-RPKI-Up-Down-Type"] = xml.get("type")
  msg["X-RPKI-Up-Down-Sender"] = xml.get("sender")
  msg["X-RPKI-Up-Down-Recipient"] = xml.get("recipient")
  msg["Subject"] = "Up-down %s %s => %s" % (xml.get("type"), xml.get("sender"), xml.get("recipient"))
  for x in xml:
    if x.tag.endswith("class"):
      for y in x:
        if y.tag.endswith("certificate") or y.tag.endswith("issuer"):
          msg.attach(email.mime.text.MIMEText(pprint_cert(y.text)))

def left_right():
  msg["X-RPKI-Left-Right-Type"] = xml.get("type")
  msg["Subject"] = "Left-right %s" % xml.get("type")

def publication():
  msg["X-RPKI-Left-Right-Type"] = xml.get("type")
  msg["Subject"] = "Publication %s" % xml.get("type")

dispatch = { "{http://www.apnic.net/specs/rescerts/up-down/}message" : up_down,
             "{http://www.hactrn.net/uris/rpki/left-right-spec/}msg" : left_right,
             "{http://www.hactrn.net/uris/rpki/publication-spec/}msg" : publication }

def fix_headers():
  if "X-RPKI-PID" in srcmsg or "X-RPKI-Object" in srcmsg:
    msg["X-RPKI-PID"] = srcmsg["X-RPKI-PID"]
    msg["X-RPKI-Object"] = srcmsg["X-RPKI-Object"]
  else:
    words = srcmsg["Subject"].split()
    msg["X-RPKI-PID"] = words[1]
    msg["X-RPKI-Object"] = " ".join(words[4:])
  
destination = None
source = None
try:
  destination = mailbox.MH(args.output, factory = None, create = True)
  source = mailbox.Maildir(args.input, factory = None)

  for srckey, srcmsg in source.iteritems():
    if args.unseen and "S" in srcmsg.get_flags():
      continue
    assert not srcmsg.is_multipart() and srcmsg.get_content_type() == "application/x-rpki"
    payload = srcmsg.get_payload(decode = True)
    cms = rpki.POW.CMS.derRead(payload)
    txt = cms.verify(rpki.POW.X509Store(), None, rpki.POW.CMS_NOCRL | rpki.POW.CMS_NO_SIGNER_CERT_VERIFY | rpki.POW.CMS_NO_ATTR_VERIFY | rpki.POW.CMS_NO_CONTENT_VERIFY)
    xml = lxml.etree.fromstring(txt)
    tag = xml.tag
    if args.tag and tag != args.tag:
      continue
    msg = email.mime.multipart.MIMEMultipart("related")
    msg["X-RPKI-Tag"] = tag
    for i in ("Date", "Message-ID", "X-RPKI-Timestamp"):
      msg[i] = srcmsg[i]
    fix_headers()
    if tag in dispatch:
      dispatch[tag]()
    if "Subject" not in msg:
      msg["Subject"] = srcmsg["Subject"]
    msg.attach(email.mime.text.MIMEText(txt))
    msg.attach(email.mime.application.MIMEApplication(payload, "x-rpki"))
    msg.epilogue = "\n"                 # Force trailing newline
    key = destination.add(msg)
    print "Added", key
    if args.kill:
      del source[srckey]
    elif args.mark:
      srcmsg.set_subdir("cur")
      srcmsg.add_flag("S")
      source[srckey] = srcmsg

finally:
  if destination:
    destination.close()
  if source:
    source.close()
