import argparse
from functools import reduce
import json
import sys
from ai.processor import PDFProcessor
from searchlib.dynamed import Dynamed
from searchlib.pubmed import PubMed
from searchlib.semantic_scholar import SemanticScholar
import asyncio
import aiohttp
import aiofiles


import logging


async def query(client, query):
    logging.info(f'Querying {client.__class__.__name__} - {query}')
    resp = await client.search(query)
    return resp

async def query_redo(redo):
    logging.info(f'Redoing {redo}')
    resp = await redo.client.search(redo.searchkey, redo.token)
    return resp

def process_results(results):
    redo = [result for result in results if result.__class__.__name__ == 'Redo']
    successes = [result for result in results if not result.__class__.__name__ in ['Redo', 'Partial']]
    partials = [result for result in results if result.__class__.__name__ == 'Partial']
    
    for partial in partials:
        successes.append(partial.successes)
        redo.append(partial.redo)

    success = []

    for s in successes:
        data = [d.data for d in s]
        success.extend(data)
    return redo, success, len(successes) > 0

def result_len(results):
    result = 0
    for r in results:
        if isinstance(r, list):
            result += len(r)
        else:
            result += 1

    return result

async def search(search_keywords, concurrent_pm, concurrent_ss, concurrent_dm, retries):
    pm_conn = aiohttp.TCPConnector(limit=concurrent_pm)
    ss_conn = aiohttp.TCPConnector(limit=concurrent_ss)
#    dm_conn = aiohttp.TCPConnector(limit=concurrent_dm)
    # set total=None because the POST is really slow and the defeault will cause any request still waiting to be processed after "total" seconds to fail.  Also set read to 10 minutes
    timeout = aiohttp.ClientTimeout(total=None, sock_connect=10, sock_read=600)

    async with (
        aiohttp.ClientSession(connector=pm_conn, timeout=timeout) as pm_session,
        aiohttp.ClientSession(connector=ss_conn, timeout=timeout) as ss_session,
#        aiohttp.ClientSession(connector=dm_conn, timeout=timeout) as dm_session,
    ):
        results = await asyncio.gather(*(query(client, searchkeyword) for client in [SemanticScholar(ss_session), PubMed(pm_session)] for searchkeyword in search_keywords))
        logging.info(f"Finalized initial run. Return is a list of {len(results)} outputs (total elements: {result_len(results)}.")

        redo, success, _ = process_results(results)
        logging.info(f"Initial run - Success: {len(success)}, Redos: {len(redo)}")

        while redo and retries > 0:
            logging.info(f"Retrying {len(redo)} results.")
            results = await asyncio.gather(*(query_redo(r) for r in redo))
            redo, new_success, any_succeded = process_results(results)
            success.extend(new_success)
            if not any_succeded:
                retries -= 1

        logging.info(f"Success: {len(success)}, Failures: {len(redo)}")

        return success

async def process_ai(processor, doc):
    url = doc["pdf_url"]
    processed_data = processor.process_pdf(url, ["introduction", "results", "conclusion"])
    new_values = { 
        "markdown_sections": processed_data["markdown_sections"],
        "introduction": processed_data["introduction"],
        "results": processed_data["results"],
        "conclusion": processed_data["conclusion"],
        "figures": processed_data["images"],
        "tables": processed_data["tables"],
        "status": {"analysis": "", "ai_processing": processed_data["ai_processing"]}
    }
    result = {**doc, **new_values}
    return result

async def main():
    parser = argparse.ArgumentParser(description='Script to perform medical search.')
    parser.add_argument('-f', '--query_file', type=str, help="The file containing the search query", default="query.txt")
    parser.add_argument('-o', '--output_file', type=str, help="The file to write the output to", default=None)
    parser.add_argument('--with-pdf-only', action='store_true', help="Only return results with PDFs", default=False)
    parser.add_argument("--concurrent-pm", type=int, help="The number of concurrent pubmed requests to make", default=10)
    parser.add_argument('--concurrent-ss', type=int, help="The number of concurrent Semantic Scholar requests to make", default=50)
    parser.add_argument('--concurrent-dm', type=int, help="The number of concurrent Dynamed requests to make", default=10)
    parser.add_argument('--process-ai', action='store_true', help="Process the AI on the results", default=True)
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

    results = await search(search_keywords, args.concurrent_pm, args.concurrent_ss, args.concurrent_dm, args.retries)

    processor = None

    if args.process_ai:
        processor = PDFProcessor()

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
            if args.process_ai:
                s = await process_ai(processor, s)
            print(json.dumps(s))

if __name__ == '__main__':
    logging.basicConfig(stream=sys.stderr, level=logging.WARN)
    asyncio.run(main())