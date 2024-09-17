import logging
import os
import urllib
import xmltodict
from .results import Redo, Success


class PubMed:
    def __init__(self):
        self.base_search_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
        self.base_details_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
        self.key = os.environ.get('PUBMED_API_KEY')
        self.headers = {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9, application/json",
        }

        if self.key:
            self.headers['Authorization'] = f'Bearer {self.key}'
            logging.debug("Using API key for Semantic Scholar")

    async def _get_ids(self, session, searchkey, token={}):
        params = {
            'db': 'pubmed',
            'retmode': 'json',
            'retmax': 10_000,
            'retstart': token.get('retstart', 0),
            'term': f'"{searchkey}"[Title:~3]',
        }

        param_str = urllib.parse.urlencode(params, safe=',"][~:')

        async with session.get(self.base_search_url, params=param_str, headers=self.headers) as resp:
            response = await resp.json()

            if resp.status != 200:
                logging.error(f"Error: {response}")
                return Redo(searchkey=searchkey, token=token)
            else:
                return response
            
    async def _get_details(self, session, ids, token):
        params = {
            'db': 'pubmed',
            'retmode': 'xml',
            'retmax': 10_000,
        }

        param_str = urllib.parse.urlencode(params, safe=',"][~:')

        first_ids = ids[:400]

        async with session.post(self.base_details_url, params=param_str, headers=self.headers, data={'id': ','.join(ids)}) as resp:
            if resp.status != 200:
                logging.error(f"Error: {resp.error}")
                return Redo(searchkey="id", token=token)
            else:
                response = await resp.text()
                response = xmltodict.parse(response)
                return response

    async def search(self, session, searchkey, token={}):
        search_result = await self._get_ids(session, searchkey, token)

        if search_result.__class__.__name__ == 'Redo':
            return search_result
        
        ids = search_result.get('esearchresult', {}).get('idlist', [])
        details_result = await self._get_details(session, ids, token)
            
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
