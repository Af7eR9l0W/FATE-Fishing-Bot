import time
import json
import signal
from vision import VisionService
from input_handler import InputHandler

class BotState:
    IDLE = 0
    SETUP = 1
    FISHING_CAST = 2
    FISHING_WAIT = 3
    FISHING_HOOK = 4

class FateBot:
    def __init__(self, config_path="bot_config.json"):
        with open(config_path, 'r') as f:
            self.config = json.load(f)
            
        self.vision = VisionService(config_path)
        self.input = InputHandler()
        
        self.state = BotState.SETUP
        self.running = True
        self.tick_sleep = 1.0 / self.config["engine"]["tick_rate_fps"]
        
        self.fishing_spot = None
        self.hook_button_location = None
        
        self.cast_time = 0
        self.max_wait_seconds = self.config["fishing"]["max_wait_for_bite_seconds"]

    def run(self):
        print("FateBot Engine Started.")
        print("You have 5 seconds to alt-tab into the game...")
        time.sleep(5)
        while self.running:
            self.tick()
            time.sleep(self.tick_sleep)
            
    def tick(self):
        if self.state == BotState.SETUP:
            self.do_setup()
        elif self.state == BotState.FISHING_CAST:
            self.do_cast()
        elif self.state == BotState.FISHING_WAIT:
            self.do_wait()
        elif self.state == BotState.FISHING_HOOK:
            self.do_hook()
            
    def do_setup(self):
        print("Setting up... Please ensure FATE is visible.")
        
        # Find pause menu to ensure we are in-game
        pause_loc = self.vision.find_image("pause_menu.PNG", cache_key="pause_menu")
        if pause_loc:
            print("Found pause menu. Closing it.")
            self.input.double_click(pause_loc.left, pause_loc.top)
            time.sleep(1)
            
        # Ensure inventory is open
        inv_loc = self.vision.find_image("inventory.PNG", cache_key="inventory")
        if not inv_loc:
            self.input.press_key('i')
            time.sleep(1)
            
        # Find fishing spot
        if not self.fishing_spot:
            spot_helper = self.vision.find_image("fishing_spot_helper.PNG", cache_key="fishing_helper")
            if spot_helper:
                self.fishing_spot = (
                    spot_helper.left - self.config["fishing"]["spot_offset_x"],
                    spot_helper.top - self.config["fishing"]["spot_offset_y"]
                )
                print(f"Fishing spot calibrated to: {self.fishing_spot}")
            else:
                return # Wait for next tick
                
        # Find hook button (if visible, it means we are currently fishing)
        hook_loc = self.vision.find_image("set_hook_button.png", cache_key="hook_button")
        if hook_loc:
            self.hook_button_location = hook_loc
            self.state = BotState.FISHING_WAIT
            self.cast_time = time.time()
            print("Setup complete. Currently fishing.")
        else:
            self.state = BotState.FISHING_CAST
            print("Setup complete. Ready to cast.")

    def do_cast(self):
        # Validate items if they exist
        val_loc = self.vision.find_image("validate_fishing.PNG", cache_key="validate_btn")
        if val_loc:
            print("Loot collected!")
            self.input.double_click(val_loc.left, val_loc.top)
            time.sleep(1)
            
        print("Casting line...")
        self.input.double_click(self.fishing_spot[0], self.fishing_spot[1])
        self.state = BotState.FISHING_WAIT
        self.cast_time = time.time()
        time.sleep(2) # Animation delay
        
        # Cache hook button location just in case we haven't found it yet
        if not self.hook_button_location:
            hook_loc = self.vision.find_image("set_hook_button.png", cache_key="hook_button")
            if hook_loc:
                self.hook_button_location = hook_loc

    def do_wait(self):
        # Timeout check
        if time.time() - self.cast_time > self.max_wait_seconds:
            print("Fishing timeout! Missed hook or cast failed. Retrying...")
            
            # Click 'Stop Fishing' to cleanly break the animation lock
            original_conf = self.vision.confidence
            self.vision.confidence = 0.85
            stop_btn = self.vision.find_image("stop_fishing_button.png", force_color=True)
            self.vision.confidence = original_conf
            
            if stop_btn:
                print("Clicking 'Stop Fishing' button...")
                center_x = stop_btn.left + int(stop_btn.width / 2)
                center_y = stop_btn.top + int(stop_btn.height / 2)
                self.input.double_click(center_x, center_y)
                time.sleep(1.5) # Wait for animation to settle
            
            self.state = BotState.FISHING_CAST
            return

        target_btn = self.hook_button_location
        if not target_btn:
            original_conf = self.vision.confidence
            self.vision.confidence = 0.85 
            target_btn = self.vision.find_image("set_hook_button.png", cache_key="hook_button", force_color=True)
            self.vision.confidence = original_conf
            self.hook_button_location = target_btn

        search_region = None
        if target_btn:
            sx = max(0, target_btn.left - 50)
            sy = max(0, target_btn.top - 600)
            search_region = (int(sx), int(sy), target_btn.width + 100, 600)

        # 1. Check for user-cropped screenshots in assets folder using standard matching
        original_conf = self.vision.confidence
        self.vision.confidence = 0.75 # Very forgiving since region is heavily restricted
        hook_imgs = self.config["vision"]["hook_images"]
        bite_loc = self.vision.find_any_image(hook_imgs, use_fate_assets=False, region=search_region)
        self.vision.confidence = original_conf
        
        # 2. If not found, check for raw game assets WITH alpha masking
        if not bite_loc and search_region:
            original_conf = self.vision.confidence
            self.vision.confidence = 0.80 
            exclamations = self.config["vision"]["exclamation_images"]
            
            for exc in exclamations:
                path = self.vision.get_image_path(exc, use_fate_assets=True)
                res = self.vision.locate_with_cv2(path, region=search_region, confidence=self.vision.confidence)
                if res:
                    bite_loc = res
                    break
                    
            self.vision.confidence = original_conf
        
        if bite_loc:
            print("Fish biting! Hooking!")
            self.state = BotState.FISHING_HOOK
            
    def do_hook(self):
        # We MUST click the "Set Hook" button. We force color matching (no grayscale)
        # to ensure it doesn't accidentally match the "Stop Fishing" button!
        original_conf = self.vision.confidence
        self.vision.confidence = 0.85 
        
        target_btn = self.hook_button_location
        if not target_btn:
            target_btn = self.vision.find_image("set_hook_button.png", cache_key="hook_button", force_color=True)
            
        if target_btn:
            # Click the CENTER of the button, not the top-left corner
            center_x = target_btn.left + int(target_btn.width / 2)
            center_y = target_btn.top + int(target_btn.height / 2)
            self.input.double_click(center_x, center_y)
        else:
            print("Error: Could not find 'Set Hook!' button to click!")
                
        self.vision.confidence = original_conf
        
        print("Hook set. Waiting for animation...")
        time.sleep(self.config["fishing"]["hook_delay_seconds"])
        self.state = BotState.FISHING_CAST

def exit_handler(signum, frame):
    print('\nShutting down FateBot...')
    if 'bot' in globals():
        bot.running = False
    else:
        exit(1)

if __name__ == "__main__":
    signal.signal(signal.SIGINT, exit_handler)
    bot = FateBot()
    bot.run()
