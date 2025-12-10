# Auto-generated Zeno UI screen
# App: ZenStore (v2.3) by Phoniex

import time
from ili9341 import color565
from firmware import HUIModule, UIScreen

APP_NAME    = 'ZenStore'
APP_AUTHOR  = 'Phoniex'
APP_VERSION = '2.3'

def main(ui=None, on_exit=None):
    # Create UI context if not provided
    if ui is None:
        ui = HUIModule()
        ui.begin()

    # Create screen
    screen = UIScreen(ui, background=color565(255, 255, 255), taskbarcolor=color565(0, 0, 64), taskbar_text='ZenStore', taskbar_text_color=color565(255, 255, 255), on_exit=on_exit)

    screen.start(ui)

    # Draw layers (colored rectangles)
    screen.layer(5, 41, 310, 44, color565(203, 205, 211))
    screen.layer(5, 87, 309, 146, color565(80, 80, 80))

    # Fade in / backlight safety
    
    ui.fade_in(fade_time=0.4)


main()