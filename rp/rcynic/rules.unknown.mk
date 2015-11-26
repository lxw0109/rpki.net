# $Id: rules.unknown.mk 5065 2013-02-25 03:58:36Z sra $

install-user-and-group install-shared-libraries install-rc-scripts: .FORCE
	@echo "Don't know how to make $@ on this platform"; exit 1
