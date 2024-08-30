import urllib

from .results import Redo, Success

class SemanticScholar:
    def __init__(self):
        self.base_url = "https://api.semanticscholar.org/graph/v1/paper/search"

    async def search(self, session, searchkey, limit=100):
        params = {
            'query': searchkey,
            'fields': 'title,abstract,publicationDate,authors,year,influentialCitationCount,openAccessPdf,tldr,citationCount,publicationTypes,fieldsOfStudy,s2FieldsOfStudy',
            'year': '2014-2024',
            'limit': limit
        }

        param_str = urllib.parse.urlencode(params, safe=',')

        async with session.get(self.base_url, params=param_str) as resp:
            response = await resp.json()
            if response.get('code', 0) == '429':
                return Redo(searchkey, self, limit)
            
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
                    figures=[]
                ))

            return result