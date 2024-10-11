import asyncio
import os
import azure.functions as func
import logging
from app import search
import pymongo
from itertools import islice

app = func.FunctionApp()

def batched(iterable, chunk_size):
    iterator = iter(iterable)
    while chunk := tuple(islice(iterator, chunk_size)):
        yield chunk

async def save_to_db(results):
    CONNECTION_STRING = os.environ.get("COSMOS_CONNECTION_STRING")
    DATATBASE_NAME = os.environ.get("COSMOS_DATABASE_NAME")
    COLLECTION_NAME = os.environ.get("COSMOS_COLLECTION_NAME")
    BATCH_SIZE = os.environ.get("COSMOS_BATCH_SIZE", 1000)

    batch_size = 1000
    try:
        batch_size = int(BATCH_SIZE)
        logging.info(f"Batch size: {batch_size}")
    except ValueError:
        logging.error(f"Invalid batch size: '{BATCH_SIZE}'")

    results_chunks = batched(results, batch_size)
    logging.info(f"Saving {len(results)} results to the database in {len(results_chunks)} chunks")

    client = pymongo.MongoClient(CONNECTION_STRING)
    database = client.get_database(DATATBASE_NAME)
    collection = database.get_collection(COLLECTION_NAME)

    for chunk in results_chunks:
        collection.insert_many(chunk)
        logging.info(f"Wrote {len(chunk)} results to the database")
        await asyncio.sleep(1)

    client.close()

@app.route(route="Search", auth_level=func.AuthLevel.ANONYMOUS)
async def Search(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Python HTTP trigger function processed a request.')

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
            results = await search(keywords, 10, 3)
            await save_to_db(results)        
            return func.HttpResponse(f"Got: '{keywords} with {len(results)} results'. This HTTP triggered function executed successfully.")
        except Exception as e:
            logging.error(f'An error occured: {str(e)}')
            return func.HttpResponse(f"An error occured: {str(e)}", status_code=500)
    else:
        return func.HttpResponse(
             "This HTTP triggered function executed successfully, but recieved no keywords",
             status_code=400
        )
    
@app.route(route="Health", auth_level=func.AuthLevel.ANONYMOUS)
async def Health(req: func.HttpRequest) -> func.HttpResponse:
    return func.HttpResponse("OK", status_code=200)

@app.route(route="Delete", auth_level=func.AuthLevel.ANONYMOUS)
async def Delete(req: func.HttpRequest) -> func.HttpResponse:
    CONNECTION_STRING = os.environ.get("COSMOS_CONNECTION_STRING")
    DATATBASE_NAME = os.environ.get("COSMOS_DATABASE_NAME")
    COLLECTION_NAME = os.environ.get("COSMOS_COLLECTION_NAME")

    client = pymongo.MongoClient(CONNECTION_STRING)
    database = client.get_database(DATATBASE_NAME)
    collection = database.get_collection(COLLECTION_NAME)
    collection.delete_many({})
    client.close()

    return func.HttpResponse("Deleted all documents", status_code=200)