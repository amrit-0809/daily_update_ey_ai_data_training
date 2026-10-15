import fitz
# Q1
doc = fitz.open(r"C:\Users\Trainer\Downloads\EY_Digital_PDF_Practice.pdf")
# question 2
print("Pages:", len(doc))
# question 3
page = doc.load_page(0)
text=page.get_text()
print(text)
# question 4
for page in doc:
    print(page.get_text())
# Question 5
print("maintenance" in "".join(p.get_text() for p in doc).lower())
# Question 6
print(sum(p.get_text().count("V303") for p in doc))
#Question 7
page2 = doc.load_page(1)
text2=page2.get_text()
print(text2)
# question 8

with open("digital_pdf_text.txt","w",encoding="utf-8") as f:
    f.write(text)
    f.write(text2)



