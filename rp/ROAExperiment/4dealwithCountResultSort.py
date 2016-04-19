#!/usr/bin/python2.7
# FileName: 4dealwithCountResultSort.py
# Author: lxw
# Date: 2016-04-19

def main():
    with open("./countResultSort.csv") as f1:
        with open("./countResultProduct.csv", "w") as f2:
            while 1:
                line = f1.readline()
                if not line:
                    break
                lineList = line.strip().split(",")
                f2.write("{0},{1},{2}\n".format(lineList[0], lineList[1], int(lineList[0])*int(lineList[1])))

if __name__ == '__main__':
    main()
else:
    print("Being imported as a module.")

