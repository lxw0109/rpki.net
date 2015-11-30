#!/usr/bin/python2.7
# FileName: ipCalculate.py
# Author: lxw
# Date: 2015-11-30

base = 256
square = base * base
cube = square * base

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
'''
cnnic1Min = 192 * cube + 2 * base + 128
cnnic1Max = 192 * cube + 2 * base + 255
cnnic2Min = 198 * cube + 51 * square + 100 * base + 128
cnnic2Max = 198 * cube + 51 * square + 100 * base + 255
cnnic3Min = 203 * cube + 113 * base + 128
cnnic3Max = 203 * cube + 113 * base + 255
print cnnic1Min, cnnic1Max
print cnnic2Min, cnnic2Max
print cnnic3Min, cnnic3Max
