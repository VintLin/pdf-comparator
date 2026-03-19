import networkx as nx

from pdfcomparator._pdf_text_geometry import PDFTextGeometry


class PDFTextGrouping(PDFTextGeometry):
    def _is_valid_vertical_neighbor(self, current, next_sent, check_font=True, distance_limit_ratio=1.5):
        direction = self._get_sentence_direction(current)
        is_vertical = self._is_vertical_direction(direction)
        distance_limit = self._max_char_height([current, next_sent]) * distance_limit_ratio
        rotation = self._get_avg_rotation(current)
        rect_current = (current.get("x0", 0), current.get("top", 0), current.get("x1", 0), current.get("bottom", 0))
        rect_next = (next_sent.get("x0", 0), next_sent.get("top", 0), next_sent.get("x1", 0), next_sent.get("bottom", 0))

        if is_vertical:
            current_main = current.get("chars", [])[0].get("x0", 0)
            current_main_end = current.get("chars", [])[0].get("x1", 0)
            next_main = next_sent.get("chars", [])[0].get("x0", 0)
            overlap_info = self._calculate_overlap_with_rotation(
                rect_current, rect_next, is_vertical_layout=False, rotation_deg=rotation
            )
        else:
            current_main = current.get("chars", [])[0].get("top", 0)
            current_main_end = current.get("chars", [])[0].get("bottom", 0)
            next_main = next_sent.get("chars", [])[0].get("top", 0)
            overlap_info = self._calculate_overlap_with_rotation(
                rect_current, rect_next, is_vertical_layout=True, rotation_deg=rotation
            )

        if direction in ("vertical_up", "vertical_layout_up", "reversed"):
            distance = current_main - next_main
        else:
            distance = next_main - current_main_end

        if abs(distance) > distance_limit:
            return False
        if overlap_info["coverage"] < 0.3:
            return False

        if check_font:
            current_fontname = current.get("fontname", "")
            next_fontname = next_sent.get("fontname", "")
            current_size = self._get_word_font_size(current)
            next_size = self._get_word_font_size(next_sent)
            if current_fontname != next_fontname or current_size != next_size:
                return False

        return True

    def _is_valid_horizontal_neighbor(self, current, next_sent, check_font=True):
        current_height = current.get("height", 15)
        tolerance = 0.2 * current_height
        if abs(next_sent.get("top", 0) - current.get("top", 0)) > tolerance:
            return False

        if check_font:
            current_fontname = current.get("fontname", "").split("+")[-1]
            next_fontname = next_sent.get("fontname", "").split("+")[-1]
            current_size = self._get_word_font_size(current)
            next_size = self._get_word_font_size(next_sent)
            if current_fontname != next_fontname or current_size != next_size:
                return False

        return True

    def _find_best_neighbor(self, current, candidates):
        current_x0 = current.get("x0", 0)
        current_x1 = current.get("x1", 0)
        current_rect = self._word_to_rect(current) or (current_x0, current.get("top", 0), current_x1, current.get("bottom", 0))

        best_idx, best_sent = candidates[0]
        best_score = float("inf")

        for idx, sent in candidates:
            sent_x0 = sent.get("x0", 0)
            sent_x1 = sent.get("x1", 0)
            sent_rect = self._word_to_rect(sent) or (sent_x0, sent.get("top", 0), sent_x1, sent.get("bottom", 0))

            left_align_diff = abs(current_x0 - sent_x0)
            right_align_diff = abs(current_x1 - sent_x1)
            align_score = min(left_align_diff, right_align_diff)
            distance = self._calculate_rect_distance(current_rect, sent_rect, False)
            score = align_score * 0.5 + distance

            if score < best_score:
                best_score = score
                best_idx = idx
                best_sent = sent

        return best_idx, best_sent

    def _merge_sentence_groups(self, sentences, join_str):
        if not sentences:
            return {"text": "", "x0": 0, "x1": 0, "top": 0, "bottom": 0, "height": 0, "fontname": "", "chars": []}
        if len(sentences) == 1:
            return sentences[0].copy()

        texts = [s.get("text", "") for s in sentences]
        merged_text = join_str.join(texts)
        x0 = min(s.get("x0", float("inf")) for s in sentences)
        x1 = max(s.get("x1", float("-inf")) for s in sentences)
        top = min(s.get("top", float("inf")) for s in sentences)
        bottom = max(s.get("bottom", float("-inf")) for s in sentences)

        merged_chars = []
        for s in sentences:
            merged_chars.extend(s.get("chars", []))

        return {
            "text": merged_text,
            "x0": x0,
            "x1": x1,
            "top": top,
            "bottom": bottom,
            "height": bottom - top,
            "fontname": sentences[0].get("fontname", ""),
            "chars": merged_chars,
        }

    def _group_vertically(self, sentences, check_font=True, distance_limit_ratio=1.5):
        if not sentences:
            return [], []

        direction = self._get_sentence_direction(sentences[0]) if sentences else "ltr"
        is_vertical = self._is_vertical_direction(direction)
        if is_vertical:
            sorted_sentences = sorted(sentences, key=lambda s: self._round_to_half(s.get("x0", 0)), reverse=(direction == "reversed"))
        else:
            sorted_sentences = sorted(sentences, key=lambda s: self._round_to_half(s.get("top", 0)), reverse=(direction == "reversed"))

        used = set()
        groups = []

        for i, current in enumerate(sorted_sentences):
            if i in used:
                continue

            group = [current]
            used.add(i)

            while True:
                candidates = [
                    (j, s)
                    for j, s in enumerate(sorted_sentences)
                    if j not in used and self._is_valid_vertical_neighbor(group[-1], s, check_font, distance_limit_ratio)
                ]
                if not candidates:
                    break
                if check_font:
                    best_idx, best = self._find_best_neighbor(group[-1], candidates)
                else:
                    best_idx, best = candidates[0]
                group.append(best)
                used.add(best_idx)

            if len(group) > 1:
                groups.append(group)
            else:
                used.discard(i)

        remaining = [s for i, s in enumerate(sorted_sentences) if i not in used]
        return groups, remaining

    def _group_horizontally(self, sentences, check_font=True):
        if not sentences:
            return [], []

        direction = self._get_sentence_direction(sentences[0]) if sentences else "ltr"
        if self._is_vertical_direction(direction):
            sorted_sentences = sorted(sentences, key=lambda s: self._round_to_half(s.get("top", 0)))
        else:
            sorted_sentences = sorted(sentences, key=lambda s: self._round_to_half(s.get("x0", 0)))

        used = set()
        groups = []

        for i, current in enumerate(sorted_sentences):
            if i in used:
                continue

            group = [current]
            used.add(i)

            while True:
                candidates = [
                    (j, s)
                    for j, s in enumerate(sorted_sentences)
                    if j not in used and self._is_valid_horizontal_neighbor(group[-1], s, check_font)
                ]
                if not candidates:
                    break
                best_idx, best = self._find_best_neighbor(group[-1], candidates)
                group.append(best)
                used.add(best_idx)

            if len(group) > 1:
                groups.append(group)
            else:
                used.discard(i)

        remaining = [s for i, s in enumerate(sorted_sentences) if i not in used]
        return groups, remaining

    def _group_adjacent_horizontally(self, sentences, distance_threshold_ratio=1.1):
        if not sentences:
            return []

        sorted_sentences = sorted(
            sentences,
            key=lambda s: (self._round_to_half(s.get("top", 0)), self._round_to_half(s.get("x0", 0))),
        )
        result = []
        used = set()

        for i, current in enumerate(sorted_sentences):
            if i in used:
                continue

            current_chars = current.get("chars", [])
            if not current_chars:
                result.append(current)
                used.add(i)
                continue

            merge_group = [current]
            used.add(i)

            while True:
                last_sent = merge_group[-1]
                last_chars = last_sent.get("chars", [])
                if not last_chars:
                    break

                last_char = last_chars[-1]
                last_char_rect = self._char_to_rect(last_char)
                distance_threshold = last_char.get("height", 0) * distance_threshold_ratio
                best_idx = None
                best_distance = float("inf")

                for j, candidate in enumerate(sorted_sentences):
                    if j in used:
                        continue

                    candidate_chars = candidate.get("chars", [])
                    if not candidate_chars:
                        continue

                    first_char = candidate_chars[0]
                    first_char_rect = self._char_to_rect(first_char)
                    distance = self._calculate_rect_distance(last_char_rect, first_char_rect, use_center=True)
                    rotation = self._get_char_rotation(last_char)
                    vertical_overlap = self._calculate_overlap_with_rotation(
                        last_char_rect, first_char_rect, is_vertical_layout=False, rotation_deg=rotation
                    )
                    overlap_ratio = vertical_overlap.get("iou", 0)

                    if overlap_ratio > 0.6 and distance < distance_threshold and distance < best_distance:
                        best_distance = distance
                        best_idx = j

                if best_idx is None:
                    break

                merge_group.append(sorted_sentences[best_idx])
                used.add(best_idx)

            if len(merge_group) > 1:
                result.append(self._merge_sentence_groups(merge_group, ""))
            else:
                result.append(current)

        return result

    def _merge_words(self, words, distance_threshold_ratio=3):
        if not words:
            return []

        new_words = []

        for word in words:
            word = word.copy()
            text = word.get("text", "")

            if len(text) != 1 and len(text.strip()) > 1:
                new_words.append(word)
                continue

            if not new_words:
                new_words.append(word)
                continue

            prev_word = new_words[-1]
            prev_chars = prev_word.get("chars", [])
            if not prev_chars:
                new_words.append(word)
                continue

            direction = self._detect_text_direction(prev_chars)
            rotation = self._get_avg_rotation(prev_word)
            rect_word = (word.get("x0", 0), word.get("top", 0), word.get("x1", 0), word.get("bottom", 0))
            rect_prev = (prev_word.get("x0", 0), prev_word.get("top", 0), prev_word.get("x1", 0), prev_word.get("bottom", 0))
            overlap_info = self._calculate_overlap_with_rotation(
                rect_word,
                rect_prev,
                is_vertical_layout=self._is_vertical_direction(direction),
                rotation_deg=rotation,
            )

            if overlap_info["coverage"] < 0.4 and len(prev_word.get("text", "")) > 1:
                new_words.append(word)
                continue

            threshold = self._avg_char_height([prev_word]) * distance_threshold_ratio
            current_rect = self._word_to_rect(word)
            prev_rect = self._char_to_rect(prev_chars[-1])
            if current_rect is None or prev_rect is None:
                new_words.append(word)
                continue

            if self._calculate_rect_distance(prev_rect, current_rect) > threshold:
                new_words.append(word)
                continue

            self._insert_char_to_word(prev_word, word)

        single_char_words = []
        multi_char_words = []
        for word in new_words:
            if len(word.get("text", "")) == 1:
                single_char_words.append(word)
            else:
                multi_char_words.append(word)

        if not single_char_words or not multi_char_words:
            return new_words

        merged_single_indices = set()
        for single_idx, single_word in enumerate(single_char_words):
            single_rect = self._word_to_rect(single_word)
            if single_rect is None:
                continue

            best_match_multi_idx = None
            best_char_distance = float("inf")

            for multi_idx, multi_word in enumerate(multi_char_words):
                multi_chars = multi_word.get("chars", [])
                direction = self._detect_text_direction(multi_chars)
                threshold = self._avg_char_height([multi_word, single_word]) * distance_threshold_ratio

                for mc in multi_chars:
                    mc_rect = (mc.get("x0", 0), mc.get("top", 0), mc.get("x1", 0), mc.get("bottom", 0))
                    rotation = self._get_char_rotation(mc)
                    overlap_info = self._calculate_overlap_with_rotation(
                        single_rect,
                        mc_rect,
                        is_vertical_layout=self._is_vertical_direction(direction),
                        rotation_deg=rotation,
                    )

                    if overlap_info["coverage"] < 0.7 or overlap_info["iou"] < 0.5:
                        continue

                    char_distance = self._calculate_rect_distance(single_rect, mc_rect, False)
                    if char_distance <= threshold and char_distance < best_char_distance:
                        best_char_distance = char_distance
                        best_match_multi_idx = multi_idx

            if best_match_multi_idx is not None:
                self._insert_char_to_word(multi_char_words[best_match_multi_idx], single_word)
                merged_single_indices.add(single_idx)

        result_words = multi_char_words.copy()
        for i, single_word in enumerate(single_char_words):
            if i not in merged_single_indices:
                result_words.append(single_word)
        return result_words

    def _group_sentences(self, words, distance_threshold_ratio=3):
        if not words:
            return []

        threshold = self._avg_char_height(words) * distance_threshold_ratio
        word_rects = []
        idx_to_word = {}

        for idx, word in enumerate(words):
            rect = self._word_to_rect(word)
            if rect is None:
                continue
            word_rects.append((idx, rect))
            idx_to_word[idx] = word

        if not word_rects:
            return []

        graph = nx.Graph()
        for idx, rect in word_rects:
            graph.add_node(idx, rect=rect)

        num = len(word_rects)
        for i in range(num):
            idx1, rect1 = word_rects[i]
            for j in range(i + 1, num):
                idx2, rect2 = word_rects[j]
                if self._calculate_rect_distance(rect1, rect2, use_center=False) <= threshold:
                    graph.add_edge(idx1, idx2)

        groups = list(nx.connected_components(graph))
        return [
            [idx_to_word[idx] for idx in group if idx in idx_to_word]
            for group in groups
            if group
        ]

    def _build_sentence_groups_from_group(self, group):
        if not group:
            return []

        adjacent_merged = self._group_adjacent_horizontally(group)
        vertical_groups, remaining_after_vertical = self._group_vertically(
            adjacent_merged, check_font=True, distance_limit_ratio=1.5
        )
        vertical_merged = [self._merge_sentence_groups(g, "") for g in vertical_groups]

        horizontal_groups, remaining_after_horizontal = self._group_horizontally(
            remaining_after_vertical, check_font=True
        )
        horizontal_merged = [self._merge_sentence_groups(g, " ") for g in horizontal_groups]

        all_sentences = vertical_merged + horizontal_merged + remaining_after_horizontal
        if not all_sentences:
            return []

        all_sentences.sort(key=lambda s: (self._round_to_half(s.get("top", 0)), self._round_to_half(s.get("x0", 0))))
        final_groups, final_remaining = self._group_vertically(
            all_sentences, check_font=False, distance_limit_ratio=2.5
        )

        merged_sentences = []
        for current_group in final_groups:
            merged = self._merge_sentence_groups(current_group, "\n")
            if merged.get("text"):
                merged_sentences.append(merged)

        for sentence in final_remaining:
            if sentence.get("text"):
                merged_sentences.append(sentence)

        merged_sentences.sort(key=lambda s: (s.get("top", 0), s.get("x0", 0)))
        return merged_sentences
