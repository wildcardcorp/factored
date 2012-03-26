import time
from datetime import datetime
import os
import base64
import random
import struct
import hmac
import hashlib


def generate_random_google_code(length=10):
    return base64.b32encode(os.urandom(length))


def make_random_code(length=255):
    return hashlib.sha1(hashlib.sha1(str(random.random())).
        hexdigest()[:5] + str(datetime.now().microsecond)).hexdigest()[:length]


def get_barcode_image(username, secretkey):
    url = "https://www.google.com/chart"
    url += "?chs=200x200&chld=M|0&cht=qr&chl=otpauth://totp/"
    url += username + "%3Fsecret%3D" + secretkey
    return url


def get_google_auth_code(secretkey, tm=None):
    if tm is None:
        tm = int(time.time() / 30)
    secretkey = base64.b32decode(secretkey)
    # convert timestamp to raw bytes
    b = struct.pack(">q", tm)

    # generate HMAC-SHA1 from timestamp based on secret key
    hm = hmac.HMAC(secretkey, b, hashlib.sha1).digest()

    # extract 4 bytes from digest based on LSB
    offset = ord(hm[-1]) & 0x0F
    truncatedHash = hm[offset:offset + 4]

    # get the code from it
    code = struct.unpack(">L", truncatedHash)[0]
    code &= 0x7FFFFFFF
    code %= 1000000
    return "%06d" % code


def get_context(req, **kwargs):
    kwargs['static_path'] = req.registry['settings']['static_path']
    return kwargs


def create_user(username):
    from factored.models import DBSession, User
    secret = generate_random_google_code()
    user = User(username=username, secret=secret)
    DBSession.add(user)
    return user
