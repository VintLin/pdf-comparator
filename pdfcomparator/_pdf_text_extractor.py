from pdfcomparator._pdf_text_grouping import PDFTextGrouping


class PDFTextExtractor(PDFTextGrouping):
    def extract_page_char_groups(self, page):
        words = page.dedupe_chars().extract_words(
            x_tolerance_ratio=2,
            y_tolerance=10,
            return_chars=True,
            keep_blank_chars=True,
            use_text_flow=True,
            extra_attrs=["fontname"],
        ) or []
        if not words:
            return []

        sentences = self._merge_words(words)
        sentence_groups = self._group_sentences(sentences) or []
        if not sentence_groups:
            return []

        paragraphs = []
        for group in sentence_groups:
            merged_sentences = self._build_sentence_groups_from_group(group)
            if not merged_sentences:
                continue
            top = min(float(s.get("top", 0) or 0) for s in merged_sentences)
            x0 = min(float(s.get("x0", 0) or 0) for s in merged_sentences)
            paragraphs.append((top, x0, merged_sentences))

        paragraphs.sort(key=lambda item: (self._round_to_half(item[0]), self._round_to_half(item[1])))

        char_groups = []
        for _, _, sentences in paragraphs:
            for sentence in sentences:
                chars = self._sorted_chars(sentence.get("chars", []))
                if chars:
                    char_groups.append(chars)
        return char_groups
