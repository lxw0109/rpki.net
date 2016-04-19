#!/usr/bin/python2.7
#coding: utf-8
#如果想有中文注释就必须得有上面的语句
# FileName: deal.py
# Author: lxw
# Date: 2016-04-16

def main():
    #f1 = open("result201604161334")
    f1 = open("./resultUniq")
    f2 = open("singlePrefix", "w")
    f3 = open("multiplePrefix", "w")
    while 1:
        line = f1.readline()
        if not line:
            break
        prefixNum = len(line.strip().split()) - 2
        if prefixNum == 1:  #single prefix
            f2.write(line)
        elif prefixNum > 1: #multiple prefix
            f3.write("{0} {1}".format(prefixNum, line))
        else:
            print(line)

    f1.close()
    f2.close()
    f3.close()

if __name__ == '__main__':
    main()
else:
    print("Being imported as a module.")

