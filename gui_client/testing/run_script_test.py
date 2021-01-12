#!/usr/bin/python3
import time
import random


def main():
    time.sleep(1)
    print("Hellloo")
    if random.choice([True, False]) is True:
        raise Exception("Error>>>>> YES")
    print("Ran without errors")
    return 0


if __name__ == '__main__':
    exit(main())
