import pydirectinput
import time

class InputHandler:
    """
    Handles all direct input to the game window.
    Wraps pydirectinput to ensure consistent delays and handling
    of DirectX input events.
    """
    
    @staticmethod
    def click(x, y, clicks=1, interval=0.1):
        """
        Sends a mouse click (or multiple clicks) to specific coordinates.
        Uses pydirectinput to ensure the game registers it properly.
        """
        pydirectinput.click(x=x, y=y, clicks=clicks, interval=interval)

    @staticmethod
    def double_click(x, y):
        """
        Helper for double clicking, common for FATE interactions.
        """
        InputHandler.click(x, y, clicks=2, interval=0.1)

    @staticmethod
    def press_key(key):
        """
        Presses a keyboard key.
        """
        pydirectinput.press(key)
