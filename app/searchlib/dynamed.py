from .results import Redo, Success


class Dynamed:
    def __init__(self, session):
        self.base_url = "https://apis.ebsco.com/medsapi-dynamed/v2/content/search"
        self.headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Authorization": "Bearer TOKEN"
        }
        self.session = session

    async def search(self, searchkey, token={}):
        params = {
            'query': searchkey,
            'fields': ['title'],
        }

        async with self.session.get(self.base_url, json=params, headers=self.headers) as resp:
            response = await resp.json()
            if response.get('name', '') == 'Unauthorized':
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
                    figures=[]
                ))

            return result
