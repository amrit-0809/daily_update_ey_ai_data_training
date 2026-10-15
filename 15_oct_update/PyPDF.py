from pypdf import PdfReader
# Question1
reader = PdfReader(r"C:\Users\Trainer\Downloads\EY_Digital_PDF_Practice.pdf")
# Question 2
print("Pages:", len(reader.pages))
# Question 3
print(reader.pages[0].extract_text())
#Question 4
print(reader.pages[1].extract_text())
# Question 5
text= reader.pages[0].extract_text()+reader.pages[1].extract_text()
print(text)
# Question 6
text=" ".join(page.extract_text() or "" for page in reader.pages)
print("NorthStar Maintenance".lower() in text.lower())

# Question 7
text=" ".join(page.extract_text() or "" for page in reader.pages)
print(text.lower().count("vendor"))
# Question 8
with open("pypdf_output.txt","w",encoding="utf-8") as f:
    f.write(" ".join(page.extract_text() or "" for page in reader.pages))
