from pdfcomparator._pdf_file import PDFFile
from pdfcomparator._utils import Utils
import logging

class DiffChar:
    def __init__(self, page) -> None:
        self.page = page
        self.same_indexs = {index: set() for index in range(len(page))}
        self.size_indexs = {index: set() for index in range(len(page))}
        self.color_indexs = {index: set() for index in range(len(page))}
        self.size_color_indexs = {index: set() for index in range(len(page))}

    def is_contain_index(self, page_index, char_index):
        return char_index in self.same_indexs[page_index] or \
        char_index in self.size_indexs[page_index] or \
        char_index in self.color_indexs[page_index] or \
        char_index in self.size_color_indexs[page_index]
    
    def is_contain_char(self, char):
        return char in self.same_chars or \
            char in self.size_chars or \
            char in self.color_chars or \
            char in self.size_color_chars
    
    def trim_chars(self):
        self.same_chars = []
        self.size_chars = []
        self.color_chars = []
        self.size_color_chars = []
        self.diff_chars = []
        for index, chars in enumerate(self.page):
            for char_index, char in enumerate(chars):
                if char_index in self.same_indexs[index]: 
                    self.same_chars.append(char)
                elif char_index in self.size_indexs[index]: 
                    self.size_chars.append(char)
                elif char_index in self.color_indexs[index]: 
                    self.color_chars.append(char)
                elif char_index in self.size_color_indexs[index]: 
                    self.size_color_chars.append(char)
                elif char not in self.diff_chars:
                    self.diff_chars.append(char)

    def get_result(self):
        return [self.same_chars, self.size_chars, self.color_chars, self.size_color_chars, self.diff_chars]
    
    @staticmethod
    def compare_char(a_diff_chars, a_page_index, a_char_index, a_char, b_diff_chars, b_page_index, b_char_index, b_char):
        text_same, size_same, color_same = PDFFile.is_char_equal(a_char, b_char)
        if text_same and size_same and color_same:
            a_diff_chars.same_indexs[a_page_index].add(a_char_index)
            b_diff_chars.same_indexs[b_page_index].add(b_char_index)
        elif text_same and not size_same and color_same:
            a_diff_chars.size_indexs[a_page_index].add(a_char_index)
            b_diff_chars.size_indexs[b_page_index].add(b_char_index)
        elif text_same and size_same and not color_same:
            a_diff_chars.color_indexs[a_page_index].add(a_char_index)
            b_diff_chars.color_indexs[b_page_index].add(b_char_index)
        elif text_same and not size_same and not color_same:
            a_diff_chars.size_color_indexs[a_page_index].add(a_char_index)
            b_diff_chars.size_color_indexs[b_page_index].add(b_char_index)
    
    @staticmethod
    def chars_check(a_diff_chars, b_diff_chars):
        a_remove_chars = []
        b_remove_chars = []
        for a_char in a_diff_chars.diff_chars:
            for b_char in b_diff_chars.diff_chars:
                text_same, size_same, color_same = PDFFile.is_char_equal(a_char, b_char)
                if text_same:
                    overlap = Utils.calculate_overlap([a_char['x0'], a_char['y0'], a_char['x1'], a_char['y1']], [b_char['x0'], b_char['y0'], b_char['x1'], b_char['y1']])
                    is_a_contain = a_diff_chars.is_contain_char(a_char)
                    is_b_contain = b_diff_chars.is_contain_char(b_char)
                    if overlap < 0.6 or is_a_contain or is_b_contain:
                        continue
                    if size_same and color_same:
                        a_diff_chars.same_chars.append(a_char)
                        b_diff_chars.same_chars.append(b_char)
                    elif not size_same and color_same:
                        a_diff_chars.size_chars.append(a_char)
                        b_diff_chars.size_chars.append(b_char)
                    elif size_same and not color_same:
                        a_diff_chars.color_chars.append(a_char)
                        b_diff_chars.color_chars.append(b_char)
                    else:
                        a_diff_chars.size_color_chars.append(a_char)
                        b_diff_chars.size_color_chars.append(b_char)
                    a_remove_chars.append(a_char)
                    b_remove_chars.append(b_char)
                    break
        for char in a_remove_chars:
            if char in a_diff_chars.diff_chars:
                a_diff_chars.diff_chars.remove(char)
        for char in b_remove_chars:
            if char in b_diff_chars.diff_chars:
                b_diff_chars.diff_chars.remove(char)
    
