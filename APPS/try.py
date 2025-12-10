# Auto-generated Zeno UI screen
# App: try (v1.0.0) by Phoenix

import time
from ili9341 import color565
from firmware import HUIModule, UIScreen

APP_NAME    = 'try'
APP_AUTHOR  = 'Phoenix'
APP_VERSION = '1.0.0'

def main(ui=None, on_exit=None):
    # Create UI context if not provided
    if ui is None:
        ui = HUIModule()
        ui.begin()

    # Create screen
    screen = UIScreen(ui, background=color565(0, 0, 0), taskbarcolor=color565(50, 50, 50), taskbar_text='try', taskbar_text_color=color565(255, 255, 255), on_exit=on_exit)

    screen.start(ui)

    # Draw layers (colored rectangles)

    # Fade in / backlight safety
    
    ui.fade_in(fade_time=0.4)


main()