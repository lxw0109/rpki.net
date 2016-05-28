#!/usr/bin/python2.7
# FileName: count.py
# Author: lxw
# Date: 2016-04-16

def main():
    f1 = open("./multiplePrefixSort")
    f2 = open("countResult.csv", "w")
    countDict = {}
    while 1:
        line = f1.readline()
        if not line:
            break
        num = int(line.strip().split()[0])
        if num in countDict:
            countDict[num] += 1
        else:
            countDict[num] = 1
    for key in countDict.keys():
        f2.write("{0},{1}\n".format(key, countDict[key]))

    f1.close()
    f2.close()


if __name__ == '__main__':
    main()
else:
    print("Being imported as a module.")

