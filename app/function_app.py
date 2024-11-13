import asyncio
from datetime import datetime
import os
import uuid
from ai.processor import PDFProcessor
import aiohttp
import azure.functions as func
import azure.durable_functions as df
import logging
import pymongo
from itertools import islice

myApp = df.DFApp(http_auth_level=func.AuthLevel.ANONYMOUS)


@myApp.route(route="orchestrators/search")
@myApp.durable_client_input(client_name="client")
async def http_start(req: func.HttpRequest, client: df.DurableOrchestrationClient):
    request_id = f"SEARCH ({datetime.now().isoformat()})"
    retries = os.environ.get("SOURCE_RETRIES", 3)
    semantic_scholar_key = os.environ.get("SS_API_KEY")
    pub_med_key = os.environ.get("PUBMED_API_KEY")

    keywords = req.params.get("keywords")
    if not keywords:
        try:
            req_body = req.get_json()
        except ValueError:
            pass
        else:
            keywords = req_body.get("keywords")

    if keywords:
        try:
            keywords = keywords.split(",")
            request_id = f"{request_id} - {keywords}"
            logging.info(f"{request_id} - Starting, retries: {retries}")

            parameters = {
                "keywords": keywords,
                "retries": int(retries),
                "semantic_scholar_key": semantic_scholar_key,
                "pub_med_key": pub_med_key,
            }

            instance_id = await client.start_new("main_orchestrator", None, parameters)
            response = client.create_check_status_response(req, instance_id)
            return response
        except Exception as e:
            logging.error(f"An error occured: {str(e)}")
            return func.HttpResponse(f"An error occured: {str(e)}", status_code=500)
    else:
        return func.HttpResponse(
            "This HTTP triggered function executed successfully, but recieved no keywords",
            status_code=400,
        )


@myApp.orchestration_trigger(context_name="context")
def main_orchestrator(context: df.DurableOrchestrationContext):
    input = context.get_input()

    tasks = []
    retry_options = df.RetryOptions(5000, input["retries"])
    for keyword in input["keywords"]:
        i = input.copy()
        i["keyword"] = keyword
        tasks.append(
            context.call_sub_orchestrator_with_retry(
                "keyword_orchestrator", retry_options, i
            )
        )

    results = yield context.task_all(tasks)

    return results


@myApp.orchestration_trigger(context_name="context")
def keyword_orchestrator(context: df.DurableOrchestrationContext):
    input = context.get_input()
    keyword = input["keyword"]

    retry_options = df.RetryOptions(5000, input["retries"])
    search_tasks = []
    for source in ["pubmed", "semantic_scholar"]:
        search_tasks.append(
            context.call_activity_with_retry(
                f"search_{source}", retry_options, keyword
            )
        )

    results = yield context.task_all(search_tasks)

    return results


@myApp.activity_trigger(input_name="keyword")
def search_semantic_scholar(keyword: str):
    return f"semantic_scholar {keyword}"


@myApp.activity_trigger(input_name="keyword")
def search_pubmed(keyword: str):
    return f"pubmed {keyword}"


def get_db_connection():
    CONNECTION_STRING = os.environ.get("COSMOS_CONNECTION_STRING")
    DATATBASE_NAME = os.environ.get("COSMOS_DATABASE_NAME")
    COLLECTION_NAME = os.environ.get("COSMOS_COLLECTION_NAME")

    client = pymongo.MongoClient(CONNECTION_STRING)
    database = client.get_database(DATATBASE_NAME)
    collection = database.get_collection(COLLECTION_NAME)
    return client, collection


def delete_keyword(keyword):
    logging.info(f"Deleting keyword: {keyword} from DB")
    client, collection = get_db_connection()
    docs = collection.delete_many({"searchkey": keyword})
    logging.info(f"Deleted {docs.deleted_count} documents")
    client.close()


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


async def process_document(session, processor, doc):
    url = doc["pdf_url"]

    processed_data = await processor.process_pdf(
        session, url, ["introduction", "results", "conclusion"]
    )
    new_values = {
        "markdown_sections": processed_data["markdown_sections"],
        "introduction": processed_data["introduction"],
        "results": processed_data["results"],
        "conclusion": processed_data["conclusion"],
        "figures": processed_data["images"],
        "tables": processed_data["tables"],
        "ai_processed": processed_data["ai_processing"],
    }

    return doc["_id"], new_values


