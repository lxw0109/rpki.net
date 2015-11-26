#!/usr/bin/awk -f
# $Id: ripe-prefixes-to-csv.awk 4473 2012-05-07 02:55:00Z sra $

# ftp -pa ftp://ftp.ripe.net/pub/stats/ripencc/membership/alloclist.txt

function done() {
    for (i = 1; i <= n_allocs; i++)
	print handle "\t" alloc[i];
    n_allocs = 0;
}

/^[a-z]/ {
    done();
    handle = $0;
    nr = NR;
}

NR == nr + 1 {
    name = $0;
}

NR > nr + 2 && NF > 1 && $2 !~ /:/ {
    split($2, a, "/");
    len = a[2];
    split(a[1], a, /[.]/);
    for (i = length(a); i < 4; i++)
	a[i+1]  = 0;
    alloc[++n_allocs] = sprintf("%d.%d.%d.%d/%d", a[1], a[2], a[3], a[4], len);
}

NR > nr + 2 && NF > 1 && $2 ~ /:/ {
    alloc[++n_allocs] = $2;
}

END {
    done();
}
