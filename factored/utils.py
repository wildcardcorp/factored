from datetime import datetime
from hashlib import sha1
import os
import base64
import random


def generate_code(length=10):
    return base64.b32encode(os.urandom(length))


def make_random_code(length=255):
    return sha1(sha1(str(random.random())).
        hexdigest()[:5] + str(datetime.now().microsecond)).hexdigest()[:length]


def get_barcode_image(username, secretkey):
    url = "https://www.google.com/chart"
    url += "?chs=200x200&chld=M|0&cht=qr&chl=otpauth://totp/"
    url += username + "%3Fsecret%3D" + secretkey
    return url
