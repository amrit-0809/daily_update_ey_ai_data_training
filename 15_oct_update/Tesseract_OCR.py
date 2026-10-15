import fitz
import pytesseract
from PIL import Image
# Question1
doc = fitz.open(r"C:\Users\Trainer\Downloads\EY_Scanned_PDF_OCR_Practice.pdf")
# Question 2
page = doc[0]
pix = page.get_pixmap()
pix.save("scanned_page.png")
# Question 3
image = Image.open("scanned_page.png")
text = pytesseract.image_to_string(image)
# Question 4
print(text)
# Question 5
print("Forklift FL-17" in text)
# Question 6
print("injuries" in text.lower())
# Question 7
for line in text.splitlines():
    if "inspection" in line.lower():
        print(line)
# question 8
with open("ocr_result.txt","w") as f:
    f.write(text)
# question 9
print(text.lower().count("inspection"))
# question 10
for line in text.splitlines():
    if "Loading Bay" in line:
        print(line)