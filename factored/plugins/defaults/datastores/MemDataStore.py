from factored.plugins import IDataStorePlugin


class MemDataStore(IDataStorePlugin):
    def initialize(self, settings):
        self.data = {}

    def store_access_request(self, host, subject, timestamp, payload):
        self.delete_access_requests(host, subject)
        self.data[host+subject] = dict(host=host, subject=subject, timestamp=timestamp, payload=payload)

    def get_access_request(self, host, subject):
        try:
            ar = self.data[host+subject]
            return (ar["host"], ar["subject"], ar["timestamp"], ar["payload"])
        except KeyError:
            return None

    def delete_access_requests(self, host, subject):
        try:
            del self.data[host+subject]
        except KeyError:
            pass
