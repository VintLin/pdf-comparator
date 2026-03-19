import os
import gc
import logging
import cv2
import shutil
import numpy as np
import pdfplumber.utils as pdf_utils

from pdfcomparator._pdf_handler import PDFHandler
from pdfcomparator._utils_for_compare import CompareUtils, CharInfo
from pdfcomparator._utils_for_image import ImageUtils

logger = logging.getLogger(__name__)


OVERLAY_STYLES = {
    CharInfo.STATE_SAME: {
        "fill": (80, 220, 120),
        "fill_alpha": 0.28,
        "stroke": (80, 220, 120),
        "stroke_alpha": 0.85,
    },
    CharInfo.STATE_SIZE_COLOR_DIFF: {
        "fill": (255, 200, 80),
        "fill_alpha": 0.3,
        "stroke": (255, 200, 80),
        "stroke_alpha": 0.85,
    },
    CharInfo.STATE_DIFF: {
        "fill": (255, 70, 70),
        "fill_alpha": 0.32,
        "stroke": (255, 70, 70),
        "stroke_alpha": 0.9,
    },
}

def compare_pdf(a_path, b_path, save_folder):
    logger.info("Starting PDF comparison: %s vs %s", a_path, b_path)
    cache_folder, origin_folder, result_folder = init_folder(save_folder)
    a_pdf = PDFHandler(a_path).load()
    b_pdf = PDFHandler(b_path).load()
    a_images = a_pdf.to_images(os.path.join(cache_folder, "left_image"))
    b_images = b_pdf.to_images(os.path.join(cache_folder, "right_image"))
    match_infos = CompareUtils.compare_pdf_by_image(a_images, b_images, a_pdf.is_large())
    logger.info("Matched %s page pairs", len(match_infos))

    for a_index, b_index, similarity in match_infos:
        file_name = get_file_name(a_index, b_index, similarity)
        origin_path = os.path.join(origin_folder, file_name)
        result_path = os.path.join(result_folder, file_name + ".jpg")
        a_image, b_image = save_origin_image(a_images[a_index], b_images[b_index], origin_path)
        a_text_image, b_text_image = get_text_images(a_index, a_pdf, a_image.copy(), b_index, b_pdf, b_image.copy())
        output_image = merge_image(a_image, b_image, a_text_image, b_text_image)
        ImageUtils.save_image(result_path, output_image)
        logger.info("Wrote comparison image: %s", result_path)

        del a_image, b_image, a_text_image, b_text_image, output_image
        gc.collect()

    del a_pdf, b_pdf
    
    if os.path.exists(cache_folder):
        shutil.rmtree(cache_folder)
    logger.info("Finished PDF comparison. Output folder: %s", save_folder)

def init_folder(folder):
    # check file is exists
    if os.path.exists(folder):
        shutil.rmtree(folder)
    
    cache_folder = os.path.join(folder, "Cache")
    origin_folder = os.path.join(folder, "OriginImages")
    result_folder = os.path.join(folder, "CompareResult")

    os.makedirs(folder, exist_ok=True)
    os.makedirs(cache_folder, exist_ok=True)
    os.makedirs(origin_folder, exist_ok=True)
    os.makedirs(result_folder, exist_ok=True)
    return cache_folder, origin_folder, result_folder

def get_file_name(a_index, b_index, similarity):
    str_suffix = "【{:.2f}%】".format(similarity * 100)
    if similarity == 1:
        str_suffix = "【SAME】"
    elif str_suffix == "【100.00%】":
        str_suffix = "【99.99%】"
    return f"Page{a_index + 1}_vs_Page{b_index + 1}{str_suffix}"

def save_origin_image(a_image_path, b_image_path, origin_folder):
    os.makedirs(origin_folder, exist_ok=True)
    
    a_path = os.path.join(origin_folder, "LeftOriginalImage.jpg")
    b_path = os.path.join(origin_folder, "RightOriginalImage.jpg")
    resize_path = os.path.join(origin_folder, "ResizedImage(Right).jpg")

    a_image = ImageUtils.read_image(a_image_path)
    b_image = ImageUtils.read_image(b_image_path)
    ImageUtils.save_image(a_path, a_image)
    ImageUtils.save_image(b_path, b_image)
    
    if ImageUtils.check_image_resize(a_image, b_image, resize_path):
        b_image = ImageUtils.read_image(resize_path)
    return a_image, b_image

def get_text_images(a_index, a_pdf, a_image, b_index, b_pdf, b_image):
    text_diffs = CompareUtils.compare_pdf_by_text(a_pdf, a_index, b_pdf, b_index)
    a_text_image = get_text_image(text_diffs[0], a_image.copy(), a_pdf.page_width, a_pdf.page_height)
    b_text_image = get_text_image(text_diffs[1], b_image.copy(), b_pdf.page_width, b_pdf.page_height)
    return a_text_image, b_text_image
    
