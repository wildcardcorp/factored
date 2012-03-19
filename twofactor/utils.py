import os
import base64


def generate_code():
    return base64.b32encode(os.urandom(10))


def get_barcode_image(username, secretkey):
    url = "https://www.google.com/chart"
    url += "?chs=200x200&chld=M|0&cht=qr&chl=otpauth://totp/"
    url += username + "%3Fsecret%3D" + secretkey
    return url
