#!/usr/bin/env python
"""A noddy fake smtp server."""

import smtpd
import asyncore
from pprint import pprint


class FakeSMTPServer(smtpd.SMTPServer):
    """A Fake smtp server"""

    def __init__(*args, **kwargs):
        print("Running fake smtp server on port 25")
        smtpd.SMTPServer.__init__(*args, **kwargs)

    def process_message(*args, **kwargs):
        pprint(args)
        pprint(kwargs)

if __name__ == "__main__":
    smtp_server = FakeSMTPServer(('localhost', 25), None)
    try:
        asyncore.loop()
    except KeyboardInterrupt:
        smtp_server.close()
