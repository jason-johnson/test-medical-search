import requests


class Dynamed:
    def __init__(self):
        self.base_url = "https://apis.ebsco.com/medsapi-dynamed/v2/content/search"
        self.headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Authorization": "Bearer TOKEN"
        }

    def search(self, query, limit=10, sort='relevance', filter='all'):
        params = {
            'query': query,
            'fields': ['title'],
        }

        response = requests.post(self.base_url, json=params, headers=self.headers)
        data = response.json()

        return data
