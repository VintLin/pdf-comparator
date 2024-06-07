import difflib
import string

class StringUtils:
    @staticmethod
    def similarity_ratio(a, b, remove_punctuation=True, use_contains=False):
        if remove_punctuation:
            a = StringUtils.remove_punctuation(a)
            b = StringUtils.remove_punctuation(b)
            
        ratio = difflib.SequenceMatcher(None, a, b).ratio()
        if use_contains and ratio < 0.1 and StringUtils.contains_four_consecutive(a, b):
            return 0.1
        else:
            return ratio

    @staticmethod
    def contains_four_consecutive(a, b):
        """
        Checks whether two strings contain four consecutive contiguous characters.
        """
        for i in range(len(a) - 3):  # -3 is because there must be at least four consecutive characters
            sub_a = a[i:i+4]
            if sub_a in b:
                return True
        return False
    
    @staticmethod
    def remove_punctuation(text):
        # Chinese punctuation marks
        chinese_punctuation = " 。？！，、；：“”‘’（）《》【】——…"
        all_punctuation = string.punctuation + chinese_punctuation
        translator = str.maketrans('', '', all_punctuation)
        return text.translate(translator)

    @staticmethod
    def calculate_overlap(rect1, rect2):
        # Calculated coincidence area
        x1_rect1, y1_rect1, x2_rect1, y2_rect1 = rect1
        x1_rect2, y1_rect2, x2_rect2, y2_rect2 = rect2

        area_rect1 = (x2_rect1 - x1_rect1) * (y2_rect1 - y1_rect1)

        area_rect2 = (x2_rect2 - x1_rect2) * (y2_rect2 - y1_rect2)

        x1_overlap = max(x1_rect1, x1_rect2)
        y1_overlap = max(y1_rect1, y1_rect2)

        x2_overlap = min(x2_rect1, x2_rect2)
        y2_overlap = min(y2_rect1, y2_rect2)

        width_overlap = max(0, x2_overlap - x1_overlap)
        height_overlap = max(0, y2_overlap - y1_overlap)

        area_overlap = width_overlap * height_overlap

        overlap_ratio = area_overlap / min(area_rect1, area_rect2)

        return overlap_ratio
