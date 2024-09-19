import argparse
import json
import sys
from search.dynamed import Dynamed
from search.pubmed import PubMed
from search.semantic_scholar import SemanticScholar
import asyncio
import aiohttp
import aiofiles


import logging


async def query(client, query, session):
    logging.info(f'Querying {client.__class__.__name__}')
    resp = await client.search(session, query)
    return resp

async def query_redo(redo, session):
    logging.info(f'Redoing {redo}')
    resp = await redo.client.search(session, redo.searchkey, redo.token)
    return resp

def process_results(results, success=[]):
    redo = [result for result in results if result.__class__.__name__ == 'Redo']
    successes = [result for result in results if not result.__class__.__name__ in ['Redo', 'Partial']]
    partials = [result for result in results if result.__class__.__name__ == 'Partial']
    
    for partial in partials:
        successes.append(partial.successes)
        redo.append(partial.redo)

    for s in successes:
        data = [d.data for d in s]
        success.extend(data)
    return redo, success, len(successes) > 0

async def search(search_keywords, concurrent, retries):
    conn = aiohttp.TCPConnector(limit=concurrent)
    # set total=None because the POST is really slow and the defeault will cause any request still waiting to be processed after "total" seconds to fail.  Also set read to 10 minutes
    timeout = aiohttp.ClientTimeout(total=None, sock_connect=10, sock_read=600)

    async with aiohttp.ClientSession(connector=conn, timeout=timeout) as session:
        results = await asyncio.gather(*(query(client, searchkeyword, session) for client in [SemanticScholar(), PubMed()] for searchkeyword in search_keywords))
        logging.info("Finalized all. Return is a list of len {} outputs.".format(len(results)))

        redo, success, _ = process_results(results)

        while redo and retries > 0:
            logging.info(f"Retrying {len(redo)} results.")
            results = await asyncio.gather(*(query_redo(r, session) for r in redo))
            redo, success, any_succeded = process_results(results, success)
            if not any_succeded:
                retries -= 1

        logging.info(f"Success: {len(success)}, Failures: {len(redo)}")

        return success


async def main():
    parser = argparse.ArgumentParser(description='Script to perform medical search.')
    parser.add_argument('-f', '--query_file', type=str, help="The file containing the search query", default="query.txt")
    parser.add_argument('-o', '--output_file', type=str, help="The file to write the output to", default=None)
    parser.add_argument('--with-pdf-only', action='store_true', help="Only return results with PDFs", default=False)
    parser.add_argument("--concurrent", type=int, help="The number of concurrent requests to make", default=10)
    parser.add_argument('-r', '--retries', type=int, default=3, help='Number of retries to make')
    parser.add_argument('-v', '--verbose', action='count', help='Enable verbose mode', default=0)
    
    args = parser.parse_args()

    if args.verbose == 1:
        logging.getLogger().setLevel(logging.INFO)
    elif args.verbose > 1:
        logging.getLogger().setLevel(logging.DEBUG)

    search_keywords = []
    async with aiofiles.open(args.query_file, mode='r') as f:
        async for line in f:
            search_keywords.append(line.strip())

    results = await search(search_keywords, args.concurrent, args.retries)

    if args.output_file:
        async with aiofiles.open(args.output_file, mode='w') as f:
            for s in results:
                if args.with_pdf_only and not s['pdf_url']:
                    continue
                await f.write(json.dumps(s) + '\n')
    else:
        for s in results:
            if args.with_pdf_only and not s['pdf_url']:
                continue
            print(json.dumps(s))

if __name__ == '__main__':
    logging.basicConfig(stream=sys.stderr, level=logging.WARN)
    asyncio.run(main())

@app.route(route="HttpExample", auth_level=func.AuthLevel.ANONYMOUS)
def HttpExample(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Python HTTP trigger function processed a request.')

    name = req.params.get('search_keywords')
    if not name:
        try:
            req_body = req.get_json()
        except ValueError:
            pass
        else:
            name = req_body.get('search_keywords')

    if name:
        return func.HttpResponse(f"Hello, {name}. This HTTP triggered function executed successfully.")
    else:
        return func.HttpResponse(
             "This HTTP triggered function executed successfully. Pass a name in the query string or in the request body for a personalized response.",
             status_code=200
        )