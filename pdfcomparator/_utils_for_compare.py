import logging
import concurrent.futures

from pdfcomparator._utils_for_image import ImageUtils
from pdfcomparator._utils_for_string import StringUtils
from pdfcomparator._pdf_handler import PDFHandler

logger = logging.getLogger(__name__)


class CharInfo:
    STATE_DIFF = -1
    STATE_SIZE_COLOR_DIFF = 0
    STATE_SAME = 1

    colors = {
        STATE_SAME: (0, 255, 0),  # Green: exact match
        STATE_SIZE_COLOR_DIFF: (0, 165, 230),  # Orange: text matches but style differs
        STATE_DIFF: (0, 0, 255),  # Red: unmatched
    }

    def __init__(self, chars) -> None:
        self.chars = chars
        self.match_chars = [[CharInfo.STATE_DIFF for _ in range(len(line))] for line in chars]

    def is_used(self, line_index, char_index):
        return self.match_chars[line_index][char_index] != CharInfo.STATE_DIFF

    def get_result(self):
        diff_chars = []
        same_chars = []
        size_color_diff_chars = []
        for i, line in enumerate(self.match_chars):
            for j, char_state in enumerate(line):
                char = self.chars[i][j]
                if char_state == CharInfo.STATE_DIFF:
                    diff_chars.append(char)
                elif char_state == CharInfo.STATE_SAME:
                    same_chars.append(char)
                elif char_state == CharInfo.STATE_SIZE_COLOR_DIFF:
                    size_color_diff_chars.append(char)
                else:
                    diff_chars.append(char)
        return {
            CharInfo.STATE_DIFF: diff_chars,
            CharInfo.STATE_SAME: same_chars,
            CharInfo.STATE_SIZE_COLOR_DIFF: size_color_diff_chars,
        }

    def set_char_match(self, line_index, char_index, state):
        self.match_chars[line_index][char_index] = state

    def get_diff_chars(self):
        diff_chars = []
        for line_index, line in enumerate(self.match_chars):
            for char_index, char_state in enumerate(line):
                if char_state == CharInfo.STATE_DIFF:
                    diff_chars.append([self.chars[line_index][char_index], line_index, char_index])
        return diff_chars


class CompareUtils:
    @staticmethod
    def compare_pdf_by_image(a_pages, b_pages, is_large):        
        if len(a_pages) == len(b_pages):
            return CompareUtils._get_images_when_page_count_equal(a_pages, b_pages, is_large)
        else:
            return CompareUtils._get_images_when_page_count_different(a_pages, b_pages, is_large)

    @staticmethod
    def _get_images_when_page_count_equal(a_images, b_images, is_large):
        if not a_images:
            return []

        max_workers = CompareUtils._get_max_workers(len(a_images), is_large)
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            rates = list(executor.map(ImageUtils.get_similarity, a_images, b_images))
        return [[index, index, rate] for index, rate in enumerate(rates)]

    @staticmethod
    def _get_images_when_page_count_different(a_images, b_images, is_large):
        is_a_more = len(a_images) >= len(b_images)
        more_images, few_images = (a_images, b_images) if is_a_more else (b_images, a_images)

        if not more_images or not few_images:
            return []

        max_workers = CompareUtils._get_max_workers(len(more_images) * len(few_images), is_large)
        candidates = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_map = {
                executor.submit(ImageUtils.get_similarity, few_image, more_image): (few_index, more_index)
                for few_index, few_image in enumerate(few_images)
                for more_index, more_image in enumerate(more_images)
            }
            for future in concurrent.futures.as_completed(future_map):
                few_index, more_index = future_map[future]
                rate = future.result()
                candidates.append((few_index, more_index, rate))

        candidates.sort(key=lambda item: item[2], reverse=True)

        used_few_indexes = set()
        used_more_indexes = set()
        match_pages = []
        for few_index, more_index, match_rate in candidates:
            if few_index in used_few_indexes or more_index in used_more_indexes:
                continue

            used_few_indexes.add(few_index)
            used_more_indexes.add(more_index)
            if is_a_more:
                match_pages.append([more_index, few_index, match_rate])
            else:
                match_pages.append([few_index, more_index, match_rate])
            logger.debug("Matched page %s with %s at rate %.4f", few_index, more_index, match_rate)

            if len(used_few_indexes) == len(few_images):
                break

        match_pages.sort(key=lambda item: (item[0], item[1]))
        return match_pages

    @staticmethod
    def _get_max_workers(task_count, is_large):
        if task_count <= 1:
            return 1
        if is_large:
            return min(2, task_count)
        return min(8, task_count)

    @staticmethod
    def compare_pdf_by_text(a_pdf: PDFHandler, a_index: int, b_pdf: PDFHandler, b_index: int):
        # 1. get pdf chars
        a_lines = a_pdf.get_page_chars(a_index)
        b_lines = b_pdf.get_page_chars(b_index)
        
        # 2. Convert extracted char groups back to comparable text snippets.
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
                match_index = b_text.find(split_text)
                b_char_index = match_index + distance
                if match_index == -1 or b_char_index >= len(b_text):
                    continue
                matches_index.append([a_char_index, b_char_index])
                break
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
        a_text = a.get("text")
        b_text = b.get("text")
        if not a_text or not b_text or a_text.isspace() or b_text.isspace():
            return [False, False, False]

        try:
            is_same_size = CompareUtils._round_off(a.get("size")) == CompareUtils._round_off(b.get("size"))
        except (TypeError, ValueError):
            return [False, False, False]

        is_same_text = a_text == b_text
        is_same_color = (
            a.get("non_stroking_color") == b.get("non_stroking_color")
            and a.get("stroking_color") == b.get("stroking_color")
        )
        return [is_same_text, is_same_size, is_same_color]

    @staticmethod
    def _round_off(number):
        if number is None:
            return 0
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
                state = CompareUtils._get_state(a_char, b_char)
                if state == CharInfo.STATE_DIFF:
                    continue

                overlap = CompareUtils._get_overlap(a_char, b_char)
                if overlap < 0.6:
                    continue

                a_info.set_char_match(a_line_index, a_char_index, state)
                b_info.set_char_match(b_line_index, b_char_index, state)
                break

    @staticmethod
    def _get_overlap(a_char, b_char):
        required_keys = ("x0", "y0", "x1", "y1")
        if any(key not in a_char or key not in b_char for key in required_keys):
            return 0
        return StringUtils.calculate_overlap(
            [a_char["x0"], a_char["y0"], a_char["x1"], a_char["y1"]],
            [b_char["x0"], b_char["y0"], b_char["x1"], b_char["y1"]],
        )
