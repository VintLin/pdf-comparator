import time
import threading
import concurrent.futures

from queue import Queue
from pdfcomparator._utils_for_image import ImageUtils
from pdfcomparator._utils_for_char import CharInfo
from pdfcomparator._utils_for_string import StringUtils
from pdfcomparator._pdf_handler import PDFHandler

class CompareUtils:
    @staticmethod
    def compare_pdf_by_image(a_pages, b_pages, is_large):        
        if len(a_pages) == len(b_pages):
            return CompareUtils._get_images_when_page_count_equal(a_pages, b_pages, is_large)
        else:
            return CompareUtils._get_images_when_page_count_different(a_pages, b_pages, is_large)
    
    @staticmethod
    def _get_images_when_page_count_equal(a_images, b_images, is_large):
        result_queue = Queue()
        threads = [threading.Thread(
            target=CompareUtils._image_similarity, 
            args=(i, a_images[i], b_images[i], result_queue)
            ) for i in range(len(b_images))]
        
        for thread in threads:
            if (is_large):
                time.sleep(0.1)
            thread.start()
            
        for thread in threads:
            thread.join()
        
        results = []
        while not result_queue.empty():
            results.append(result_queue.get())

        return results
    
    @staticmethod
    def _image_similarity(i, a_image, b_image, result_queue):
        result = ImageUtils.get_similarity(a_image, b_image)
        result_queue.put([i, i, result])
    
    @staticmethod
    def _get_images_when_page_count_different(a_images, b_images, is_large):
        match_pages = []
        used_indexes = set()
        is_a_more = len(a_images) >= len(b_images)
        more_images, few_images = (a_images, b_images) if is_a_more else (b_images, a_images)
        
        # Use ThreadPoolExecutor to parallelize image comparison
        with concurrent.futures.ThreadPoolExecutor() as executor:
            # Prepare futures for all comparisons
            futures = [
                executor.submit(
                    CompareUtils._compare_images, 
                    few_index, 
                    few_image, 
                    more_images, 
                    used_indexes
                    ) for few_index, few_image in enumerate(few_images)]
            
            # Process results as they are completed
            for future in concurrent.futures.as_completed(futures):
                few_index, match_index, match_rate = future.result()
                if match_index != -1:
                    used_indexes.add(match_index)
                    if is_a_more:
                        match_pages.append([match_index, few_index, match_rate])
                    else:
                        match_pages.append([few_index, match_index, match_rate])
                    print(f"match {few_index}/{len(a_images)} {match_index}/{len(b_images)}")
                else:
                    print(f"No match found for index {few_index}")
        return match_pages
    
    @staticmethod
    def _compare_images(image_index, origin_image, compare_images, used_indexes):
        match_rate = -1
        match_index = -1
        for index, image in enumerate(compare_images):
            if index in used_indexes:
                continue
            rate = ImageUtils.get_similarity(origin_image, image)
            if rate > match_rate:
                match_rate = rate
                match_index = index
        return image_index, match_index, match_rate
    
    @staticmethod
    def compare_pdf_by_text(a_pdf: PDFHandler, a_index: int, b_pdf: PDFHandler, b_index: int):
        # 1. get pdf chars
        a_lines = a_pdf.get_page_chars(a_index)
        b_lines = b_pdf.get_page_chars(b_index)
        
        # 2. group chars convert to text
        a_texts = PDFHandler.get_texts(a_lines)
        b_texts = PDFHandler.get_texts(b_lines)
        
        # 3. find matching
        a_info = CharInfo(a_lines)
        b_info = CharInfo(b_lines)

        for a_line_index, a_text in enumerate(a_texts):
            # 3.1 find matching text based on similarity
            matches = CompareUtils._find_matches(a_text, b_texts)
            
            # 3.2 Matches every character in the text
            for b_line_index, b_text, ratio in matches:
                if ratio < 0.1:
                    continue
                match_char_indexs = CompareUtils._get_match_char_indexs(a_text, b_text)
                for a_char_index, b_char_index in match_char_indexs:
                    if a_info.is_used(a_line_index, a_char_index) or \
                        b_info.is_used(b_line_index, b_char_index):
                            continue
                    
                    a_char = a_lines[a_line_index][a_char_index]
                    b_char = b_lines[b_line_index][b_char_index]
                    
                    state = CompareUtils._get_state(a_char, b_char)
                    
                    a_info.set_char_match(a_line_index, a_char_index, state)
                    b_info.set_char_match(b_line_index, b_char_index, state)
        CompareUtils._check_chars(a_info, b_info)
        return [a_info.get_result(), b_info.get_result()]
        
    @staticmethod
    def _find_matches(a_text, b_texts):
        # Calculate the similarity and find the best match
        matches = []
        for b_index, b_text in enumerate(b_texts):
            ratio = StringUtils.similarity_ratio(a_text, b_text)
            # Add complete matching information
            matches.append([b_index, b_text, ratio])
        
        sorted_matches = sorted(matches, key=lambda x: x[2], reverse=True)
        
        return sorted_matches

    @staticmethod
    def _get_match_char_indexs(a_text, b_text):
        matches_index = []
        for a_char_index in range(len(a_text)):
            a_split_texts = CompareUtils._get_split_texts(a_char_index, a_text)
            for distance, split_text in a_split_texts:    
                try:
                    match_index = b_text.find(split_text)
                    b_char_index = match_index + distance
                    if match_index == -1 or b_char_index >= len(b_text):
                        continue
                    matches_index.append([a_char_index, b_char_index])
                    break
                except:
                    print("Error")
        return matches_index

    @staticmethod
    def _get_split_texts(char_index, line, include=6):
        texts = set()
        for left_index in range(include, -1, -1):
            for right_index in range(include, -1, -1):
                start_index = char_index - left_index
                start_index = 0 if start_index < 0 else start_index
                
                end_index = char_index + right_index
                end_index = len(line) - 1 if end_index >= len(line) else end_index

                text = line[start_index: end_index + 1]
                
                if len(text) > 4 or len(line) == len(text):
                    texts.add((char_index - start_index, text))
        
        texts = sorted(texts, key=lambda x: len(x[1]), reverse=True)
        return texts

    @staticmethod
    def _get_state(a, b):
        is_same_text, is_same_size, is_same_color = CompareUtils._is_equal(a, b)
        state = CharInfo.STATE_DIFF
        if is_same_text:
            state = CharInfo.STATE_SAME if is_same_size and is_same_color else CharInfo.STATE_SIZE_COLOR_DIFF
        return state

    @staticmethod
    def _is_equal(a, b):
        try:
            is_same_text = a['text'] == b['text'] and not a['text'].isspace() and not b['text'].isspace()
            is_same_size = CompareUtils._round_off(a['size']) == CompareUtils._round_off(b['size'])
            is_same_color = a['non_stroking_color'] == b['non_stroking_color'] and a['stroking_color'] == a['stroking_color']
            return [is_same_text, is_same_size, is_same_color]
        except:
            return [False, False, False]

    @staticmethod
    def _round_off(number):
        integer_part = int(number)
        decimal_part = number - integer_part
        if decimal_part > 0.75:
            category = 1
        elif decimal_part >= 0.25:
            category = 0.5
        else:
            category = 0
        return integer_part + category

    @staticmethod
    def _check_chars(a_info:CharInfo, b_info:CharInfo):
        # Leak filling
        a_diff_chars = a_info.get_diff_chars()
        b_diff_chars = b_info.get_diff_chars()
        
        for a_char, a_line_index, a_char_index in a_diff_chars:
            for b_char, b_line_index, b_char_index in b_diff_chars:
                try:
                    state = CompareUtils._get_state(a_char, b_char)
                    if state != CharInfo.STATE_DIFF:
                        overlap = StringUtils.calculate_overlap([a_char['x0'], a_char['y0'], a_char['x1'], a_char['y1']], [b_char['x0'], b_char['y0'], b_char['x1'], b_char['y1']])
                        if overlap < 0.6:
                            continue
                        a_info.set_char_match(a_line_index, a_char_index, state)
                        b_info.set_char_match(b_line_index, b_char_index, state)
                        break
                except:
                    print("check chars error")
    
    