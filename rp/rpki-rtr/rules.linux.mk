# $Id: rules.linux.mk 5818 2014-05-01 02:49:04Z sra $

install-always: install-listener

install-postconf:
	@true

# Only need to make listener if not already present

install-listener: ${DESTDIR}/etc/xinetd.d/rpki-rtr

${DESTDIR}/etc/xinetd.d/rpki-rtr:
	@${AWK} 'BEGIN { \
	    print "service rpki-rtr"; \
	    print "{"; \
	    print "    type           = UNLISTED"; \
	    print "    flags          = IPv4"; \
	    print "    socket_type    = stream"; \
	    print "    protocol       = tcp"; \
	    print "    port           = ${RPKI_RTR_PORT}"; \
	    print "    wait           = no"; \
	    print "    user           = rpkirtr"; \
	    print "    server         = ${bindir}/${BIN}"; \
	    print "    server_args    = server /var/rcynic/rpki-rtr"; \
	    print "}"; \
	}' >xinetd.rpki-rtr
	${INSTALL} -d ${DESTDIR}/etc/xinetd.d
	${INSTALL} -m 644 xinetd.rpki-rtr $@
	rm  xinetd.rpki-rtr
