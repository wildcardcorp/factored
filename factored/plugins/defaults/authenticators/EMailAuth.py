import binascii
from datetime import datetime, timedelta
import hashlib
import os
import time

from pyramid_mailer.mailer import Mailer
from pyramid_mailer.message import Message

from factored.mail import create_message_id
from factored.plugins import IAuthenticatorPlugin

import logging
logger = logging.getLogger("factored.plugins")
auditlog = logging.getLogger('factored.audit')


class CodeTimeoutError(Exception):
    pass


class CodeIncorrectError(Exception):
    pass


class CodeSendingError(Exception):
    pass


class NoAccessRequestError(Exception):
    pass


class EMailAuth(IAuthenticatorPlugin):
    @property
    def display_name(self):
        return "Email"

    def get_code_hash(self, settings, code):
        salt = str.encode(settings.get("code_hash_salt", "7pLPnGtXI9"))
        bcode = str.encode(code)
        codehash = binascii.hexlify(
            hashlib.pbkdf2_hmac(
                "sha256",
                bcode,
                salt,
                100000))
        return codehash.decode('utf-8')

    def generate_and_send_code(self, host, settings, params, datastore, subject):
        # note: hexlify will generate 2 ascii chars for each byte, so the
        # length would be twice what we want, the "[0::2]" bit is just to
        # get every other character so we get the desired number of chars
        # specified by the 'code_length' setting
        codelen = int(settings.get("code_length", 6))
        newcode = binascii.hexlify(os.urandom(codelen))[0::2].decode("utf-8")

        # save a storable hash of the code
        codehash = self.get_code_hash(settings, newcode)
        timestamp = time.time()
        # TODO: need to handle case where there's an exception here, possibly
        # indicating an issue where the subject isn't a valid subject for
        # generating access requests but is otherwise a valid email
        datastore.store_access_request(host, subject, timestamp, codehash)

        # send code to user
        tmpl_msg = settings.get(
            "body_template",
            "You requested authentication.\n"
            "Your temporary access code is: {code}")
        msg_out = tmpl_msg.replace("{code}", newcode)
        msgdomain = settings.get("mail.domain", "localhost.localdomain")
        message = Message(
            subject=settings.get("subject", "2FA Authentication Code"),
            sender=settings.get("sender", "factored@localhost.localdomain"),
            recipients=[subject],
            body=msg_out,
            extra_headers={
                "Message-ID": create_message_id(domain=msgdomain),
            })
        mailer = Mailer.from_settings(settings)
        try:
            mailer.send_immediately(message, fail_silently=False)
            auditlog.info("code sent => {sub}".format(sub=subject))
        except Exception:
            logger.error("couldn't mail code", exc_info=True)
            raise CodeSendingError("Problem sending code. Please try again, "
                                   "or contact an administrator.")

    #
    # will raise exception on invalid code
    #
    def validate_code(self, host, settings, params, datastore, subject, code):
        ar = datastore.get_access_request(host, subject)
        if ar is None:
            raise NoAccessRequestError("No request found")
        stored_host = ar[0]
        stored_subject = ar[1]
        stored_timestamp = ar[2]
        stored_payload = ar[3]

        # Has the code timed out?
        try:
            code_timeout = int(settings.get("code_timeout", 300))
        except Exception:
            logger.error("failed to get code_timeout config", exc_info=True)
            code_timeout = 300
        timeout_delta = timedelta(seconds=code_timeout)
        expires_at = datetime.fromtimestamp(stored_timestamp) + timeout_delta
        if expires_at <= datetime.now():
            datastore.delete_access_requests(host, subject)
            auditlog.info("{} had code timeout".format(subject))
            raise CodeTimeoutError("Your code timed out, please try again.")

        # do the codes match?
        codehash = self.get_code_hash(settings, code)
        if codehash != stored_payload:
            auditlog.info("{} had code mismatch".format(subject))
            raise CodeIncorrectError("Incorrect code.")

    def handle(self, host, settings, params, datastore, finder):
        submit = params.get("submit", None)
        subject = params.get("email", None)
        code = params.get("code", None)
        error = None
        results = {
            "email": params.get("email", ""),
        }

        # must generate code and send to user to validate
        if submit == "email" and subject is not None:
            if not finder.is_valid_subject(host, subject):
                # invalid user presented, don't let the user know, but also
                # don't do any further work on the auth
                auditlog.info("{} ** invalid user".format(subject))
            else:
                try:
                    self.generate_and_send_code(host, settings, params, datastore, subject)
                    results["subject"] = subject
                except CodeSendingError as ex:
                    error = str(ex)

        # must confirm code and generate jwt or reject
        elif submit == "code" and code is not None:
            if not finder.is_valid_subject(host, subject):
                # invalid user presented, don't let the user know, but also
                # don't do any further work on the auth
                auditlog.info("{} ** bad code, invalid user".format(subject))
            else:
                try:
                    self.validate_code(host, settings, params, datastore, subject, code)
                    return { "authenticated": True, "subject": subject }
                except CodeTimeoutError as ex:
                    error = str(ex)
                except CodeIncorrectError as ex:
                    error = str(ex)
                except NoAccessRequestError as ex:
                    error = str(ex)

        if error is not None:
            results["err"] = error

        return results
