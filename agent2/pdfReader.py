import pdfplumber

class PdfReader:
    def __init__(self, pdfPath):
        self.pdfPath = pdfPath
        self.pageTexts = []
        self.totalPages = 0

    def load(self):
        with pdfplumber.open(self.pdfPath) as pdf:
            self.totalPages = len(pdf.pages)
            for page in pdf.pages:
                try:
                    text = page.extract_text() 
                except:
                    text = ""
                self.pageTexts.append(text)
        return self.totalPages
