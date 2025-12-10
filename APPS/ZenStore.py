# Auto-generated Zeno UI screen
# App: ZenStore (v1.0.0) by Phoenix

import time
from ili9341 import color565
from firmware import HUIModule, UIScreen

APP_NAME    = 'ZenStore'
APP_AUTHOR  = 'Phoenix'
APP_VERSION = '1.0.0'

def main(ui=None, on_exit=None):
    # Create UI context if not provided
    if ui is None:
        ui = HUIModule()
        ui.begin()

    # Create screen
    screen = UIScreen(ui, background=color565(255, 255, 255), taskbarcolor=color565(64, 0, 128), taskbar_text='ZenStore', taskbar_text_color=color565(255, 255, 255), on_exit=on_exit)

    screen.start(ui)

    # Draw layers (colored rectangles)
    screen.layer(2, 39, 316, 25, color565(225, 225, 225))
    screen.layer(2, 66, 316, 171, color565(202, 202, 202))
    screen.layer(5, 101, 310, 133, color565(216, 216, 216))

    # Fade in / backlight safety
    ui.fade_in(fade_time=0.4)


main()