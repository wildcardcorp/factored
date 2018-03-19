import re

from factored.plugins import IFinderPlugin

import logging
logger = logging.getLogger("factored.plugins")


class EMailDomain(IFinderPlugin):
    def initialize(self, settings):
        self.settings = settings

    def is_valid_subject(self, host, sub):
        # might not correctly get _all_ addresses, but should succeed on most
        # of the ones we're looking for. If more accuracy is needed, you might
        # want to create a more sophisticated plugin.
        m = re.search("^[a-zA-Z0-9_.+-]+@([a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+)$", sub)
        if m is None:
            return False

        domainpart = m.group(1).strip().lower()

        valid_domains = self.settings.get("valid_domains", None)
        if valid_domains is None:
            logger.error("valid_domains not configured for emaildomain plugin")
            return False
        valid_domains = valid_domains.splitlines()

        for d in valid_domains:
            if d.strip().lower() == domainpart:
                return True

        return False