def get_text_image(diffs, image, width, height):
    words_group = {
        key: pdf_utils.extract_words(words)
        for key, words in diffs.items()
    }
    return _draw_diff_word(words_group, image, width, height)

def merge_image(
        a_image=None, 
        b_image=None, 
        a_text_image=None, 
        b_text_image=None, 
    ):
    if a_image is None or b_image is None or a_text_image is None or b_text_image is None:
        return None
    # Determine minimum dimensions
    h = min(a_image.shape[0], b_image.shape[0])
    w = min(a_image.shape[1], b_image.shape[1])

    # Resize images to minimum dimensions
    a_text_image = cv2.resize(a_text_image, (w, h))
    b_text_image = cv2.resize(b_text_image, (w, h))
    upper = np.hstack((a_text_image, b_text_image))
    del a_text_image, b_text_image
    
    a_image = cv2.resize(a_image, (w, h))
    b_image = cv2.resize(b_image, (w, h))
    # Calculate absolute difference between images
    abs_diff = cv2.absdiff(a_image, b_image)
    abs_diff_gray = cv2.cvtColor(abs_diff, cv2.COLOR_BGR2GRAY)
    # Threshold the difference image to get significant differences
    _, mask = cv2.threshold(abs_diff_gray, 15, 255, cv2.THRESH_BINARY)
    # Create a color mask
    a_color_mask = a_image.copy()
    b_color_mask = b_image.copy()
    a_color_mask[mask > 0] = [0, 0, 255]  # Red color
    b_color_mask[mask > 0] = [0, 0, 255]
    # Apply the mask to the original images
    a_color_mask = cv2.addWeighted(a_color_mask, 0.6, a_image, 0.4, 0)
    b_color_mask = cv2.addWeighted(b_color_mask, 0.6, b_image, 0.4, 0)
    middle = np.hstack((a_color_mask, b_color_mask))
    del mask, a_color_mask, b_color_mask
    
    abs_diff_gray_inverted = 255 - abs_diff_gray
    # Convert abs_diff_gray to a color image if you want to display it alongside the heatmap
    abs_diff_color = cv2.cvtColor(abs_diff_gray, cv2.COLOR_GRAY2BGR)
    abs_diff_color_inverted = cv2.cvtColor(abs_diff_gray_inverted, cv2.COLOR_GRAY2BGR)
    # Combine text and image comparisons
    lower = np.hstack((abs_diff_color, abs_diff_color_inverted))  # Showing grayscale and heatmap comparison
    del abs_diff_color, abs_diff_color_inverted
    
    # Stack all parts together
    result_image = np.vstack((upper, middle, lower))
    return result_image

def _draw_diff_word(words_group, image, width, height):
    img_height, img_width = image.shape[:2]

    x_scale = img_width / width
    y_scale = img_height / height

    overlay_fill = image.copy()
    overlay_stroke = image.copy()

    for key, words in words_group.items():
        style = OVERLAY_STYLES.get(key, OVERLAY_STYLES[CharInfo.STATE_DIFF])
        fill_color = style["fill"]
        stroke_color = style["stroke"]
        fill_alpha = style["fill_alpha"]
        stroke_alpha = style["stroke_alpha"]

        for word in words:
            x0 = word["x0"] * x_scale
            y0 = word["top"] * y_scale
            x1 = word["x1"] * x_scale
            y1 = word["bottom"] * y_scale

            pad_x = max(1, int(round((x1 - x0) * 0.04)))
            pad_y = max(1, int(round((y1 - y0) * 0.12)))

            left = max(0, int(round(x0)) - pad_x)
            top = max(0, int(round(y0)) - pad_y)
            right = min(img_width - 1, int(round(x1)) + pad_x)
            bottom = min(img_height - 1, int(round(y1)) + pad_y)

            if right <= left or bottom <= top:
                continue

            cv2.rectangle(
                overlay_fill,
                (left, top),
                (right, bottom),
                fill_color,
                -1,
                lineType=cv2.LINE_AA,
            )
            image = cv2.addWeighted(overlay_fill, fill_alpha, image, 1 - fill_alpha, 0)
            overlay_fill[:] = image

            cv2.rectangle(
                overlay_stroke,
                (left, top),
                (right, bottom),
                stroke_color,
                2,
                lineType=cv2.LINE_AA,
            )
            image = cv2.addWeighted(overlay_stroke, stroke_alpha, image, 1 - stroke_alpha, 0)
            overlay_stroke[:] = image

    return image
