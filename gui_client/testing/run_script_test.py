#!/usr/bin/python3
import time
import random


def main():
    time.sleep(1)
    print("Started processing.")
    time.sleep(1)
    print("Processing FASTQ file")
    time.sleep(1)
    print("Running mapper")
    time.sleep(1)
    if random.choice([True]) is True:
        raise Exception("This is a dummy error.")
    print("Finished processing.")
    return 0


if __name__ == '__main__':
    exit(main())
