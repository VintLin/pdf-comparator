import math

from pdfplumber.ctm import CTM


class PDFTextGeometry:
    @staticmethod
    def _round_to_half(value):
        if value is None:
            return 0.0
        return round(value * 2) / 2

    @staticmethod
    def _calculate_overlap_with_rotation(rect1, rect2, is_vertical_layout=False, rotation_deg=0.0):
        base_axis = 0.0 if is_vertical_layout else 90.0
        axis_angle_rad = math.radians(base_axis + rotation_deg)
        cos_a = math.cos(axis_angle_rad)
        sin_a = math.sin(axis_angle_rad)

        x0_1, top1, x1_1, bottom1 = rect1
        x0_2, top2, x1_2, bottom2 = rect2

        corners1 = [(x0_1, top1), (x1_1, top1), (x0_1, bottom1), (x1_1, bottom1)]
        projs1 = [x * cos_a + y * sin_a for x, y in corners1]
        s1, e1 = min(projs1), max(projs1)

        corners2 = [(x0_2, top2), (x1_2, top2), (x0_2, bottom2), (x1_2, bottom2)]
        projs2 = [x * cos_a + y * sin_a for x, y in corners2]
        s2, e2 = min(projs2), max(projs2)

        h1, h2 = e1 - s1, e2 - s2
        if h1 == 0 or h2 == 0:
            return {"overlap_len": 0, "iou": 0.0, "coverage": 0.0}

        overlap_len = max(0, min(e1, e2) - max(s1, s2))
        union_len = h1 + h2 - overlap_len
        iou = overlap_len / union_len if union_len > 0 else 0
        coverage = overlap_len / min(h1, h2) if min(h1, h2) > 0 else 0

        return {"overlap_len": overlap_len, "iou": iou, "coverage": coverage}

    @staticmethod
    def _calculate_rect_distance(rect1, rect2, use_center=True):
        if use_center:
            center1_x = (rect1[0] + rect1[2]) / 2
            center1_y = (rect1[1] + rect1[3]) / 2
            center2_x = (rect2[0] + rect2[2]) / 2
            center2_y = (rect2[1] + rect2[3]) / 2
            return math.sqrt((center1_x - center2_x) ** 2 + (center1_y - center2_y) ** 2)

        dx = max(0, rect2[0] - rect1[2], rect1[0] - rect2[2])
        dy = max(0, rect2[1] - rect1[3], rect1[1] - rect2[3])
        return math.sqrt(dx ** 2 + dy ** 2)

    @staticmethod
    def _word_to_rect(word):
        x0 = word.get("x0")
        top = word.get("top")
        x1 = word.get("x1")
        bottom = word.get("bottom")
        if x0 is None or top is None or x1 is None or bottom is None:
            return None
        return (x0, top, x1, bottom)

    @staticmethod
    def get_perfect_bbox(char):
        a, b, c, d, e, f = char["matrix"]
        adv = char.get("adv", 1.0)

        ph_1 = char["bottom"] + char["y0"]
        ph_2 = char["top"] + char["y1"]
        page_height = (ph_1 + ph_2) / 2

        origin = (e, f)
        vec_width = (a * adv, b * adv)
        vec_height = (c, d)

        p0 = origin
        p1 = (origin[0] + vec_width[0], origin[1] + vec_width[1])
        p2 = (origin[0] + vec_height[0], origin[1] + vec_height[1])
        p3 = (origin[0] + vec_width[0] + vec_height[0], origin[1] + vec_width[1] + vec_height[1])

        points_page = []
        for px, py in [p0, p1, p2, p3]:
            points_page.append((px, page_height - py))

        xs = [p[0] for p in points_page]
        ys = [p[1] for p in points_page]
        final_bbox = [min(xs), min(ys), max(xs), max(ys)]
        return final_bbox, points_page

    @staticmethod
    def _char_to_rect(char):
        if (
            not isinstance(char, dict)
            or "matrix" not in char
            or "y0" not in char
            or "y1" not in char
        ):
            return (
                float(char.get("x0", 0) or 0),
                float(char.get("top", 0) or 0),
                float(char.get("x1", 0) or 0),
                float(char.get("bottom", 0) or 0),
            )

        stable_rect, _ = PDFTextGeometry.get_perfect_bbox(char)
        return (stable_rect[0], stable_rect[1], stable_rect[2], stable_rect[3])

    @staticmethod
    def _get_char_rotation(char):
        matrix = char.get("matrix")
        if not matrix or len(matrix) < 6:
            return 0.0
        try:
            ctm = CTM(*matrix)
            return ctm.skew_x
        except Exception:
            return 0.0

    def _get_avg_rotation(self, item):
        chars = item.get("chars", [item])
        if not chars:
            return 0.0
        rotations = [self._get_char_rotation(c) for c in chars]
        return sum(rotations) / len(rotations)

    def _detect_text_direction(self, chars, new_char=None):
        if not chars:
            return "ltr"

        rotations = [self._get_char_rotation(c) for c in chars]
        avg_rotation = sum(rotations) / len(rotations) if rotations else 0.0

        if 140 <= abs(avg_rotation) <= 220:
            return "reversed"
        if 80 <= avg_rotation <= 100:
            return "vertical_down"
        if -100 <= avg_rotation <= -80:
            return "vertical_up"

        if len(chars) < 2:
            if not new_char:
                return "ltr"
            base = chars[0]
            dx = abs((new_char.get("x0", 0) or 0) - (base.get("x0", 0) or 0))
            dy = abs((new_char.get("top", 0) or 0) - (base.get("top", 0) or 0))
            if dy > dx * 2:
                return "vertical_layout_down"
            return "ltr"

        x_deltas = [
            chars[i + 1].get("x0", 0) - chars[i].get("x0", 0)
            for i in range(len(chars) - 1)
        ]
        y_deltas = [
            chars[i + 1].get("top", 0) - chars[i].get("top", 0)
            for i in range(len(chars) - 1)
        ]
        avg_x_delta = sum(x_deltas) / len(x_deltas) if x_deltas else 0
        avg_y_delta = sum(y_deltas) / len(y_deltas) if y_deltas else 0

        if abs(avg_y_delta) > abs(avg_x_delta):
            return "vertical_layout_down" if avg_y_delta > 0 else "vertical_layout_up"
        if avg_x_delta < 0:
            return "rtl"
        return "ltr"

    def _get_sentence_direction(self, sentence):
        return self._detect_text_direction(sentence.get("chars", []))

    def _insert_char_to_word(self, target_word, source_word):
        source_chars = source_word.get("chars", [])
        if not source_chars:
            return

        target_chars = target_word.get("chars", [])
        for new_char in source_chars:
            target_chars = self._insert_single_char(target_chars, new_char)

        target_word["chars"] = target_chars
        target_word["text"] = "".join(c.get("text", "") for c in target_chars)
        target_word["x0"] = min(target_word.get("x0", 0), source_word.get("x0", 0))
        target_word["x1"] = max(target_word.get("x1", 0), source_word.get("x1", 0))
        target_word["top"] = min(target_word.get("top", 0), source_word.get("top", 0))
        target_word["bottom"] = max(target_word.get("bottom", 0), source_word.get("bottom", 0))
        target_word["height"] = abs(target_word.get("bottom", 0) - target_word.get("top", 0))
        target_word["width"] = abs(target_word.get("x1", 0) - target_word.get("x0", 0))

    def _insert_single_char(self, chars, new_char):
        if not chars:
            return [new_char]

        direction = self._detect_text_direction(chars, new_char)
        new_rect = self._char_to_rect(new_char)
        new_x0 = new_char.get("x0", 0)
        new_top = new_char.get("top", 0)

        best_idx = 0
        best_distance = float("inf")
        for idx, char in enumerate(chars):
            char_rect = self._char_to_rect(char)
            distance = self._calculate_rect_distance(new_rect, char_rect)
            if distance < best_distance:
                best_distance = distance
                best_idx = idx

        best_char = chars[best_idx]
        best_x0 = best_char.get("x0", 0)
        best_top = best_char.get("top", 0)

        if len(chars) < 2 and direction == "ltr":
            insert_idx = best_idx if new_x0 < best_x0 else best_idx + 1
        elif direction in ("reversed", "rtl"):
            if new_x0 > best_x0:
                insert_idx = best_idx
            elif new_x0 < best_x0:
                insert_idx = best_idx + 1
            elif new_top < best_top:
                insert_idx = best_idx
            else:
                insert_idx = best_idx + 1
        elif direction in ("vertical_down", "vertical_layout_down"):
            if new_top < best_top:
                insert_idx = best_idx
            elif new_top > best_top:
                insert_idx = best_idx + 1
            elif new_x0 < best_x0:
                insert_idx = best_idx
            else:
                insert_idx = best_idx + 1
        elif direction in ("vertical_up", "vertical_layout_up"):
            if new_top > best_top:
                insert_idx = best_idx
            elif new_top < best_top:
                insert_idx = best_idx + 1
            elif new_x0 < best_x0:
                insert_idx = best_idx
            else:
                insert_idx = best_idx + 1
        else:
            if new_x0 < best_x0:
                insert_idx = best_idx
            elif new_x0 > best_x0:
                insert_idx = best_idx + 1
            elif new_top < best_top:
                insert_idx = best_idx
            else:
                insert_idx = best_idx + 1

        result = chars.copy()
        result.insert(insert_idx, new_char)
        return result

    @staticmethod
    def _get_word_font_size(word):
        chars = word.get("chars", [])
        if chars:
            size = chars[-1].get("size", 15.0)
            return PDFTextGeometry._round_to_half(size)
        height = word.get("height")
        if height is not None:
            return PDFTextGeometry._round_to_half(height)
        return 15.0

    @staticmethod
    def _avg_char_height(words, fallback=15.0):
        heights = []
        for word in words:
            for char in word.get("chars", []):
                heights.append(char.get("height", fallback))
        return sum(heights) / len(heights) if heights else fallback

    @staticmethod
    def _max_char_height(words, fallback=15.0):
        max_height = 0
        for word in words:
            for char in word.get("chars", []):
                current = char.get("height", fallback)
                if max_height < current:
                    max_height = current
        return max_height if max_height else fallback

    @staticmethod
    def _is_vertical_direction(direction):
        return direction in ("vertical_down", "vertical_up", "vertical_layout_down", "vertical_layout_up")

    def _sorted_chars(self, chars):
        if not chars:
            return []
        return sorted(chars, key=lambda item: (self._round_to_half(item.get("top", 0)), self._round_to_half(item.get("x0", 0))))
