#!/usr/bin/python2.7
# FileName: 3multipleCalc.py
# Author: lxw
# Date: 2016-04-19

def main():
    total = 0
    num = 0
    with open("./multiplePrefixSort") as f1:
        while 1:
            line = f1.readline()
            if not line:
                break
            total += int(line.strip().split()[0])
            num += 1
    print("number of prefixes: {0}\nnumber of ROAs: {1}\naverage prefixes in each ROA: {2}".format(total, num, total*1.0/num))

if __name__ == '__main__':
    main()
else:
    print("Being imported as a module.")

