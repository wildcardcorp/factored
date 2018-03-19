from pyramid_mailer.mailer import Mailer
from pyramid_mailer.message import Message

from factored.mail import create_message_id
from factored.plugins import IRegistrationPlugin


import logging
logger = logging.getLogger("factored.plugins")
auditlog = logging.getLogger('factored.audit')


class MailerRegistration(IRegistrationPlugin):
    def handle(self, host, settings, params, datastore, finder):
        if params.get("submit", None) == "requestaccess":
            sender = settings.get("sender", None)
            recipientstr = settings.get("recipients", None)
            emailsubject = settings.get("subject", None)

            if sender is None or recipientstr is None or emailsubject is None:
                logger.error("MailerRegistration does not have 'sender', "
                             "'recipients', and/or 'subject' configured")
                return {}

            recipients = [a.strip() for a in recipientstr.splitlines() if len(a.strip()) > 0]

            reqemail = params.get("email", None)
            reqfname = params.get("firstname", None)
            reqlname = params.get("lastname", None)
            if reqemail is None or reqfname is None or reqlname is None:
                logger.error("registration submitted without valid form data")
                return {}

            # send request to configured email
            instanceid = settings.get("instanceid", None)
            instancestr = "on {instanceid} ".format(instanceid=instanceid) \
                          if instanceid is not None else ""
            msg_out = "Access has been requested {idstr}for the following " \
                      "user:\n\n{fname} {lname}\n{email}" \
                      .format(idstr=instancestr, fname=reqfname, lname=reqlname, email=reqemail)
            msgdomain = settings.get("mail.domain", "localhost.localdomain")
            message = Message(
                subject=emailsubject,
                sender=sender,
                recipients=recipients,
                body=msg_out,
                extra_headers={
                    "Message-ID": create_message_id(domain=msgdomain),
                })
            mailer = Mailer.from_settings(settings)
            try:
                mailer.send_immediately(message, fail_silently=False)
                auditlog.info("sent registration request ({fname} {lname} {email}) "
                              "=> {recipients}".format(
                                  fname=reqfname,
                                  lname=reqlname,
                                  email=reqemail,
                                  recipients=", ".join(recipients)))
            except:
                logger.error("couldn't mail registration request", exc_info=True)
                raise Exception("Problem sending code. Please try again, "
                                "or contact an administrator.")

        return {}
