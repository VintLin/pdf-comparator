import os
import shutil
import imutils
import cv2
import numpy as np
import logging

from PIL import Image, ImageDraw, ImageFont
from skimage.metrics import structural_similarity as compare_ssim

from pdfcomparator._pdf_file import PDFFile
from pdfcomparator._compare_image import ImageHandler
from pdfcomparator._compare_char import compare_page_text

def compare_pdf(a_pdf, b_pdf, output_folder, compare_image=True, compare_text=True):
    if not compare_image and not compare_text:
        return
    
    options = CompareOptions(a_pdf, b_pdf, output_folder, is_compare_image=compare_image, is_compare_text=compare_text)

    a = PDFFile(a_pdf)
    b = PDFFile(b_pdf)
    
    a_images = a.to_images(os.path.join(options.cache_path, "LeftImage"), True)
    b_images = b.to_images(os.path.join(options.cache_path, "RightImage"), True)
    
    match_pages = PDFFile.get_match_pages_by_image(a_images, b_images)
    
    for indexs in match_pages:
        options.set_current_page(a_images[indexs[0]], indexs[0] + 1, b_images[indexs[1]], indexs[1] + 1, indexs[2])        
        origin_path = os.path.join(options.origin_path, options.page_name)
        compare_path = os.path.join(options.compare_path, options.page_name)
        if compare_text:
            text_diffs = compare_page_text(a.get_page(indexs[0]), b.get_page(indexs[1]))
            options.set_compare_text(
                a.page_width,
                a.page_height,
                PDFFile.extract_words(text_diffs[0]), 
                PDFFile.extract_words(text_diffs[1]),
                )
        _compare(origin_path, compare_path, options)
    
    if os.path.exists(options.cache_path):
        shutil.rmtree(options.cache_path)

class CompareOptions:
    def __init__(self, a_path, b_path, output_folder, is_compare_image=False, is_compare_text=False) -> None:
        self.a_pdf_path = a_path
        self.b_pdf_path = b_path
        self.output_folder = output_folder
        self.is_compare_image = is_compare_image
        self.is_compare_text = is_compare_text
        
        self.cache_path = self._init_folder(os.path.join(output_folder, "Cache"))
        self.origin_path = self._init_folder(os.path.join(output_folder, "OriginImages"))
        self.compare_path = self._init_folder(os.path.join(output_folder, "CompareResult"))
    
    def set_current_page(self, a_image, a_page_index, b_image, b_page_index, diff_rate):
        self.a_image_path = a_image
        self.a_page_index = a_page_index
        self.b_image_path = b_image
        self.b_page_index = b_page_index
        self.diff_rate = diff_rate
        self.suffix = os.path.splitext(a_image)[1]
        rate = "[{:.2f}%]".format(diff_rate * 100)
        if diff_rate == 1:
            rate = "[SAME]"
        elif rate == "[100.00%]":
            rate = "[99.99%]"
        self.page_name = f"Page{a_page_index}_vs_Page{b_page_index}{rate}"
        
    def set_compare_text(self, pdf_width, pdf_height, a_text_diffs, b_text_diffs):
        self.pdf_width = pdf_width
        self.pdf_height = pdf_height
        self.a_text_diffs = a_text_diffs
        self.b_text_diffs = b_text_diffs
        return self
    
    def _init_folder(self, folder):
        if os.path.exists(folder):
            shutil.rmtree(folder)
        os.makedirs(folder, exist_ok=True)
        return folder

def _compare(origin_path, compare_path, options: CompareOptions):
    os.makedirs(origin_path, exist_ok=True)
    a_path = os.path.join(origin_path, "OriginImage(Left)" + options.suffix)
    b_path = os.path.join(origin_path, "OriginImage(Right)" + options.suffix)
    resize_path = os.path.join(origin_path, "ResizeImage(Right)" + options.suffix)
    quick_path = compare_path + options.suffix
    
    a_image = ImageHandler.read_image(options.a_image_path)
    b_image = ImageHandler.read_image(options.b_image_path)
    ImageHandler.save_image(a_path, a_image)
    ImageHandler.save_image(b_path, b_image)
    
    real_resize_path = ImageHandler.check_image_resize(options.b_image_path, options.a_image_path, resize_path)
    if real_resize_path == resize_path:
        b_image = ImageHandler.read_image(resize_path)
    
    if options.is_compare_text:
        a_text_image = _draw_text_image(a_image.copy(), options.pdf_width, options.pdf_height, options.a_text_diffs)
        b_text_image = _draw_text_image(b_image.copy(), options.pdf_width, options.pdf_height, options.b_text_diffs)
    
    if options.is_compare_image and options.is_compare_text:
        output_image = _compare_image(a_image, b_image, a_text_image, b_text_image, options)
    elif options.is_compare_image:
        output_image = _compare_image(a_image, b_image, None, None, options)
    elif options.is_compare_text:
        output_image = _compare_image(None, None, a_text_image, b_text_image, options)
    # save image
    ImageHandler.save_image(quick_path, output_image)

