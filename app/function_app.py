import azure.functions as func
import logging
from app import search

app = func.FunctionApp()

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
        keywords = keywords.split(',')
        results = await search(keywords, 10, 3)
        return func.HttpResponse(f"Got: '{keywords} with {len(results)} results'. This HTTP triggered function executed successfully.")
    else:
        return func.HttpResponse(
             "This HTTP triggered function executed successfully, but recieved no keywords",
             status_code=400
        )