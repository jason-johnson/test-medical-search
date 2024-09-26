import json


class Success:
    def __init__(self, source, searchkey, published_year, published_date, authors, keywords, title, abstract, introduction, results, conclusion, figures, pdf_url):
        self.data = {
            "source": source,
            "searchkey": searchkey,
            "metadata": {
                "published_year": published_year,
                "published_date": published_date,
                "authors": authors,
            },
            "keywords": keywords,
            "title": title,
            "abstract": abstract,
            "introduction": introduction,
            "results": results,
            "conclusion": conclusion,
            "figures": figures,
            "pdf_url": pdf_url
        }

    def __str__(self):
        return json.dumps(self.data, indent=4)
    
    def __repr__(self):
        return f"Success({self.data})"
    
class Partial:
    def __init__(self, successes, redo):
        self.successes = successes
        self.redo = redo

    def __str__(self):
        return f'Partial({self.redo.searchkey})'
    
    def __repr__(self):
        return f"Partial({self.redo.searchkey}, {self.redo.token})"
    
class Redo:
    def __init__(self, searchkey, client, token):
        self.searchkey = searchkey
        self.client = client
        self.token = token

    def __str__(self):
        return f'Redo({self.searchkey} with {self.client.__class__.__name__})'
    
    def __repr__(self):
        return f"Redo({self.searchkey}, {self.client}, {self.token})"