def _draw_text_image(image, pdf_width, pdf_height, words_group):
    img_height, img_width = image.shape[:2]
    alpha = 0.6  
    x_scale = img_width / pdf_width
    y_scale = img_height / pdf_height
    for index, words in enumerate(words_group):
        if index == 0:
            color = (0, 255, 0) # Same (Green)
        elif index == 1:
            color = (255, 105, 180) # Font Size (Blue)
        elif index == 2:
            color = (0, 165, 230) # Font Color (Yellow)
        elif index == 3:
            color = (200, 0, 200) # Font Size / Font Color (Purple)
        else:
            color = (0, 0, 255) # Different (Red)
        for word in words:
            x0, y0, x1, y1 = word["x0"], word["top"], word["x1"], word["bottom"]
            top_left = (int(x0 * x_scale), int(y1 * y_scale))
            bottom_right = (int(x1 * x_scale), int(y0 * y_scale))
            draw_image = image.copy()
            cv2.rectangle(draw_image, top_left, bottom_right, color, -1) 
            image = cv2.addWeighted(draw_image, alpha, image, 1 - alpha, 0)
            cv2.rectangle(image, top_left, bottom_right, color, 2)
    return image
    
def _compare_image(a_image=None, b_image=None, a_text_image=None, b_text_image=None, options:CompareOptions=None):
    is_compare_text = False
    is_compare_image = False
    mask = a_image.copy()
    h, w = -1, -1
    if a_image is not None and b_image is not None:
        is_compare_image = True
        a_gray = cv2.cvtColor(a_image, cv2.COLOR_BGR2GRAY)
        b_gray = cv2.cvtColor(b_image, cv2.COLOR_BGR2GRAY)
        
        (score, diff) = compare_ssim(a_gray, b_gray, full=True)
        diff = (diff * 255).astype("uint8")
        thresh = cv2.threshold(diff, 0, 255, cv2.THRESH_BINARY_INV | cv2.THRESH_OTSU)[1]
        kernel = np.ones((3,3), np.uint8)
        dilated = cv2.dilate(thresh, kernel, iterations=2)
        cnts = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        cnts = imutils.grab_contours(cnts)
        for c in cnts:
            cv2.fillPoly(mask, [c], (0, 0, 255))
        
        transparency = 0.6
        cv2.addWeighted(mask, transparency, a_image, 1 - transparency, 0, a_image)
        cv2.addWeighted(mask, transparency, b_image, 1 - transparency, 0, b_image)
        
        h = min(a_image.shape[0], b_image.shape[0], diff.shape[0], thresh.shape[0])
        w = min(a_image.shape[1], b_image.shape[1], diff.shape[1], thresh.shape[1])
        a_image = cv2.resize(a_image, (w, h))
        b_image = cv2.resize(b_image, (w, h))
        diff = cv2.resize(diff, (w, h))
        thresh = cv2.resize(thresh, (w, h))
    
    if a_text_image is not None and b_text_image is not None:
        is_compare_text = True
        if h == -1 or w == -1:
            h = min(a_text_image.shape[0], b_text_image.shape[0])
            w = min(a_text_image.shape[1], b_text_image.shape[1])
        a_text_image = cv2.resize(a_text_image, (w, h))
        b_text_image = cv2.resize(b_text_image, (w, h))

    if len(diff.shape) == 2:
        diff = cv2.cvtColor(diff, cv2.COLOR_GRAY2BGR)
    if len(thresh.shape) == 2:
        thresh = cv2.cvtColor(thresh, cv2.COLOR_GRAY2BGR)
    
    result = None
    if is_compare_image and is_compare_text:
        a_text_image = _draw_path(options.a_pdf_path, options.a_page_index, a_text_image)
        b_text_image = _draw_path(options.b_pdf_path, options.b_page_index, b_text_image)
        upper = np.hstack((a_text_image, b_text_image))  
        middle = np.hstack((a_image, b_image))  
        lower = np.hstack((diff, thresh))  
        result = np.vstack((upper, middle))  
        result = np.vstack((result, lower)) 
    elif is_compare_image:
        a_image = _draw_path(options.a_pdf_path, options.a_page_index, a_image)
        b_image = _draw_path(options.b_pdf_path, options.b_page_index,  b_image)
        upper = np.hstack((a_image, b_image))
        lower = np.hstack((diff, thresh))
        result = np.vstack((upper, lower))
    elif is_compare_text:
        a_text_image = _draw_path(options.a_pdf_path, options.a_page_index, a_text_image)
        b_text_image = _draw_path(options.b_pdf_path, options.b_page_index, b_text_image)
        result = np.hstack((a_text_image, b_text_image))
    return result


def _draw_path(path, index, image):
    try:
        path = path.strip().replace("//", "\\").replace("\\\\", "\\").replace("/", "\\")
        path = f"Path: \"{path}\" Current Page: \"{index}\""
        image_convert = Image.fromarray(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
        draw = ImageDraw.Draw(image_convert)
        
        color = (255, 0, 0)  # Red
        padding = 10
        
        try:
            max_width = (image_convert.width - 2 * padding) * 3 / 4
            font_path= "msyh.ttf"
            font_size = 30
            font = ImageFont.truetype(font_path, font_size)
            while font.getlength(path) > max_width:
                font_size -= 2
                font = ImageFont.truetype(font_path, font_size)
        except:
            font = ImageFont.load_default()
        logging.debug(f"font path: {font_path}, index {index}")
        draw.text((padding, padding), path, font=font, fill=color)
        image = cv2.cvtColor(np.array(image_convert), cv2.COLOR_RGB2BGR)
        return image
    except:
        return image