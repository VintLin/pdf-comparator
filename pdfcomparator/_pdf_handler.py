import os
import re
import shutil
import logging
import threading
import pdfplumber

from pdfplumber.page import Page as PlumberPage
from pdf2image import convert_from_path
from threading import Thread
from pdfcomparator._utils_for_char import CharUtils

class PDFHandler:
    def __init__(self, path) -> None:
        self.path = path
        self._pages : list = []
        self._lock = threading.Lock() 
    
    @staticmethod
    def get_str(groups, add_return=False):
        str = ""
        for group in groups:
            # words_group = pdf_utils.extract_words(group)
            result = PDFHandler._get_text(group, add_return).replace(" ", "")
            if result.strip():
                str += f"{result}\n"
        return str
    
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
            # set common stats
            self.page_count = len(pdf.pages)
            self.page_width = pdf.pages[0].width
            self.page_height = pdf.pages[0].height
            
            threads = []
            for index in range(self.page_count):
                thread = Thread(target=self.load_page, args=(pdf.pages[index],))
                threads.append(thread)
                thread.start()
            
            for thread in threads:
                thread.join()
        return self
        
    def load_page(self, page: PlumberPage):
        with self._lock:  
            chars = page.chars
            lines = CharUtils.divide_groups(chars)
            self._pages.append(lines)
    
    def to_images(self, output_folder):
        print(output_folder)
        if os.path.exists(output_folder):
            shutil.rmtree(output_folder)
        os.makedirs(output_folder, exist_ok=True)
        # convert to image
        image_files = []
        images = convert_from_path(self.path, fmt='jpeg', thread_count=8, dpi=200)
        for index, image in enumerate(images):
            image_path = os.path.join(output_folder, f"page_{index + 1}.jpg")
            image.save(image_path, "JPEG")
            image_files.append(image_path)
            logging.debug("Image Create: " + image_path)
        del images
        return image_files