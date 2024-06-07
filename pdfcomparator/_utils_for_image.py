from skimage.metrics import structural_similarity
import numpy as np
import cv2
import os
import gc
import logging

class ImageUtils:
    @staticmethod
    def read_image(path):
        try:
            with open(path, "rb") as file:
                bytes = file.read()
                np_array = np.frombuffer(bytes, dtype=np.uint8)
            return cv2.imdecode(np_array, cv2.IMREAD_UNCHANGED)
        except Exception as e:
            # Handle exceptions for debugging and error tracing
            print(f"Failed to read image due to: {e}")
            return None
    
    @staticmethod
    def save_image(path, image):
        file_extension = os.path.splitext(path)[1]
        cv2.imencode(file_extension, image)[1].tofile(path)
    
    @staticmethod
    def get_similarity(a_path, b_path):
        try:
            # load the two input images
            imageA = ImageUtils.read_image(a_path)
            imageB = ImageUtils.read_image(b_path)
            
            # Resize images to reduce computation
            scale_factor = 0.7  # Example scale factor
            width = int(imageA.shape[1] * scale_factor)
            height = int(imageA.shape[0] * scale_factor)
            dim = (width, height)
            
            resizedA = cv2.resize(imageA, dim, interpolation=cv2.INTER_AREA)
            resizedB = cv2.resize(imageB, dim, interpolation=cv2.INTER_AREA)
            del imageA, imageB
            
            score, _ = structural_similarity(resizedA, resizedB, channel_axis=2, full=True)  # multichannel 参数允许处理彩色图像
            
            logging.debug(f"SSIM: {score} compare: {a_path} vs {b_path}")
            print(f"SSIM: {score} compare: {a_path} vs {b_path}")
            return score
        except Exception as e:
            # Handle exceptions for debugging and error tracing
            print(f"Failed to get_image_same_rate to: {e}")
            return 0
        finally:
            gc.collect()
    
    @staticmethod
    def check_image_resize(a_image, b_image, resize_path):
        # If the sizes of the two images are the same, save the image to the output path and return
        if a_image.shape == b_image.shape:
            return False
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

        ImageUtils.save_image(resize_path, img2_transformed)
        return True