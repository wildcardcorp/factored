from factored.plugins import IDataStorePlugin


class MemDataStore(IDataStorePlugin):
    def initialize(self, settings):
        self.data = {}

    def store_access_request(self, subject, timestamp, payload):
        self.delete_access_requests(subject)
        self.data[subject] = dict(subject=subject, timestamp=timestamp, payload=payload)

    def get_access_request(self, subject):
        try:
            ar = self.data[subject]
            return (ar["subject"], ar["timestamp"], ar["payload"])
        except KeyError:
            return None

    def delete_access_requests(self, subject):
        try:
            del self.data[subject]
        except KeyError:
            pass
