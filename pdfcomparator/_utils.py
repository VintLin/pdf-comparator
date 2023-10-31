
class Utils:
    @staticmethod
    def get_same_rate(str1, str2):
        try:
            m = len(str1)
            n = len(str2)

            dp = [[0] * (n + 1) for _ in range(m + 1)]

            max_len = 0
            end_index = 0

            for i in range(1, m + 1):
                for j in range(1, n + 1):
                    if str1[i - 1] == str2[j - 1]:
                        dp[i][j] = dp[i - 1][j - 1] + 1
                        if dp[i][j] > max_len:
                            max_len = dp[i][j]
                            end_index = i

            longest_substring = str1[end_index - max_len:end_index]
            same1_rate = len(longest_substring) / len(str1)
            same2_rate = len(longest_substring) / len(str2)
            if same1_rate > same2_rate:
                return same1_rate * 0.9 + same2_rate * 0.1
            else:
                return same2_rate * 0.9 + same1_rate * 0.1
        except:
            return 0.0
    
    @staticmethod
    def calculate_overlap(rect1, rect2):
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