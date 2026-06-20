import pyautogui
import os
import json
import cv2
import numpy as np
from PIL import ImageGrab

class VisionService:
    """
    Abstracts computer vision tasks and image recognition.
    """
    def __init__(self, config_path="bot_config.json"):
        with open(config_path, 'r') as f:
            self.config = json.load(f)["vision"]
        
        self.base_dir = os.path.dirname(os.path.abspath(__file__))
        self.assets_dir = os.path.join(self.base_dir, self.config["assets_folder"])
        self.fate_assets_dir = os.path.join(self.base_dir, self.config["fate_assets_folder"])
        
        self.confidence = self.config["confidence_threshold"]
        self.grayscale = self.config["grayscale"]
        
        self.cached_regions = {}

    def get_image_path(self, filename, use_fate_assets=False):
        if use_fate_assets:
            return os.path.join(self.fate_assets_dir, filename)
        return os.path.join(self.assets_dir, filename)

    def locate_with_cv2(self, template_path, region=None, confidence=0.8):
        """
        Custom locator using OpenCV that properly handles alpha channels (transparency mask).
        """
        # Take screenshot of the region or full screen
        if region:
            screen = ImageGrab.grab(bbox=(region[0], region[1], region[0]+region[2], region[1]+region[3]))
        else:
            screen = ImageGrab.grab()
            
        screen_cv = cv2.cvtColor(np.array(screen), cv2.COLOR_RGB2BGR)
        
        # Load template with alpha channel
        template_bgra = cv2.imread(template_path, cv2.IMREAD_UNCHANGED)
        
        if template_bgra is None:
            return None

        # Check if template has an alpha channel
        if template_bgra.shape[2] == 4:
            template = template_bgra[:, :, :3]
            alpha = template_bgra[:, :, 3]
            # Use TM_CCORR_NORMED which supports masking
            result = cv2.matchTemplate(screen_cv, template, cv2.TM_CCORR_NORMED, mask=alpha)
        else:
            # No alpha channel, use standard matching
            template = template_bgra
            result = cv2.matchTemplate(screen_cv, template, cv2.TM_CCOEFF_NORMED)
            
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
        
        if max_val >= confidence:
            h, w = template.shape[:2]
            left, top = max_loc
            if region:
                left += region[0]
                top += region[1]
                
            # Return a generic object mimicking pyautogui's Box
            class Box:
                def __init__(self, l, t, w, h):
                    self.left = l
                    self.top = t
                    self.width = w
                    self.height = h
            return Box(left, top, w, h)
            
        return None

    def find_image(self, filename, use_fate_assets=False, cache_key=None, use_cache=True, use_masking=False, force_color=False, region=None):
        """
        Attempts to locate an image on screen.
        If use_masking is True, uses the custom OpenCV implementation.
        """
        path = self.get_image_path(filename, use_fate_assets)
        
        try:
            search_region = region
            if cache_key and use_cache and cache_key in self.cached_regions:
                search_region = self.cached_regions[cache_key]
                
            if use_masking:
                location = self.locate_with_cv2(path, region=search_region, confidence=self.confidence)
            else:
                gray = False if force_color else self.grayscale
                if search_region:
                    location = pyautogui.locateOnScreen(path, region=search_region, grayscale=gray, confidence=self.confidence)
                else:
                    location = pyautogui.locateOnScreen(path, grayscale=gray, confidence=self.confidence)
                
            if location and cache_key and not (cache_key in self.cached_regions):
                self.cached_regions[cache_key] = (
                    max(0, location.left - 10), 
                    max(0, location.top - 10), 
                    location.width + 20, 
                    location.height + 20
                )
            return location
        except pyautogui.ImageNotFoundException:
            return None
        except Exception as e:
            print(f"Vision error locating {filename}: {e}")
            return None

    def find_any_image(self, filenames, use_fate_assets=False, use_masking=False, region=None):
        for filename in filenames:
            location = self.find_image(filename, use_fate_assets=use_fate_assets, use_masking=use_masking, region=region)
            if location:
                return location
        return None
