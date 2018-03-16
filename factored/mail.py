import binascii
import os
import time


def create_message_id(domain='localhost', mid=None):
    if mid is None:
        ts = str(time.time())
        rand = binascii.hexlify(os.urandom(10))
        mid = "{ts}-{rand}".format(ts=ts, rand=rand)
    return "<{mid}@{domain}>".format(mid=mid, domain=domain)


