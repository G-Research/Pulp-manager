import json

class MockResponse(object):
    def __init__(self, status_code, text, json_output=None):
        self.status_code = status_code
        self.text = text
        self._json = json_output

    def json(self):
        return self._json
