import requests
import PyPDF2
from io import BytesIO

# Specify the URL of the PDF
pdf_url = 'https://example.com/yourfile.pdf'

# Download the PDF
response = requests.get(pdf_url)

# Ensure the request was successful
if response.status_code == 200:
    # Convert the content to a file-like object
    pdf_file = BytesIO(response.content)
    
    # Read the PDF
    pdf_reader = PyPDF2.PdfFileReader(pdf_file)
    
    # Extract text from each page
    for page_number in range(pdf_reader.numPages):
        pdf_page = pdf_reader.getPage(page_number)
        print(pdf_page.extractText())
