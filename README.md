# FATE Fishing Bot Engine

A fully automated, state-machine driven fishing bot for the RPG game **FATE**. 
This engine has been completely decoupled to prevent CPU exhaustion and softlocks, featuring a highly-optimized bounded-region vision algorithm that eliminates false positives.

## Action Showcase
<video src="./assets/4ux3sp_1.mp4" autoplay loop muted playsinline></video>

## Requirements & Dependencies

The bot is written in Python 3. Install the required dependencies using the `requirements.txt` file:

```bash
pip install -r requirements.txt
```

## Game Settings & Calibration

The bot operates optimally when the game is set to **Window Mode** with a resolution of **1920x1080**.

Open your FATE `config.dat` file and ensure the following values are set:
```ini
SCREENWIDTH: 1920
SCREENHEIGHT: 1080
FULLSCREEN: 0
VSYNC: 0
1920x1080: 1
FOV: 70
```

### Custom Assets

Due to how the FATE engine scales and renders UI elements based on resolution, the bot requires you to take two custom cropped screenshots of your specific game:

1. **`assets/exclamation_mark.PNG`**: Use the Windows Snipping tool to crop a tight box around the yellow exclamation point that pops up when a fish bites.
2. **`assets/stop_fishing_button.png`**: Crop a tight box around the "Stop Fishing" button text. This allows the bot to cleanly cancel and recast if a fish is missed.

## Architecture

The bot uses a **Finite State Machine** (`fishing_bot.py`) to manage fishing loops safely:
- **`SETUP`**: Automatically finds the game, closes pause menus, opens the inventory, and calculates the exact fishing spot offset based on `bot_config.json`.
- **`FISHING_CAST`**: Casts the line.
- **`FISHING_WAIT`**: Calculates a tightly-bounded 250x600 pixel search region directly above the "Set Hook!" button. It scans exclusively inside this box for your custom `exclamation_mark.PNG`. By limiting the search area, false positives are completely eliminated.
- **`FISHING_HOOK`**: Clicks the "Set Hook!" button and waits for the reeling animation.

## Usage

1. Open FATE and walk your character to the edge of the dock.
2. Open a terminal in the bot directory.
3. Run the bot:
   ```bash
   python fishing_bot.py
   ```
4. You have **5 seconds** to alt-tab back into the game window. Do not touch your mouse once the bot begins its setup phase!

## Debugging Tools

If the bot is failing to detect the hook or the exclamation point, use the bundled `debug_vision.py` script to visually diagnose what the bot sees:

- `python debug_vision.py --live`: Opens a live OpenCV video feed showing bounded boxes around detections in real-time.
- `python debug_vision.py --fishspot`: Automates the `SETUP` phase and draws a red crosshair showing exactly where the bot intends to click the water.
- `python debug_vision.py --dry-exclregion`: Automates a cast, then saves 10 screenshots of the exact 250x600 bounded region it is searching for the exclamation point, proving whether or not the UI fits inside the box.
