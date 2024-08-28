import requests


class SemanticScholar:
    def __init__(self):
        self.base_url = "https://api.semanticscholar.org/graph/v1/paper/autocomplete"

    def search(self, query, limit=10):
        params = {
            'query': query,
        }

        response = requests.get(self.base_url, params=params)
        data = response.json()

        return data