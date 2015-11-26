# $Id: rules.darwin.mk 5792 2014-04-14 15:40:52Z sra $

install-always:

install-postconf: install-listener

install-listener:
	@echo "No rule for $@ on this platform (yet), you'll have to do that yourself if it matters."

