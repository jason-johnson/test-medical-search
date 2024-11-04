import logging
import os
import re
import base64
import uuid
import requests
from io import BytesIO
from PIL import Image
import pymupdf
from openai import AzureOpenAI
from azure.core.credentials import AzureKeyCredential
from azure.ai.documentintelligence import DocumentIntelligenceClient
from azure.ai.documentintelligence.models import AnalyzeDocumentRequest, ContentFormat
from azure.identity import DefaultAzureCredential
from azure.storage.blob import BlobServiceClient, BlobClient, ContainerClient


class PDFProcessor:
    def __init__(self):
        # Azure Form Recognizer credentials
        self.di_client = DocumentIntelligenceClient(
            endpoint=os.environ.get("AZURE_FORM_RECOGNIZER_ENDPOINT"),
            credential=AzureKeyCredential(
                os.environ.get("AZURE_FORM_RECOGNIZER_KEY"))
        )

        # Azure OpenAI
        self.aoai_client = AzureOpenAI(
            api_key=os.environ.get("OPENAI_API_KEY"),
            api_version=os.environ.get(
                "OPENAI_API_VERSION", "2024-02-15-preview"),
            azure_endpoint=os.environ.get("OPENAI_AZURE_ENDPOINT")
        )
        self.deployment_name = os.environ.get(
            "OPENAI_DEPLOYMENT_NAME", 'GPT-4o-20240513-global')
        
        account_url = os.environ.get("AZURE_STORAGE_ACCOUNT_URL")
        default_credential = DefaultAzureCredential()
        
        self.blob_service_client = BlobServiceClient(account_url, credential=default_credential)

    @staticmethod
    def download_pdf_from_url(url):
        """
        Downloads the PDF from the provided URL and returns the content as a BytesIO object.
        """
        try:
            response = requests.get(url)
            response.raise_for_status()
            return BytesIO(response.content)
        except requests.RequestException as e:
            logging.error(f"Error downloading PDF from {url}: {e}")
            return None

    @staticmethod
    def crop_image_from_file(pdf_bytes, page_number, bounding_box):
        """
        Crops a region from a given page in a PDF and returns it as a base64-encoded string.
        """
        try:
            doc = pymupdf.open(stream=pdf_bytes, filetype="pdf")
            page = doc.load_page(page_number)

            # Convert bounding box to points
            bbx = [x * 72 for x in bounding_box]
            rect = pymupdf.Rect(bbx)
            pix = page.get_pixmap(
                matrix=pymupdf.Matrix(300/72, 300/72), clip=rect)

            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

            # Convert the image to a base64-encoded string
            buffered = BytesIO()
            img.save(buffered, format="PNG")
            img_base64 = base64.b64encode(buffered.getvalue()).decode('utf-8')

            doc.close()
            return img_base64
        except Exception as e:
            logging.error(f"Error cropping image from PDF: {e}")
            return None

    def extract_images_from_pdf(self, pdf_url, result):
        pdf_bytes = self.download_pdf_from_url(pdf_url)
        if not pdf_bytes:
            return []

        base64_images = []

        if result is None:
            logging.info(f"Result is None for PDF {pdf_url}.")
            return []

        if not hasattr(result, 'figures') or not result.figures:
            logging.info(f"No figures found in result for PDF {pdf_url}.")
            return []

        for figure in result.figures:
            try:
                region = figure["boundingRegions"][0]["polygon"]
                bounding_box = (
                    region[0],  # x0 (left)
                    region[1],  # y0 (top)
                    region[4],  # x1 (right)
                    region[5]   # y1 (bottom)
                )
                page = figure["boundingRegions"][0]["pageNumber"] - 1

                cropped_image = self.crop_image_from_file(
                    pdf_bytes, page, bounding_box)
                if cropped_image:
                    base64_images.append(cropped_image)
            except Exception as e:
                logging.error(
                    f"Error extracting image from PDF {pdf_url}: {e}")
                continue

        return base64_images

    def extract_text_from_pdf(self, pdf_url):
        try:
            poller = self.di_client.begin_analyze_document(
                "prebuilt-layout",
                AnalyzeDocumentRequest(url_source=pdf_url),
                output_content_format=ContentFormat.MARKDOWN
            )

            result = poller.result()

            extracted_text = ""
            for page in result.pages:
                for line in page.lines:
                    extracted_text += line.content + " "

            return extracted_text, result
        except Exception as e:
            logging.error(f"Error extracting text from PDF {pdf_url}: {e}")
            return "", None

    def extract_tables(self, result):
        tables_markdown = ""

        if result is None:
            logging.info(f"Result is None for PDF.")
            return ""

        if not hasattr(result, 'tables') or not result.tables:
            logging.info(f"No tables found in result for PDF.")
            return ""

        for table_json in result.tables:
            try:
                row_count = table_json['rowCount']
                column_count = table_json['columnCount']

                table = [['' for _ in range(column_count)]
                         for _ in range(row_count)]

                for cell in table_json['cells']:
                    row = cell['rowIndex']
                    col = cell['columnIndex']
                    content = cell.get('content', '')

                    col_span = cell.get('columnSpan', 1)
                    row_span = cell.get('rowSpan', 1)

                    table[row][col] = content

                    for i in range(row_span):
                        for j in range(col_span):
                            if i == 0 and j == 0:
                                continue
                            table[row + i][col + j] = content

                markdown_table = []

                for i, row in enumerate(table):
                    markdown_row = "| " + " | ".join(row) + " |"
                    markdown_table.append(markdown_row)

                    if i == 0:
                        separator = "| " + \
                            " | ".join(['---'] * column_count) + " |"
                        markdown_table.append(separator)

                tables_markdown += "\n\n".join(markdown_table) + "\n\n"
            except Exception as e:
                logging.error(f"Error processing table: {e}")
                continue

        if not tables_markdown:
            return ""

        prompt = f"""
        You have been given multiple tables from a scientific study that appear to be split or not properly formatted.
        Your task is to ensure that each table is not split across different sections and is formatted correctly.
        Use markdown syntax to clearly separate each table, ensuring that each table's structure is intact, and there are distinct separations between different tables.
        After restructuring, ensure that the headings, rows, and columns align correctly, and ensure proper labeling where necessary.
        Return the results in markdown format, including proper titles for each table.

        {tables_markdown}
        """

        try:
            response = self.aoai_client.chat.completions.create(
                model=self.deployment_name,
                messages=[
                    {"role": "system", "content": "You are an AI assistant."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0,
                max_tokens=4096
            )

            return response.choices[0].message.content
        except Exception as e:
            logging.error(f"Error processing tables with OpenAI: {e}")
            return ""

    def extract_sections(self, text, sections):

        extracted_strings = ["", "", ""]  # List to hold the three sections

        system_message = """
        ## Extract sections from the research paper markdown.
        """

        prompt = f"""
        Extract the following sections: {', '.join(sections)} from the research paper text:
        {text}
        """

        try:
            response = self.aoai_client.chat.completions.create(
                model=self.deployment_name,
                messages=[
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": prompt}
                ],
                temperature=0,
                max_tokens=4096
            )

            markdown = response.choices[0].message.content

            for index, section in enumerate(sections):
                # Use regex to find the section content, making it case-insensitive
                # pattern = rf"#{1,2} {section}\n\n(.*?)(?=\n#{1,2} |\Z)"
                pattern = rf"{section}\n\n(.*?)(?=\n|\Z)"
                # Added re.IGNORECASE
                match = re.search(pattern, markdown, re.IGNORECASE | re.DOTALL)
                if match:
                    # Store content in corresponding index
                    extracted_strings[index] = match.group(1).strip()

            return extracted_strings[0], extracted_strings[1], extracted_strings[2], markdown

        except Exception as e:
            logging.error(f"Error extracting sections with OpenAI: {e}")
            return tuple(extracted_strings + [""])
        
    def save_images_to_blob(self, images):
        container_name = os.environ.get("AZURE_STORAGE_CONTAINER_NAME", "journal-images")
        container_client = self.blob_service_client.get_container_client(container_name)

        results = []
        
        for _, image in enumerate(images):
            try:
                image_bytes = base64.b64decode(image)
                blob_name = f'{str(uuid.uuid4())}.png'
                blob_client = container_client.get_blob_client(blob_name)
                blob_client.upload_blob(image_bytes, overwrite=True)
                results.append(blob_client.url)
            except Exception as e:
                logging.error(f"Error saving image to blob: {e}")
                continue

        return results

    def process_pdf(self, url, sections):
        images = []
        tables = ""

        if not url:
            return {
                "markdown_sections": "",
                "introduction": "",
                "results": "",
                "conclusion": "",
                "images": "",
                "tables": "",
                "ai_processing": "unsupported (no URL)"
            }
        else:
            try:
                response = requests.head(url, allow_redirects=True)
                content_type = response.headers.get('Content-Type')

                if content_type is None or "pdf" not in content_type:
                    logging.warning(f"\nThe URL is not a PDF file: {url}")
                    return {
                        "markdown_sections": "",
                        "introduction": "",
                        "results": "",
                        "conclusion": "",
                        "images": "",
                        "tables": "",
                        "ai_processing": "unsupported (not a PDF)"
                    }

                logging.info(f"\nProcessing URL: {url}")
                text, poller_result = self.extract_text_from_pdf(url)
                if text and poller_result:
                    introduction, results, conclusion, markdown_sections = self.extract_sections(
                        text, sections)
                    images = self.extract_images_from_pdf(url, poller_result)
                    tables = self.extract_tables(poller_result)

                    image_urls = self.save_images_to_blob(images)

                    return {
                        "markdown_sections": markdown_sections,
                        "introduction": introduction,
                        "results": results,
                        "conclusion": conclusion,
                        "images": image_urls,
                        "tables": tables,
                        "ai_processing": "successful"
                    }
                else:
                    logging.warning(f"\nNo text extracted from the PDF: {url}")
                    return {
                        "markdown_sections": "",
                        "introduction": "",
                        "results": "",
                        "conclusion": "",
                        "images": "",
                        "tables": "",
                        "ai_processing": "failed (no text extracted)"
                    }

            except requests.RequestException as e:
                logging.error(f"\nError checking the URL {url}: {e}")
                return {
                    "markdown_sections": "",
                    "introduction": "",
                    "results": "",
                    "conclusion": "",
                    "images": "",
                    "tables": "",
                    "ai_processing": f"failed {e}"
                }
