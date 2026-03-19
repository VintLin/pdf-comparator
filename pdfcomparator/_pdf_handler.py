import os
import re
import shutil
import logging
import pdfplumber
import pypdfium2

from pdfcomparator._pdf_text_extractor import PDFTextExtractor

class PDFHandler:
    def __init__(self, path) -> None:
        self.path = path
        self._pages : list = []
        self._text_extractor = PDFTextExtractor()
    
    @staticmethod
    def get_texts(groups, add_return=False):
        texts = []
        for group in groups:
            result = PDFHandler._get_text(group, add_return)
            texts.append(result)
        return texts

    @staticmethod
    def _get_text(chars, add_return=False):
        text = ""
        pre_top = -1
        pre_left = -1
        for char in chars:
            current_top = char['y1']
            current_left = char['x0']
            if add_return and \
                pre_left != -1 and \
                not PDFHandler.is_within_range(current_left, pre_left - 2, pre_left + 2) and\
                pre_top != -1 and \
                not PDFHandler.is_within_range(current_top, pre_top - 2, pre_top + 2) and \
                text[-1] != "\n":
                text += "\n"
            text += char['text']
            pre_top = current_top
            pre_left = current_left
        return PDFHandler._prune_text(text).strip()

    @staticmethod
    def _prune_text(text):
        # Regular expression to find all (cid:x) patterns
        cid_pattern = re.compile(r'\(cid:(\d+)\)')
        pruned_text = re.sub(cid_pattern, "", text)
        return pruned_text
    
    @staticmethod
    def is_within_range(value, lower_bound, upper_bound):
        return lower_bound <= value <= upper_bound
    
    def is_large(self):
        return self.page_height * self.page_width > 1000 * 1000
    
    def get_page_chars(self, page_index):
        return self._pages[page_index]
    
    def load(self):
        with pdfplumber.open(self.path) as pdf:
            # Cache shared page metadata before extracting text groups.
            self.page_count = len(pdf.pages)
            self.page_width = pdf.pages[0].width
            self.page_height = pdf.pages[0].height
            self._pages = [None for _ in range(self.page_count)]
            for index in range(self.page_count):
                self._pages[index] = self._text_extractor.extract_page_char_groups(pdf.pages[index])
        return self
    
    def to_images(self, output_folder):
        logging.debug("Rendering PDF pages to images in %s", output_folder)
        if os.path.exists(output_folder):
            shutil.rmtree(output_folder)
        os.makedirs(output_folder, exist_ok=True)

        image_files = []
        pdf = pypdfium2.PdfDocument(self.path)
        scale = 200 / 72
        try:
            for index in range(len(pdf)):
                page = pdf.get_page(index)
                try:
                    image = page.render(scale=scale).to_pil()
                    image_path = os.path.join(output_folder, f"page_{index + 1}.jpg")
                    image.convert("RGB").save(image_path, "JPEG")
                    image_files.append(image_path)
                    logging.debug("Image created: %s", image_path)
                finally:
                    page.close()
        finally:
            pdf.close()
        return image_files
