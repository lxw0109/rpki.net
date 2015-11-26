#!/bin/sh -
# $Id: yamltest-test-all.sh 5765 2014-04-07 21:25:15Z sra $

# Copyright (C) 2009-2013  Internet Systems Consortium ("ISC")
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
 
set -x

export TZ=UTC

test -z "$STY" && exec screen -L sh $0

screen -X split
screen -X focus

: ${runtime=900}

for yaml in smoketest.*.yaml
do
  settitle "$yaml: Starting"
  rm -rf test rcynic-data
  python sql-cleaner.py 
  now=$(date +%s)
  finish=$(($now + $runtime))
  title="$yaml: will finish at $(date -r $finish)"
  settitle "$title"
  screen sh -c "settitle '$title'; exec python yamltest.py -p yamltest.pid $yaml"
  date
  sleep 180
  date
  while test $(date +%s) -lt $finish
  do
    sleep 30
    date
    ../../rp/rcynic/rcynic
    ../../rp/rcynic/rcynic-text rcynic.xml
    ../../rp/utils/scan_roas rcynic-data/authenticated
    date
    echo "$title"
  done
  if test -r yamltest.pid
  then
    kill -INT $(cat yamltest.pid)
    sleep 30
  fi
  make backup
done
