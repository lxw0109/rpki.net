#!/usr/bin/python2.7
#coding: utf-8
# FileName: preCheckASN.py
# Author: lxw
# Date: 2015-11-30

import sys

def showStrListTuple(aDict):
    '''
    Each element is like:
    str: [(intMin, intMax), ...]
    '''
    for key in aDict.iterkeys():
        print key, "\t",
        for intMin, intMax in aDict[key]:
            print "{0}-{1},".format(intMin, intMax),
        print ""    #newline


def readFile(filename):
    '''
    create content(each line) from filename.
    yield is good.
    '''
    with open(filename, "r") as f:
        for line in f:
            yield line

def getHandle():
    '''
    Get handle from /etc/rpki.conf
    '''
    for line in readFile("/etc/rpki.conf"):
        line = line.strip()
        if line.startwith("handle"):
            lineList = line.split()
            return lineList[2]
    return ""

def initASDict(asDict):
    '''
    Here we just initialize AS info by manual.
    When Left-Right protocol is standardized, this should be initialized automatically with the authoratitive resource-holding data.
    '''
    #IANA
    '''
    ASN:       0-4294967295
    '''
    ianaMin = 0
    ianaMax = 4294967295
    asDict["iana"] = [(ianaMin, ianaMax)]

    #APNIC
    '''
    ASN:       64497-64510,65537-65550
    '''
    apnic1Min = 64497
    apnic1Max = 64510
    apnic2Min = 65537
    apnic2Max = 65550
    asDict["apnic"] = [(apnic1Min, apnic1Max), (apnic2Min, apnic2Max)]

def checkASN(handle, fileName, asDict):
    '''
    ./preCheckASN.py -i apnic abc.csv
    handle = apnic
    fileName = abc.csv
    The format of "fileName" file is like:
    cnnic	64498-64505
    cnnic	65540
    jpnic	65540-65550
    '''
    lineno = 0
    childASDict = {}
    for line in readFile(fileName):
        lineno += 1
        lineList = line.split()
        #only care about lineList[1].
        if "-" in lineList[1]:  #range
            asRange = lineList[1].split("-")
            asMin = int(asRange[0])
            asMax = int(asRange[1])
        else:
            asMin = int(lineList[1])
            asMax = int(lineList[1])

        #Resource-holding check(未获授权资源分配)
        flag = False
        for low, high in asDict[handle]:
            if asMin >= low and asMax <= high:
                #print "OK: {0}-{1} is in range {2}-{3}.".format(asMin, asMax, low, high)
                flag = True
                break    #OK
        if not flag:
            #print "Error: {0}-{1} does not belong to {2}.".format(asMin, asMax, handle)
            #return 1    #illegal
            if asMin == asMax:
                unAuthAS = str(asMin)
            else:
                unAuthAS = "{0}-{1}".format(asMin, asMax)

            print "Unauthorized Resources Found:\n  {0} [line:{1}] \"{2}\" \n  AS{3} does not belong to {4}".format(fileName, lineno, line.strip(), unAuthAS, handle)
            return 1
        if lineList[0] in childASDict:
            childASDict[lineList[0]].append((asMin, asMax))
        else:
            childASDict[lineList[0]] = [(asMin, asMax)]

    #Out of "for" scope.
    #Resource Re-Allocation check(资源的重复分配)
    '''
    csv file:
    cnnic	64498-64505
    cnnic	65540
    jpnic	65540-65550
    twnic	64497
    twnic	65551

    childASDict:
    jpnic   65540-65550,
    twnic   64497-64497,
    cnnic   64498-64505, 65540-65540,
    '''
    overlapFlag = False
    #showStrListTuple(childASDict)
    for key in childASDict.keys():
        for asMin, asMax in childASDict[key]:
            for key1 in childASDict.keys():
                if key1 != key:
                    for asMin1, asMax1 in childASDict[key1]:
                        if asMin > asMax1 or asMax < asMin1:
                            continue
                        else:
                            asOverlapMin = max(asMin, asMin1)
                            asOverlapMax = min(asMax, asMax1)
                            overlapFlag = True
                            break   #Re-Allocation Found
                if overlapFlag:
                    break
            if overlapFlag:
                break
        if overlapFlag:
            break

    if overlapFlag:     #Re-Allocation Found
        if asOverlapMin == asOverlapMax:
            reAllocAS = str(asOverlapMin)
        else:
            reAllocAS = "{0}-{1}".format(asOverlapMin, asOverlapMax)
        print "Resources Re-Allocation Found:\n  {0} \"{1}\" \n  AS{1} are allocated more than once.".format(fileName, reAllocAS)
        return 1


def main():
    #Initialize
    asDict = {}
    initASDict(asDict)
    #showStrListTuple(asDict)

    #Get input
    #    0         1    2      3
    #./preCheckASN.py -i apnic abc.csv
    length = len(sys.argv)
    #length is bigger than 2.
    if length < 3:
        handle = getHandle()
        fileName = sys.argv[1].strip()
    else:
        handle = sys.argv[2].strip()
        fileName = sys.argv[3].strip()
    #print "handle: {0}, fileName: {1}".format(handle, fileName)
    result = checkASN(handle, fileName, asDict)
    exit(result)

if __name__ == "__main__":
    main()
else:
    print "imported as an module"
