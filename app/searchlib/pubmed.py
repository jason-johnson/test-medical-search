import asyncio
import logging
import os
import urllib
import xmltodict
from .results import Redo, Success


class PubMed:
    def __init__(self, session):
        self.base_search_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
        self.base_details_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
        self.key = os.environ.get('PUBMED_API_KEY')
        self.session = session
        self.headers = {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9, application/json",
        }

        if self.key:
            self.headers['Authorization'] = f'Bearer {self.key}'
            logging.debug("Using API key for Semantic Scholar")

    async def _get_ids(self, searchkey, token={}):
        params = {
            'db': 'pubmed',
            'retmode': 'json',
            'retmax': 10_000,
            'retstart': token.get('retstart', 0),
            'term': f'"{searchkey}"[Title:~3] AND free full text[sb]',
        }

        param_str = urllib.parse.urlencode(params, safe=',"][~:')

        async with self.session.get(self.base_search_url, params=param_str, headers=self.headers) as resp:
            if resp.status != 200:
                response = await resp.text()
                logging.error(f"Error: {self.__class__.__name__}({searchkey}) - {response}")
                return Redo(searchkey, self, token)
            else:
                response = await resp.json()
                return response
            
    async def _get_details(self, ids, token):
        params = {
            'db': 'pubmed',
            'retmode': 'xml',
            'retmax': 10_000,
        }

        param_str = urllib.parse.urlencode(params, safe=',"][~:')

        async with self.session.post(self.base_details_url, params=param_str, headers=self.headers, data={'id': ','.join(ids)}) as resp:
            if resp.status != 200:
                logging.error(f"Error: {resp.error}")
                return Redo(searchkey="id", token=token)
            else:
                response = await resp.text()
                data = xmltodict.parse(response)
                return data
            
    async def _get_url(self, pmc_ids):
        for pmc_id in pmc_ids:
            url = f"https://www.ncbi.nlm.nih.gov/pmc/articles/{pmc_id}/pdf/"
            try:
                async with self.session.head(url) as resp:
                    logging.debug(f"Checking {url} - {resp.status}")
                    if resp.status == 200:
                        return url
                    elif resp.status == 303:
                        location = resp.headers.get('location')
                        return location
            except Exception as e:
                logging.error(f"Error: {self.__class__.__name__}({pmc_id}) - {e}")
                continue
                
        return ''
    
    async def _process_article(self, searchkey, entry):
        data = entry.get('MedlineCitation', {})
        pmc_id = data.get('PMID', {}).get('#text', '')
        article_ids = entry.get('PubmedData', {}).get('ArticleIdList', {}).get('ArticleId', [])
        if article_ids.__class__.__name__ == 'dict':
            article_ids = [article_ids]
        pmc_ids = [pmc_id] + [id.get('#text', '') for id in article_ids if id.get('@IdType') == 'pmc']
        article = data.get('Article', {})
        published_year = data.get('Article', {}).get('Journal', {}).get('JournalIssue', {}).get('PubDate', {}).get('Year', '')
        pub_date = data.get('Article', {}).get('Journal', {}).get('JournalIssue', {}).get('PubDate', {})
        published_date = f'{pub_date.get("Year", "")}-{pub_date.get("Month", "")}-{pub_date.get("Day", "")}'
        author_list = article.get('AuthorList', {}).get('Author', [])
        if author_list.__class__.__name__ == 'dict':
            author_list = [author_list]
        authors = [f"{author.get('ForeName', '')} {author.get('LastName', '')}" for author in author_list]
        keywords = [keyword.get('#text', '') for keyword in article.get('KeywordList', [])]
        title = article.get('ArticleTitle', '')
        abstract = article.get('Abstract', {}).get('AbstractText')
        if abstract is not None:
            if abstract.__class__.__name__ == 'list':
                abstract = [f"{a.get('@Label', '')}\n{a.get('#text', '')}" for a in abstract]
                abstract = ' '.join(abstract)

        citationRefList = entry.get('PubmedData', {}).get('ReferenceList', {})
        if citationRefList.__class__.__name__ == 'dict':
            citationRefList = citationRefList.get('Reference', [])
        elif citationRefList.__class__.__name__ == 'list':
            refs = [ref.get('Reference') for ref in citationRefList]
            citationRefList = [ref for ref in refs if ref is not None]

        citations = len(citationRefList)

        pdf_url = await self._get_url(pmc_ids),

        return Success(
                source=self.__class__.__name__,
                searchkey=searchkey,
                published_year=published_year,
                published_date=published_date,
                authors=authors,
                keywords=keywords,
                citations=citations,
                title=title,
                abstract=abstract,
                introduction='NA',
                results='NA',
                conclusion='NA',
                figures=[],
                pdf_url=pdf_url[0],
            )

    async def search(self, searchkey, token={}):
        search_result = await self._get_ids(searchkey, token)

        if search_result.__class__.__name__ == 'Redo':
            return search_result
        
        ids = search_result.get('esearchresult', {}).get('idlist', [])

        details_result = None
        try:
            details_result = await self._get_details(ids, token)
        except Exception as e:
            logging.error(f"Error: {self.__class__.__name__}({searchkey}) - {e}")
            return Redo(searchkey, self, token)
        
        articles = details_result.get('PubmedArticleSet', {}).get('PubmedArticle', [])

        result = await asyncio.gather(*(self._process_article(searchkey, article) for article in articles))
        
        return result
