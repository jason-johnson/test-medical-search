import logging
import urllib
import os

from .results import Partial, Redo, Success

class SemanticScholar:
    def __init__(self):
        self.base_url = "https://api.semanticscholar.org/graph/v1/paper/search"
        self.key = os.environ.get('SS_API_KEY')

    async def search(self, session, searchkey, token={}):
        params = {
            'query': searchkey,
            'fields': 'title,abstract,publicationDate,authors,year,influentialCitationCount,openAccessPdf,tldr,citationCount,publicationTypes,fieldsOfStudy,s2FieldsOfStudy',
            'year': '2014-2024',
            'offset': token.get('offset', 0),
            'limit': token.get('limit', 100)
        }
        headers = {}

        if self.key:
            headers['X-API-KEY'] = self.key
            logging.debug("Using API key for Semantic Scholar")

        param_str = urllib.parse.urlencode(params, safe=',')

        async with session.get(self.base_url, params=param_str, headers=headers) as resp:
            response = await resp.json()
            if response.get('code', 0) == '429':
                return Redo(searchkey, self, token)
            
            result = []
            
            for data in response.get('data', []):
                result.append(Success(
                    searchkey=searchkey,
                    published_year=data.get('publicationDate', ''),
                    published_date=data.get('year', ''),
                    authors=[author.get('name', '') for author in data.get('authors', [])],
                    keywords=[],
                    title=data.get('title', ''),
                    abstract=data.get('abstract', 'NA'),
                    introduction='NA',
                    results='NA',
                    conclusion='NA',
                    figures=[],
                    pdf_url=(data.get('openAccessPdf', {}) or {}).get('url', ''),
                ))

            if response.get('total', 0) > token.get('offset', 0) + token.get('limit', 100):
                token['offset'] = response.get('next', 0)
                token['limit'] = token.get('limit', 100)
                redo = Redo(searchkey, self, token)
                result = Partial(result, redo)

            return result