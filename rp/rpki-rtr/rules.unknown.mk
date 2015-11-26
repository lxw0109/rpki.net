# $Id: rules.unknown.mk 5792 2014-04-14 15:40:52Z sra $

install-always:

install-postconf: install-listener

install-listener:
	@echo "Don't know how to make $@ on this platform"; exit 1
