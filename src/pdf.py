import requests
import PyPDF2
from io import BytesIO
print('ok')
# Specify the URL of the PDF
pdf_url = 'https://bitvm.org/bitvm.pdf'

# Download the PDF
response = requests.get(pdf_url)
print('response', response)

# Ensure the request was successful
if response.status_code == 200:
    # Convert the content to a file-like object
    pdf_file = BytesIO(response.content)
    print(pdf_file)
    
    # Read the PDF
    pdf_reader = PyPDF2.PdfReader(pdf_file)
    
    # Extract text from each page
    for page_number in range(len(pdf_reader.pages)):
        pdf_page = pdf_reader.pages[page_number]
        print(pdf_page.extract_text())
