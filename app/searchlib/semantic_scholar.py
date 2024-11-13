import logging
import urllib
from datetime import datetime

import requests

from .results import Partial, Redo, Success

def search(self, api_key, searchkey, token=None):
    base_url = "https://api.semanticscholar.org/graph/v1/paper/search/bulk"
    current_year = datetime.now().year

    params = {
        'query': f'"{searchkey}"',
        'fields': 'title,abstract,publicationDate,authors,year,influentialCitationCount,openAccessPdf,citationCount,publicationTypes,fieldsOfStudy,s2FieldsOfStudy',
        'year': f'{current_year-10}-{current_year}',
        'sort': 'citationCount:desc',
    }
    if token:
        params['token'] = token

    headers = {}

    if api_key:
        headers['X-API-KEY'] = api_key
        logging.debug("Using API key for Semantic Scholar")

    param_str = urllib.parse.urlencode(params, safe=',"')
    response = requests.get(base_url, params=param_str, headers=headers)
    response.raise_for_status()
    
    result = []
    
    for data in response.get('data', []):
        result.append(Success(
            source=self.__class__.__name__,
            searchkey=searchkey,
            published_year=data.get('publicationDate', ''),
            published_date=data.get('year', ''),
            authors=[author.get('name', '') for author in data.get('authors', [])],
            keywords=[],
            citations=data.get('citationCount', 0),
            title=data.get('title', ''),
            abstract=data.get('abstract', 'NA'),
            introduction='NA',
            results='NA',
            conclusion='NA',
            figures=[],
            pdf_url=(data.get('openAccessPdf', {}) or {}).get('url', ''),
        ))

    if response.get('token'):
        token = response.get('token')
        redo = Redo(searchkey, self, token)
        result = Partial(result, redo)

    return result