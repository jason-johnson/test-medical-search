import asyncio
import datetime
import os
import azure.functions as func
import logging
from app import search
import pymongo
from itertools import islice

app = func.FunctionApp()


def get_db_connection():
    CONNECTION_STRING = os.environ.get("COSMOS_CONNECTION_STRING")
    DATATBASE_NAME = os.environ.get("COSMOS_DATABASE_NAME")
    COLLECTION_NAME = os.environ.get("COSMOS_COLLECTION_NAME")

    client = pymongo.MongoClient(CONNECTION_STRING)
    database = client.get_database(DATATBASE_NAME)
    collection = database.get_collection(COLLECTION_NAME)
    return client, collection


def batched(iterable, chunk_size):
    iterator = iter(iterable)
    while chunk := tuple(islice(iterator, chunk_size)):
        yield chunk


async def save_to_db(results):
    BATCH_SIZE = os.environ.get("COSMOS_BATCH_SIZE", 1000)

    batch_size = 1000
    try:
        batch_size = int(BATCH_SIZE)
        logging.info(f"Batch size: {batch_size}")
    except ValueError:
        logging.error(f"Invalid batch size: '{BATCH_SIZE}'")

    results_chunks = batched(results, batch_size)

    client, collection = get_db_connection()

    logging.debug(f"Database connection established.")

    for chunk in results_chunks:
        collection.insert_many(chunk)
        logging.info(f"Wrote {len(chunk)} results to the database")
        await asyncio.sleep(1)

    client.close()


@app.route(route="Search", auth_level=func.AuthLevel.ANONYMOUS)
async def Search(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Python HTTP trigger function processed a request.')
    concurrent_pm = os.environ.get("CONCURRENT_PUBMED", 10)
    concurrent_ss = os.environ.get("CONCURRENT_SEMANTIC_SCHOLAR", 50)
    concurrent_dm = os.environ.get("CONCURRENT_DYNAMED", 10)
    retries = os.environ.get("SOURCE_RETRIES", 3)

    request_id = f'SEARCH ({datetime.now().isoformat()})'

    keywords = req.params.get('keywords')
    if not keywords:
        try:
            req_body = req.get_json()
        except ValueError:
            pass
        else:
            keywords = req_body.get('keywords')

    if keywords:
        try:
            keywords = keywords.split(',')
            request_id = f'{request_id} - {keywords}'
            logging.info(f'{request_id} - Starting')
            results = await search(keywords, concurrent_pm, concurrent_ss, concurrent_dm, retries)
            await save_to_db(results)
            return func.HttpResponse(f"Got: '{keywords} with {len(results)} results'. This HTTP triggered function executed successfully.")
        except Exception as e:
            logging.error(f'An error occured: {str(e)}')
            return func.HttpResponse(f"An error occured: {str(e)}", status_code=500)
        finally:
            logging.info(f'{request_id} - Completed')
    else:
        return func.HttpResponse(
            "This HTTP triggered function executed successfully, but recieved no keywords",
            status_code=400
        )


@app.route(route="Health", auth_level=func.AuthLevel.ANONYMOUS)
async def Health(req: func.HttpRequest) -> func.HttpResponse:
    return func.HttpResponse("OK", status_code=200)


@app.route(route="ClearDatabase", auth_level=func.AuthLevel.ANONYMOUS)
async def ClearDatabase(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Clear Database request recieved.')

    try:
        client, collection = get_db_connection()
        collection.delete_many({})
        client.close()
    except Exception as e:
        logging.error(f'An error occured: {str(e)}')
        return func.HttpResponse(f"An error occured: {str(e)}", status_code=500)

    logging.info('Clear Database request completed.')
    return func.HttpResponse("Deleted all documents", status_code=200)
