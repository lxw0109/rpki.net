#!/usr/bin/python2.7
# FileName: demo.py
# Author: lxw
# Date: 2015-12-01

import logging

def main():
    #logging.basicConfig(level=logging.DEBUG, format="%(asctime)s %(filename)s[line:%(lineno)d] %(levelname)s %(message)s", datefmt="%a, %d %b %Y %H:%M:%S", filename="demo.log", filemod="w")
    logging.basicConfig(level=logging.DEBUG, format="%(asctime)s %(filename)s[line:%(lineno)d] %(levelname)s %(message)s", datefmt="%a, %d %b %Y %H:%M:%S", filemod="w")

    logging.debug("debug message")
    logging.info("info message")
    logging.warning("warning message")

if __name__ == '__main__':
    main()
else:
    print("Being imported as a module.")

