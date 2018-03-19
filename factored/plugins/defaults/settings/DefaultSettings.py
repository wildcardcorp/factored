from factored.plugins import ISettingsPlugin


class DefaultSettings(ISettingsPlugin):
    def get_request_settings(self, host):
        return {
            # EXAMPLE:
            #"jwt.audience": "urn:factored",
            #"jwt.algorithm": "HS512",
            #"jwt.secret": "supersecret",
            #"jwt.cookie.name": "factored",
            #"jwt.cookie.age": "86400",
            #"jwt.cookie.secure": "false",
            #"jwt.cookie.httponly": "true",
            #"plugins.dirs": "/app/etc/",
            #"plugins.template": "DefaultTemplate",
            #"plugins.datastore": "SQLDataStore",
            #"plugins.finder": "EMailDomain",
            #"plugins.registrar": "MailerRegistration",
            #"plugin.DefaultTemplate.registration.enabled": "true",
            #"plugin.SQLDataStore.sql.url": "sqlite:////data/db.sqlite",
            #"plugin.EMailAuth.registration.enabled": "true",
            #"plugin.EMailAuth.code_timeout": "300",
            #"plugin.EMailAuth.code_length": "6",
            #"plugin.EMailAuth.code_hash_salt": "1XlPyGtXI2",
            #"plugin.EMailAuth.mail.domain": "localhost.localdomain",
            #"plugin.EMailAuth.mail.host": "debugmailer",
            #"plugin.EMailAuth.mail.port": "2525",
            #"plugin.EMailAuth.subject": "Authentication Request",
            #"plugin.EMailAuth.sender": "factored@localhost.localdomain",
            #"plugin.EMailAuth.body_template": "You have requested authentication.\nYour temporary access code is: {code}",
            #"plugin.EMailDomain.valid_domains": "wildcardcorp.com",
            #"plugin.MailerRegistration.instanceid": "Factored Instance 1",
            #"plugin.MailerRegistration.sender": "factored@localhost.localdomain",
            #"plugin.MailerRegistration.recipients": "registrar@localhost.localdomain",
            #"plugin.MailerRegistration.subject": "A registration request has been made",
            #"plugin.MailerRegistration.mail.host": "debugmailer",
            #"plugin.MailerRegistration.mail.port": "2525",
            #"plugin.MailerRegistration.mail.domain": "localhost.localdomain",
        }
