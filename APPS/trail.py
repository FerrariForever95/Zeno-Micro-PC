# Auto-generated Zeno UI screen
# App: trail (v1.0.0) by Phoenix

import time
from ili9341 import color565
from firmware import HUIModule, UIScreen

APP_NAME    = 'trail'
APP_AUTHOR  = 'Phoenix'
APP_VERSION = '1.0.0'

def main(ui=None, on_exit=None):
    # Create UI context if not provided
    if ui is None:
        ui = HUIModule()
        ui.begin()

    # Create screen
    screen = UIScreen(ui, background=color565(255, 255, 255), taskbarcolor=color565(50, 50, 50), taskbar_text='trail', taskbar_text_color=color565(255, 255, 255), on_exit=on_exit)

    screen.start(ui)

    # Draw layers (colored rectangles)
    screen.layer(16, 54, 134, 69, color565(64, 0, 128))

    # Fade in / backlight safety
    try:
        ui.fade_in(fade_time=0.4)
    except Exception:
        try:
            ui.on()
        except Exception:
            pass

    # Keep app running (simple loop)
    while True:
        time.sleep(0.05)

if __name__ == '__main__':
    main()