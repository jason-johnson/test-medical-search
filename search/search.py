import argparse
import sys
from search.dynamed import Dynamed
from search.semantic_scholar import SemanticScholar
import asyncio
import aiohttp
import aiofiles


import logging


async def query(client, query, limit, session):
    logging.info(f'Querying {client.__class__.__name__}')
    resp = await client.search(session, query, limit)
    return resp

async def query_redo(redo, session):
    logging.info(f'Redoing {redo}')
    resp = await redo.client.search(session, redo.searchkey, redo.limit)
    return resp

def process_results(results, success=[]):
    redo = [result for result in results if result.__class__.__name__ == 'Redo']
    successes = [result for result in results if not result.__class__.__name__ == 'Redo']
    for s in successes:
        data = [d.data for d in s]
        success.extend(data)
    return redo, success

async def main():
    parser = argparse.ArgumentParser(description='Script to perform medical search.')
    parser.add_argument('-f', '--query_file', type=str, help="The file containing the search query", default="query.txt")
    parser.add_argument("--concurrent", type=int, help="The number of concurrent requests to make", default=2)
    parser.add_argument('-l', '--limit', type=int, default=100, help='Limit the number of search results (default: 100)')
    parser.add_argument('-r', '--retries', type=int, default=3, help='Number of retries to make')
    parser.add_argument('-v', '--verbose', action='count', help='Enable verbose mode', default=0)
    
    args = parser.parse_args()

    if args.verbose == 1:
        logging.getLogger().setLevel(logging.INFO)
    elif args.verbose > 1:
        logging.getLogger().setLevel(logging.DEBUG)
    
    print(f'Limit: {args.limit}')

    search_keywords = []
    async with aiofiles.open(args.query_file, mode='r') as f:
        async for line in f:
            search_keywords.append(line.strip())

    conn = aiohttp.TCPConnector(limit=args.concurrent)
    # set total=None because the POST is really slow and the defeault will cause any request still waiting to be processed after "total" seconds to fail.  Also set read to 10 minutes
    timeout = aiohttp.ClientTimeout(total=None, sock_connect=10, sock_read=600)

    async with aiohttp.ClientSession(connector=conn, timeout=timeout) as session:
        results = await asyncio.gather(*(query(client, searchkeyword, args.limit, session) for client in [SemanticScholar(), Dynamed()] for searchkeyword in search_keywords))
        logging.info("Finalized all. Return is a list of len {} outputs.".format(len(results)))

        redo, success = process_results(results)

        retries = args.retries
        while redo and retries > 0:
            logging.info(f"Retrying {len(redo)} results.")
            results = await asyncio.gather(*(query_redo(r, session) for r in redo))
            redo, success = process_results(results, success)
            retries -= 1

        logging.info(f"Success: {len(success)}, Failures: {len(redo)}")

if __name__ == '__main__':
    logging.basicConfig(stream=sys.stderr, level=logging.WARN)
    asyncio.run(main())