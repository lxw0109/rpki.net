#!/usr/bin/python2.7
# FileName: 5calculateEachRange.py
# Author: lxw
# Date: 2017-07-05

def main():
    # Format of each file: num of prefix in each ROA, ROA_count, prefix_count
    total_roa_count = 0
    total_prefix_count = 0
    roa_count = 0
    prefix_count = 0
    with open("./2-10") as f1:
        while 1:
            line = f1.readline()
            if not line:
                break
            lineList = line.strip().split(",")
            roa_count += int(lineList[1].strip())
            prefix_count += int(lineList[2].strip())
    print("[2-10]roa_count: {0}, prefix_count: {1}\n".format(roa_count, prefix_count))
    total_roa_count += roa_count
    total_prefix_count += prefix_count

    roa_count = 0
    prefix_count = 0
    with open("./11-50") as f1:
        while 1:
            line = f1.readline()
            if not line:
                break
            lineList = line.strip().split(",")
            roa_count += int(lineList[1].strip())
            prefix_count += int(lineList[2].strip())
    print("[11-50]roa_count: {0}, prefix_count: {1}\n".format(roa_count, prefix_count))
    total_roa_count += roa_count
    total_prefix_count += prefix_count

    roa_count = 0
    prefix_count = 0
    with open("./51-100") as f1:
        while 1:
            line = f1.readline()
            if not line:
                break
            lineList = line.strip().split(",")
            roa_count += int(lineList[1].strip())
            prefix_count += int(lineList[2].strip())
    print("[51-100]roa_count: {0}, prefix_count: {1}\n".format(roa_count, prefix_count))
    total_roa_count += roa_count
    total_prefix_count += prefix_count

    roa_count = 0
    prefix_count = 0
    with open("./gt100") as f1:
        while 1:
            line = f1.readline()
            if not line:
                break
            lineList = line.strip().split(",")
            roa_count += int(lineList[1].strip())
            prefix_count += int(lineList[2].strip())
    print("[gt100]roa_count: {0}, prefix_count: {1}\n".format(roa_count, prefix_count))
    total_roa_count += roa_count
    total_prefix_count += prefix_count

    print("total_roa_count: {0}, total_prefix_count: {1}\n".format(total_roa_count, total_prefix_count))

if __name__ == '__main__':
    main()
else:
    print("Being imported as a module.")

