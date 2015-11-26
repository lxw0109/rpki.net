# $Id: rules.freebsd.mk 5426 2013-07-06 07:01:44Z sra $

install-user-and-group: .FORCE
	@if /usr/sbin/pw groupshow "${RCYNIC_GROUP}" 2>/dev/null; \
	then \
	    echo "You already have a group \"${RCYNIC_GROUP}\", so I will use it."; \
	elif /usr/sbin/pw groupadd ${RCYNIC_GROUP}; \
	then \
	    echo "Added group \"${RCYNIC_GROUP}\"."; \
	else \
	    echo "Adding group \"${RCYNIC_GROUP}\" failed..."; \
	    echo "Please create it, then try again."; \
	    exit 1; \
	fi
	@if /usr/sbin/pw groupshow "${RPKIRTR_GROUP}" 2>/dev/null; \
	then \
	    echo "You already have a group \"${RPKIRTR_GROUP}\", so I will use it."; \
	elif /usr/sbin/pw groupadd ${RPKIRTR_GROUP}; \
	then \
	    echo "Added group \"${RPKIRTR_GROUP}\"."; \
	else \
	    echo "Adding group \"${RPKIRTR_GROUP}\" failed..."; \
	    echo "Please create it, then try again."; \
	    exit 1; \
	fi
	@if /usr/sbin/pw usershow "${RCYNIC_USER}" 2>/dev/null; \
	then \
	    echo "You already have a user \"${RCYNIC_USER}\", so I will use it."; \
	elif /usr/sbin/pw useradd ${RCYNIC_USER} -g ${RCYNIC_GROUP} -h - -d /nonexistant -s /usr/sbin/nologin -c "${RCYNIC_GECOS}" -G "${RPKIRTR_GROUP}"; \
	then \
	    echo "Added user \"${RCYNIC_USER}\"."; \
	else \
	    echo "Adding user \"${RCYNIC_USER}\" failed..."; \
	    echo "Please create it, then try again."; \
	    exit 1; \
	fi
	@if /usr/sbin/pw usershow "${RPKIRTR_USER}" 2>/dev/null; \
	then \
	    echo "You already have a user \"${RPKIRTR_USER}\", so I will use it."; \
	elif /usr/sbin/pw useradd ${RPKIRTR_USER} -g ${RPKIRTR_GROUP} -h - -d /nonexistant -s /usr/sbin/nologin -c "${RPKIRTR_GECOS}"; \
	then \
	    echo "Added user \"${RPKIRTR_USER}\"."; \
	else \
	    echo "Adding user \"${RPKIRTR_USER}\" failed..."; \
	    echo "Please create it, then try again."; \
	    exit 1; \
	fi


# We use static compilation on FreeBSD, so no need for shared libraries

install-shared-libraries: 
	@true

install-rc-scripts:
	${INSTALL} -m 555 -o root -g wheel -p rc-scripts/freebsd/rc.d.rcynic ${DESTDIR}/usr/local/etc/rc.d/rcynic
