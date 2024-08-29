import requests
import urllib

class SemanticScholar:
    def __init__(self):
        self.base_url = "https://api.semanticscholar.org/graph/v1/paper/search"

    def search(self, query, limit=100):
        params = {
            'query': query,
            'fields': 'title,abstract,publicationDate,authors,influentialCitationCount,openAccessPdf,tldr,citationCount,publicationTypes,fieldsOfStudy,s2FieldsOfStudy',
            'year': '2014-2024',
            'limit': limit
        }

        param_str = urllib.parse.urlencode(params, safe=',')

        response = requests.get(self.base_url, params=param_str)
        data = response.json()

        return data