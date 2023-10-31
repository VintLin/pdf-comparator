import os
import shutil
import logging
import pdfplumber
import pdfplumber.utils as pdf_utils
from pdf2image import convert_from_path
from sklearn.cluster import DBSCAN

from pdfcomparator._compare_image import ImageHandler
from pdfcomparator._utils import Utils

class PDFFile:
    def __init__(self, path) -> None:
        self.path = path
        with pdfplumber.open(path) as pdf:
            self.page_count = len(pdf.pages)
            self.page_width = pdf.pages[0].width
            self.page_height = pdf.pages[0].height
            pdf.close()
    
    @staticmethod
    def get_page_sentence(chars):
        content = ""
        for char in chars:
            content += char['text']
        return content
    
    @staticmethod
    def is_char_equal(a_char, b_char):
        try:
            text_same = a_char['text'] == b_char['text'] and not a_char['text'].isspace() and not b_char['text'].isspace()
            size_same = PDFFile._categorize_float(a_char['size']) == PDFFile._categorize_float(b_char['size'])
            color_same = a_char['non_stroking_color'] == b_char['non_stroking_color'] and a_char['stroking_color'] == a_char['stroking_color']
            return [text_same, size_same, color_same]
        except:
            return [False, False, False]
    
    @staticmethod
    def _categorize_float(number):
        integer_part = int(number)
        decimal_part = number - integer_part
        if decimal_part > 0.75:
            category = 1
        elif decimal_part >= 0.25:
            category = 0.5
        else:
            category = 0
        return integer_part + category

    def get_page_text(self, page_index):
        chars_groups = self._get_chars_groups(page_index)
        content = ""
        for chars in chars_groups:
            content += self.get_page_sentence(chars)
        return content
    
    @staticmethod
    def extract_words(words_group):
        extract_words = []
        for words in words_group:
            extract_words.append(pdf_utils.extract_words(words))
        return extract_words
    
    def to_images(self, output_folder, cache=False):
        print(output_folder)
        files = []
        
        if cache:
            is_complete = True
            for index in range(self.page_count):
                image_path = os.path.join(output_folder, f"page_{index + 1}.jpg")
                if os.path.exists(image_path):
                    files.append(image_path)
                else:
                    is_complete = False
            if is_complete:
                return files
        
        if os.path.exists(output_folder):
            shutil.rmtree(output_folder)
        os.makedirs(output_folder, exist_ok=True)
        
        images = convert_from_path(self.path)
        for index, image in enumerate(images):
            image_path = os.path.join(output_folder, f"page_{index + 1}.jpg")
            image.save(image_path, "JPEG")
            files.append(image_path)
            logging.debug("Image Create: " + image_path)
        return files
    
    @staticmethod
    def get_match_pages_by_image(a_images, b_images):
        match_pages = []
        used_indexs = []
        if len(a_images) == len(b_images):
            for i in range(len(a_images)):
                match_pages.append([i, i, ImageHandler.get_image_same_rate(a_images[i], b_images[i])])
            return match_pages
        elif len(a_images) > len(b_images):
            is_a_more = True
            more_images = a_images
            few_images = b_images
        else:
            is_a_more = False
            more_images = b_images     
            few_images = a_images       
        for few_index, few_image in enumerate(few_images):
            match_rate = -1
            match_index = -1
            for more_index, more_image in enumerate(more_images):
                if more_index in used_indexs:
                    print("used in", more_index)
                    continue
                rate = ImageHandler.get_image_same_rate(few_image, more_image)
                print(f"rate {rate} {few_index} {more_index}")
                if rate > match_rate:
                    match_rate = rate
                    match_index = more_index
            if match_index == -1 and len(b_images) > few_index:
                match_index = few_index
                match_rate = 1
            elif match_index == -1:
                continue
            used_indexs.append(match_index)
            if is_a_more:
                match_pages.append([match_index, few_index, match_rate])
            else:
                match_pages.append([few_index, match_index, match_rate])
            print(f"match {few_index}/{len(a_images)} {match_index}/{len(b_images)}")
        return match_pages                
    
    @staticmethod
    def get_match_pages_by_text(a, b):
        match_pages = []
        for a_index in range(a.page_count):
            match_rate = -1
            match_index = -1
            a_text = a.get_page_text(a_index)
            for b_index in range(b.page_count):
                b_text = b.get_page_text(b_index)
                rate = Utils.get_same_rate(a_text, b_text)
                if rate > match_rate and rate > 0.6:
                    match_rate = rate
                    match_index = b_index
            if match_index == -1 and b.page_count >= a_index:
                match_index = a_index
            elif match_index == -1:
                continue
            match_pages.append([a_index, match_index])
        return match_pages
    
    def get_page(self, page_index):
        return self._get_chars_groups(page_index)
    
    def _get_chars_groups(self, page_index):
        with pdfplumber.open(self.path) as data:
            page = data.pages[page_index]
            words = {}
            points = []
            for char in page.chars:
                point = (char['x0'], char['y0'])
                hash_value = hash(point)
                words[hash_value] = char
                points.append(point)
            
            points_groups = self._point_clusters(points)
            
            chars_groups = []
            for group in points_groups.values():
                chars = []
                for point in group:
                    key = hash(tuple(point))
                    chars.append(words[key])
                chars = sorted(chars, key=lambda x: x['top'], reverse=False)
                chars_groups.append(chars)
            data.close()
            return chars_groups
    
    def _point_clusters(self, points):
        try:
            threshold_distance = 60.0  

            point_dict = {}
            
            dbscan = DBSCAN(eps=threshold_distance, min_samples=2)
            
            clusters = dbscan.fit(points)

            for i, cluster in enumerate(clusters.labels_):
                if cluster not in point_dict:
                    point_dict[cluster] = [points[i]]
                else:
                    point_dict[cluster].append(points[i])
            return point_dict
        except:
            return {}

