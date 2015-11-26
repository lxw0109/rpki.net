#!/bin/sh -
# $Id: update-snapshot.sh 6075 2015-07-10 02:15:16Z sra $
#
# Fetch today's OpenSSL tarball and do everything needed to make it
# the current code other than the svn commit.

#version="1.0.0-stable-SNAP-$(date +%Y%m%d)"

version="1.0.2d"

tarball="openssl-${version}.tar.gz"

case $version in
  *SNAP*) directory=snapshot;;
  *)      directory=source;;
esac

/bin/test -f "${tarball}" || /usr/bin/fetch -m -p "ftp://ftp.openssl.org/${directory}/${tarball}" || exit

/bin/rm -f openssl

for i in *.tar.gz
do
  if [ "$i" != "$tarball" ]
  then
    /bin/rm -rf "${i%.tar.gz}"
    /usr/local/bin/svn rm "$i"
  fi
done

/usr/bin/awk -v version="$version" '/^VERSION = / {$NF = version} {print}' Makefile.in >Makefile.in.$$ &&
/bin/mv Makefile.in.$$ Makefile.in

/usr/local/bin/svn add "$tarball"