""" async def SearchOld(req: func.HttpRequest) -> func.HttpResponse:
    logging.info("Python HTTP trigger function processed a request.")
    concurrent_pm = os.environ.get("CONCURRENT_PUBMED", 10)
    concurrent_ss = os.environ.get("CONCURRENT_SEMANTIC_SCHOLAR", 50)
    concurrent_dm = os.environ.get("CONCURRENT_DYNAMED", 10)
    retries = os.environ.get("SOURCE_RETRIES", 3)

    request_id = f"SEARCH ({datetime.now().isoformat()})"

    keywords = req.params.get("keywords")
    if not keywords:
        try:
            req_body = req.get_json()
        except ValueError:
            pass
        else:
            keywords = req_body.get("keywords")

    if keywords:
        try:
            keywords = keywords.split(",")
            request_id = f"{request_id} - {keywords}"
            logging.info(f"{request_id} - Starting")

            results = await search(
                keywords, concurrent_pm, concurrent_ss, concurrent_dm, retries
            )
            await save_to_db(results)
            return func.HttpResponse(
                f"Got: '{keywords} with {len(results)} results'. This HTTP triggered function executed successfully."
            )
        except Exception as e:
            logging.error(f"An error occured: {str(e)}")
            return func.HttpResponse(f"An error occured: {str(e)}", status_code=500)
        finally:
            logging.info(f"{request_id} - Completed")
    else:
        return func.HttpResponse(
            "This HTTP triggered function executed successfully, but recieved no keywords",
            status_code=400,
        ) """


async def Health(req: func.HttpRequest) -> func.HttpResponse:
    return func.HttpResponse("OK", status_code=200)


async def Delete(req: func.HttpRequest) -> func.HttpResponse:
    logging.info("Delete request recieved.")

    keywords = req.params.get("keywords")
    if not keywords:
        try:
            req_body = req.get_json()
        except ValueError:
            pass
        else:
            keywords = req_body.get("keywords")

    if keywords:
        try:
            keywords = keywords.split(",")
            for keyword in keywords:
                delete_keyword(keyword)
            return func.HttpResponse(
                f"Deleted: '{keywords}'. This HTTP triggered function executed successfully."
            )
        except Exception as e:
            logging.error(f"An error occured: {str(e)}")
            return func.HttpResponse(f"An error occured: {str(e)}", status_code=500)
    else:
        return func.HttpResponse(
            "This HTTP triggered function executed successfully, but recieved no keywords",
            status_code=400,
        )


async def ClearDatabase(req: func.HttpRequest) -> func.HttpResponse:
    logging.info("Clear Database request recieved.")

    try:
        client, collection = get_db_connection()
        collection.delete_many({})
        client.close()
    except Exception as e:
        logging.error(f"An error occured: {str(e)}")
        return func.HttpResponse(f"An error occured: {str(e)}", status_code=500)

    logging.info("Clear Database request completed.")
    return func.HttpResponse("Deleted all documents", status_code=200)


async def UpdateAI(updateAI: func.TimerRequest) -> None:
    id = uuid.uuid4()

    logging.basicConfig(
        format="[%(name)s: %(levelname)s - %(funcName)20s()] %(message)s"
    )
    logger = logging.getLogger(f"{id}")

    if updateAI.past_due:
        logger.info(f"DB AI Update timer is past due! ({id})")

    logger.info("DB AI Update timer is starting")
    batch_size = os.environ.get("COSMOS_AI_BATCH_SIZE", 15)
    batch_size = int(batch_size)
    logger.info(f"Only processing first {batch_size} documents")

    processor = PDFProcessor()
    client, collection = get_db_connection()

    try:
        cursor = collection.find({"ai_processed": False}, limit=batch_size)
        docs = cursor.to_list()

        if len(docs) == 0:
            logger.info(f"No documents to process")
            return

        logger.info(f"Found {len(docs)} documents to process")

        logger.info("Locking documents for processing")
        for doc in docs:
            doc_id = doc["_id"]
            result = collection.update_one(
                {"_id": doc_id}, {"$set": {"ai_processed": f"processing ({id})"}}
            )
            if result.modified_count == 1:
                logger.info(f"Locked document: {doc_id}")
            else:
                logger.warning(f"Failed to lock document for some reason: {doc_id}")
        logger.info("Document locking complete")

        results = []

        timeout = aiohttp.ClientTimeout(total=None, sock_connect=10, sock_read=600)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            results = await asyncio.gather(
                *(process_document(session, processor, doc) for doc in docs)
            )

        for doc_id, new_values in results:
            result = collection.update_one({"_id": doc_id}, {"$set": new_values})
            if result.modified_count == 1:
                logger.info(f"Updated document: {doc_id}")
            else:
                logger.warning(f"Failed to update document for some reason: {doc_id}")

    except Exception as e:
        logger.error(f"An error occured: {str(e)}")
    finally:
        client.close()
