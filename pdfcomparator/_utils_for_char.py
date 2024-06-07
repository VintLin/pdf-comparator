import string
from sklearn.cluster import DBSCAN
from pdfcomparator._utils_for_string import StringUtils

class CharUtils:
    @staticmethod
    def divide_groups(chars):
        words = {}  
        points = []
        for char in chars:
            point = (char['x0'], char['y1'])
            hash_value = hash(point)
            points.append(point)
            words[hash_value] = char
        
        points_groups = CharUtils._divide_point(points)
        
        text_groups = []
        for points in points_groups.values():
            chars = []
            for point in points:
                key = hash(tuple(point))
                chars.append(words[key])
            chars = CharUtils._sorted_chars(chars)
            text_groups.append(chars)
        return text_groups
    
    @staticmethod
    def _sorted_chars(chars, tolerance=1):
        v_chars = []
        h_chars = sorted(chars, key=lambda x: x['y1'], reverse=True)
        horizontal_groups = []
        current_group = []
        pre_top_y = h_chars[0]['y1']
        pre_bottom_y = h_chars[0]['y0']
        for char in h_chars:
            current_top_y = char['y1']
            current_bottom_y = char['y0']
            arrange = False
            if CharUtils.is_punctuation(char['text']):
                over_top_y = -1
                over_bottom_y = -1
                if current_top_y <= pre_top_y:
                    over_top_y = current_top_y
                else:
                    over_top_y = pre_top_y
                
                if current_bottom_y <= pre_bottom_y:
                    over_bottom_y = pre_bottom_y
                else:
                    over_bottom_y = current_bottom_y
                
                if over_top_y >= over_bottom_y:
                    overlay = (over_top_y - over_bottom_y) / (current_top_y - current_bottom_y)
                    arrange = overlay > 0.8

            if abs(current_top_y - pre_top_y) <= tolerance or arrange:
                current_group.append(char)
            else:
                if len(current_group) == 1:
                    v_chars.append(current_group[0])
                else:
                    current_group = sorted(current_group, key=lambda x: x['x0'], reverse=False)
                    horizontal_groups.append(current_group)
                current_group = [char]
                pre_top_y = current_top_y
                pre_bottom_y = current_bottom_y
        
        if len(current_group) == 1:
            v_chars.append(current_group[0])
        else:
            current_group = sorted(current_group, key=lambda x: x['x0'], reverse=False)
            horizontal_groups.append(current_group)
            
        if not v_chars:
            chars = [char for group in horizontal_groups for char in group]
            return CharUtils._filter_char_by_overlap(chars)
        
        v_chars = sorted(v_chars, key=lambda x: x['x0'], reverse=False)
        vertical_groups = []
        current_group = []
        pre_mid_x = (v_chars[0]['x0'] + v_chars[0]['x1']) / 2.0
        for char in v_chars:
            current_mid_x = (char['x0'] + char['x1']) / 2.0
            if abs(current_mid_x - pre_mid_x) <= tolerance:
                current_group.append(char)
            else:
                current_group = sorted(current_group, key=lambda x: x['y1'], reverse=True)
                vertical_groups.append(current_group)
                current_group = [char]
                pre_mid_x = current_mid_x
        
        if current_group:
            current_group = sorted(current_group, key=lambda x: x['y1'], reverse=True)
            vertical_groups.append(current_group)
        sorted_chars = [char for group in horizontal_groups for char in group]
        sorted_chars.extend([char for group in vertical_groups for char in group])
        return CharUtils._filter_char_by_overlap(sorted_chars)
    
    @staticmethod
    def _filter_char_by_overlap(chars):
        for index in range(len(chars) - 1, 0, -1):
            current_char = chars[index]
            pre_char = chars[index - 1]
            if current_char['text'] != pre_char['text']:
                continue
            overlap = StringUtils.calculate_overlap(
                [current_char['x0'], current_char['y0'], current_char['x1'], current_char['y1']], 
                [pre_char['x0'], pre_char['y0'], pre_char['x1'], pre_char['y1']],
                )
            if overlap > 0.8:
                del chars[index]
        return chars
    
    @staticmethod
    def _divide_point(points):
        try:
            threshold_distance = 40.0  
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
        
    @staticmethod
    def is_punctuation(char):
        punctuation_set = set(string.punctuation + '，。；：！？【】（）《》‘’“”－／％')
        return char in punctuation_set

class CharInfo:
    STATE_DIFF = -1
    STATE_SIZE_COLOR_DIFF = 0
    STATE_SAME = 1
    
    colors = {
        STATE_SAME: (0, 255, 0),  # Green: Just the same
        STATE_SIZE_COLOR_DIFF: (0, 165, 230),  # Orange: The size and color are different
        STATE_DIFF: (0, 0, 255)  # Red: Totally different
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
            CharInfo.STATE_SIZE_COLOR_DIFF: size_color_diff_chars
        }
    
    def set_char_match(self, line_index, char_index, state):
        self.match_chars[line_index][char_index] = state
        
    def set_line_match(self, line_index, state):
        for index in range(len(self.match_chars[line_index])):
            self.match_chars[line_index][index] = state
    
    def get_diff_chars(self):
        diff_chars = []
        for line_index, line in enumerate(self.match_chars):
            for char_index, char_state in enumerate(line):
                if char_state == CharInfo.STATE_DIFF:
                    diff_chars.append([self.chars[line_index][char_index], line_index, char_index])
        return diff_chars
