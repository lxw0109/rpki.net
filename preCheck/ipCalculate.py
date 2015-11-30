#!/usr/bin/python2.7
# FileName: ipCalculate.py
# Author: lxw
# Date: 2015-11-30

base = 256
square = base * base
cube = square * base

def initASDict():
    #IANA
    '''
    ASN:       0-4294967295
    '''
    pass

def initIPV4Dict(ipv4Dict):
    #IANA
    '''
    IPv4:      0.0.0.0/0
    IPv6:      ::/0
    '''
    ianaMin = 0
    ianaMax = 255 * cube + 255 * square + 255 * base + 255
    ipv4Dict["iana"] = [(ianaMin, ianaMax)]

    #APNIC
    '''
    apnic   192.0.2.128/25
    apnic   198.51.100.128/25
    apnic   203.0.113.128/25
    '''
    apnic1Min = 192 * cube + 2 * base + 128
    apnic1Max = 192 * cube + 2 * base + 255
    apnic2Min = 198 * cube + 51 * square + 100 * base + 128
    apnic2Max = 198 * cube + 51 * square + 100 * base + 255
    apnic3Min = 203 * cube + 113 * base + 128
    apnic3Max = 203 * cube + 113 * base + 255
    ipv4Dict["apnic"] = [(apnic1Min, apnic1Max), (apnic2Min, apnic2Max), (apnic3Min, apnic3Max)]

    print apnic1Min, apnic1Max
    print apnic2Min, apnic2Max
    print apnic3Min, apnic3Max

    '''
    cnnic   192.0.2.128/26
    cnnic   198.51.100.128/26
    cnnic   203.0.113.128/26
    jpnic   203.0.113.128/26
    twnic   192.0.2.192/26
    twnic   192.0.3.128/26
    cnnic1Min = 192 * cube + 2 * base + 128
    cnnic1Max = 192 * cube + 2 * base + 255
    cnnic2Min = 198 * cube + 51 * square + 100 * base + 128
    cnnic2Max = 198 * cube + 51 * square + 100 * base + 255
    cnnic3Min = 203 * cube + 113 * base + 128
    cnnic3Max = 203 * cube + 113 * base + 255
    print cnnic1Min, cnnic1Max
    print cnnic2Min, cnnic2Max
    print cnnic3Min, cnnic3Max
    '''

def showStrListTuple(aDict):
    '''
    Each element is like:
    str: [(intMin, intMax), ...]
    '''
    for key in aDict.iterkeys():
        print key, "\t", #no "\n"
        for tup

def main():
    '''
    After initIPV4Dict(ipv4Dict), ipv4Dict is like:
    {"iana":[(0, 4294967295)],
    "apnic":[(3221226112, 3221226239), (3325256832, 3325256959), (3405803904, 3405804031)]}
    '''
    ipv4Dict = {}
    initIPV4Dict(ipv4Dict)
    showStrListTuple(ipv4Dict)

if __name__ == "__main__":
    main()
else:
    print "imported as an module"