def compare_page_text(a_page, b_page):
    a_diff_chars = DiffChar(a_page)
    b_diff_chars = DiffChar(b_page)
    for a_index, a_chars in enumerate(a_page):
        a_sentence = PDFFile.get_page_sentence(a_chars)
        b_sentences = list(map(lambda b_chars: PDFFile.get_page_sentence(b_chars), b_page))
        
        match_indexs = get_match_sentence(a_sentence, b_sentences)
        if not match_indexs:
            continue
        
        logging.debug(f"a: {PDFFile.get_page_sentence(a_chars)}")
        for match_index, rate in match_indexs.items():
            b_index = match_index
            b_chars = b_page[match_index]
            b_sentence = PDFFile.get_page_sentence(b_chars)
            
            logging.debug(f"b: {b_sentence} rate: {rate}")
            
            match_content = ""
            no_match_content = ""
            for a_char_index, a_char in enumerate(a_chars):
                a_sentences = get_split_sentence(a_sentence, a_char_index)
                for sentence in a_sentences:
                    if len(sentence[0]) < 3 and not (rate == 1 and len(a_sentence) == len(b_sentence)):
                        continue
                    match_index = b_sentence.find(sentence[0])
                    if match_index == -1:
                        continue
                    b_char_index = match_index + sentence[1]
                    if b_char_index >= len(b_chars):
                        continue
                    
                    b_char = b_chars[b_char_index]
                    is_a_contain = a_diff_chars.is_contain_index(a_index, a_char_index)
                    is_b_contain = b_diff_chars.is_contain_index(b_index, b_char_index)
                    if not is_a_contain and not is_b_contain:
                        match_content += f"({a_char['text']}, {a_char_index}, {b_char_index}) "
                        DiffChar.compare_char(
                            a_diff_chars, a_index, a_char_index, a_char, 
                            b_diff_chars, b_index, b_char_index, b_char,
                        )
                    else:
                        no_match_content += f"({a_char['text']} > \"{sentence}\" {is_a_contain} {is_b_contain}) " 
                    break
            logging.debug(f"match {match_content}")
            logging.debug(f"no match {no_match_content}")
            
    a_diff_chars.trim_chars()
    b_diff_chars.trim_chars()
    
    DiffChar.chars_check(a_diff_chars, b_diff_chars)
    
    return [a_diff_chars.get_result(), b_diff_chars.get_result()]

def get_match_sentence(a_sentence, b_sentences):
    match_indexs = {}
    for b_index, b_sentence in enumerate(b_sentences):
        rate = Utils.get_same_rate(a_sentence, b_sentence)
        if rate > 0 and b_index not in match_indexs:
            match_indexs[b_index] = rate
    match_indexs = dict(sorted(match_indexs.items(), key=lambda item: item[1], reverse=True))
    return match_indexs

def get_split_sentence(sentence, current_index, split_number=6):
    sentences = set()
    
    for left_index in range(split_number, -1, -1):
        for right_index in range(split_number, -1, -1):
            start_index = current_index - left_index
            if start_index < 0:
                start_index = 0
            end_index = current_index + right_index
            if end_index >= len(sentence):
                end_index = len(sentence) - 1
            content = sentence[start_index: end_index + 1]
            sentences.add((content, current_index - start_index))
    
    sentences = sorted(sentences, key=lambda x: len(x[0]), reverse=True)
    return sentences
