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
                logging.error(f"Error: {self.__class__.__name__}({searchkey}) - {response}")
                return Redo(searchkey, self, token)
            else:
                return response
            
    async def _get_details(self, session, ids, token):
        params = {
            'db': 'pubmed',
            'retmode': 'xml',
            'retmax': 10_000,
        }

        param_str = urllib.parse.urlencode(params, safe=',"][~:')

        async with session.post(self.base_details_url, params=param_str, headers=self.headers, data={'id': ','.join(ids)}) as resp:
            if resp.status != 200:
                logging.error(f"Error: {resp.error}")
                return Redo(searchkey="id", token=token)
            else:
                response = await resp.text()
                data = xmltodict.parse(response)
                return data

    async def search(self, session, searchkey, token={}):
        search_result = await self._get_ids(session, searchkey, token)

        if search_result.__class__.__name__ == 'Redo':
            return search_result
        
        ids = search_result.get('esearchresult', {}).get('idlist', [])

        try:
            details_result = await self._get_details(session, ids, token)
            result = []
            articles = details_result.get('PubmedArticleSet', {}).get('PubmedArticle', [])

            for a in articles:
                data = a.get('MedlineCitation', {})
                pmc_id = data.get('PMID')
                article = data.get('Article', {})
                published_year = data.get('Article', {}).get('Journal', {}).get('JournalIssue', {}).get('PubDate', {}).get('Year', '')
                pub_date = data.get('Article', {}).get('Journal', {}).get('JournalIssue', {}).get('PubDate', {})
                published_date = f'{pub_date.get("Year", "")}-{pub_date.get("Month", "")}-{pub_date.get("Day", "")}'
                authors = [f"{author.get('ForeName', '')} {author.get('LastName', '')}" for author in article.get('AuthorList', {}).get('Author', [])]
                keywords = [keyword.get('#text', '') for keyword in article.get('KeywordList', [])]
                title = article.get('ArticleTitle', '')
                abstract = article.get('Abstract', {}).get('AbstractText', '')

                result.append(Success(
                    source=self.__class__.__name__,
                    searchkey=searchkey,
                    published_year=published_year,
                    published_date=published_date,
                    authors=authors,
                    keywords=keywords,
                    title=title,
                    abstract=abstract,
                    introduction='NA',
                    results='NA',
                    conclusion='NA',
                    figures=[],
                ))

                return result

        except Exception as e:
            logging.error(f"Error: {self.__class__.__name__}({searchkey}) - {e}")
            return Redo(searchkey, self, token)
