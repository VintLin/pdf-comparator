import os
import gc
import cv2
import shutil
import numpy as np
import pdfplumber.utils as pdf_utils

from pdfcomparator._pdf_handler import PDFHandler
from pdfcomparator._utils_for_compare import CompareUtils, CharInfo
from pdfcomparator._utils_for_image import ImageUtils

def compare_pdf(a_path, b_path, save_folder):
    # init folder
    cache_folder, origin_folder, result_folder = init_folder(save_folder)
    # 1. init pdf file
    a_pdf = PDFHandler(a_path).load()
    b_pdf = PDFHandler(b_path).load()
    # 2. convert pdf to image and get image path
    a_images = a_pdf.to_images(os.path.join(cache_folder, "left_image"))
    b_images = b_pdf.to_images(os.path.join(cache_folder, "right_image"))
    
    # 3. get match images
    match_infos = CompareUtils.compare_pdf_by_image(a_images, b_images, a_pdf.is_large())

    # 4. compare images and save result
    for a_index, b_index, similarity in match_infos:
        # 4.1 init file path
        file_name = get_file_name(a_index, b_index, similarity)
        origin_path = os.path.join(origin_folder, file_name)
        result_path = os.path.join(result_folder, file_name + ".jpg")
        
        # 4.2 get origin image
        a_image, b_image = save_origin_image(a_images[a_index], b_images[b_index], origin_path)
        
        # 4.3 get mark diff text image
        a_text_image, b_text_image = get_text_images(a_index, a_pdf, a_image.copy(), b_index, b_pdf, b_image.copy())
        
        # 4.4 merge image and save to local
        output_image = merge_image(a_image, b_image, a_text_image, b_text_image)
        ImageUtils.save_image(result_path, output_image)

        del a_image, b_image, a_text_image, b_text_image, output_image
        gc.collect()

    del a_pdf, b_pdf
    
    if os.path.exists(cache_folder):
        shutil.rmtree(cache_folder)

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
    a_text_image = get_text_image(a_index, a_pdf.path, text_diffs[0], a_image.copy(),a_pdf.page_width, a_pdf.page_height)
    b_text_image = get_text_image(b_index, b_pdf.path, text_diffs[1], b_image.copy(), b_pdf.page_width, b_pdf.page_height)
    return a_text_image, b_text_image
    
def get_text_image(index, path, diffs, image, width, height):
    words_group = _extract_words(diffs)
    edit_image = _draw_diff_word(words_group, image, width, height)
    return edit_image

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

def _extract_words(words_group):
        extract_words = {}
        for key, words in words_group.items():
            extract_words[key] = pdf_utils.extract_words(words)
        return extract_words

def _draw_diff_word(words_group, image, width, height):
    img_height, img_width = image.shape[:2]
    alpha = 0.6  # transparence
    
    # Calculated scaling factor
    x_scale = img_width / width
    y_scale = img_height / height
    
    # Create a copy
    draw_image = image.copy()
    
    for key, words in words_group.items():
        color = CharInfo.colors.get(key, (0, 0, 255))  # Default is red
        for word in words:
            x0, y0, x1, y1 = word["x0"] * x_scale, word["top"] * y_scale, word["x1"] * x_scale, word["bottom"] * y_scale

            # Computed plot coordinates
            top_left = (int(round(x0)), int(round(y0)))
            bottom_right = (int(round(x1)), int(round(y1)))
            
            # Draw a translucent rectangle directly on the copy
            cv2.rectangle(draw_image, top_left, bottom_right, color, -1)
            
            # Draw border
            cv2.rectangle(image, top_left, bottom_right, color, 2)
    
    # Apply transparency at the end of the loop
    image = cv2.addWeighted(draw_image, alpha, image, 1 - alpha, 0)
    return image