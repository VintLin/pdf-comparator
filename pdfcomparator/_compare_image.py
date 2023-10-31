from PIL import Image
from skimage.metrics import structural_similarity as compare_ssim
import numpy as np
import cv2
import os
import logging

class ImageHandler:
    @staticmethod
    def read_image(path):
        stream = open(path, "rb")
        bytes = bytearray(stream.read())
        numpyarray = np.asarray(bytes, dtype=np.uint8)
        return cv2.imdecode(numpyarray, cv2.IMREAD_UNCHANGED)
    
    @staticmethod
    def save_image(path, image):
        file_extension = os.path.splitext(path)[1]
        cv2.imencode(file_extension, image)[1].tofile(path)
    
    @staticmethod
    def convert_from_cv2_to_image(img: np.ndarray) -> Image:
        return Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))

    @staticmethod
    def convert_from_image_to_cv2(img: Image) -> np.ndarray:
        return cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
    
    @staticmethod
    def get_image_same_rate(a_path, b_path):
        try:
            # load the two input images
            imageA = ImageHandler.read_image(a_path)
            imageB = ImageHandler.read_image(b_path)
            # convert the images to grayscale
            grayA = cv2.cvtColor(imageA, cv2.COLOR_BGR2GRAY)
            grayB = cv2.cvtColor(imageB, cv2.COLOR_BGR2GRAY)
            # compute the Structural Similarity Index (SSIM) between the two
            # images, ensuring that the difference image is returned
            score = compare_ssim(grayA, grayB)
            logging.debug(f"SSIM: {score} compare: {a_path} vs {b_path}")
            return score
        except ValueError:
            logging.debug("Not Match Size")
            return 0
    
    @staticmethod
    def check_image_resize(check_path, origin_path, output_path):
        a_image = ImageHandler.read_image(origin_path)
        b_image = ImageHandler.read_image(check_path)

        # If the sizes of the two images are the same, save the image to the output path and return
        if a_image.shape == b_image.shape:
            return check_path
        
        sift = cv2.SIFT_create(nfeatures=1000, nOctaveLayers=10, contrastThreshold=0.04, edgeThreshold=5, sigma=1.2)
        kp1, des1 = sift.detectAndCompute(a_image, None)
        kp2, des2 = sift.detectAndCompute(b_image, None)

        bf = cv2.BFMatcher(cv2.NORM_L2, crossCheck=True)
        matches = bf.match(des1, des2)

        pts1 = np.float32([kp1[m.queryIdx].pt for m in matches]).reshape(-1, 1, 2)
        pts2 = np.float32([kp2[m.trainIdx].pt for m in matches]).reshape(-1, 1, 2)

        H, mask = cv2.findHomography(pts2, pts1, cv2.RANSAC, 1)

        h, w, d = a_image.shape
        img2_transformed = cv2.warpPerspective(b_image, H, (w, h))

        ImageHandler.save_image(output_path, img2_transformed)
        return output_path