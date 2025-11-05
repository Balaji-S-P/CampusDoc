import requests
from bs4 import BeautifulSoup
from PyPDF2 import PdfReader
from io import BytesIO

base_url="https://skcet.ac.in/department/b-tech-information-technology/?tab=curriculum"
visited_urls=set()
to_visit=[base_url]
def extract_pdfs_from_url(url, output_file="pdf_texts.txt"):
    visited_urls.add(url)
    response = requests.get(url)
    soup = BeautifulSoup(response.text, "html.parser")

    pdf_links = [a["href"] for a in soup.find_all("a", href=True) if a["href"].endswith(".pdf") and not("research-policy" in a["href"] or "research-paper" in a["href"] or "Tender" in a["href"]) and not(a["href"] in visited_urls)]

    with open(output_file, "w", encoding="utf-8") as f:
        for link in pdf_links:
            # Handle relative URLs
            pdf_url = link if link.startswith("http") else url + "/" + link
            try:
                pdf_response = requests.get(pdf_url)
                pdf_file = BytesIO(pdf_response.content)

                reader = PdfReader(pdf_file)
                text = ""
                for page in reader.pages:
                    text += page.extract_text() or ""

                f.write(text)

                print(f"✅ Extracted: {pdf_url}")
            except Exception as e:
                print(f"❌ Failed to extract {pdf_url}: {e}")
while to_visit:
    current_url=to_visit.pop()
    if current_url in visited_urls or "research-policy" in current_url or "research-paper" in current_url or "Tender" in current_url:
        continue
    visited_urls.add(current_url)

    

    try:
        extract_pdfs_from_url(current_url)
    except Exception as e:
        print(f"Error extracting PDFs from {current_url}: {e}")
        continue
    response=requests.get(current_url)
    response.raise_for_status()
    soup=BeautifulSoup(response.text,'html.parser')


    for link in soup.find_all('a',href=True):
        next_url=link['href']
        if "skcet.ac.in" in next_url:
            if next_url.startswith('http'):
                to_visit.append(next_url)
            else:
                to_visit.append(base_url+next_url)
    print(f"Visited {current_url}")

