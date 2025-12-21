# Auto-generated Zeno UI screen
# App: trail (v1.0.0) by Phoenix

import time
from ili9341 import color565
from firmware import HUIModule, UIScreen, UIButton, UIText

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

    # Create and draw texts (UIText)

    # Create and draw buttons
    buttons = []
    def on_button_click():
        print('Button Button 1 pressed')

    buttons.append(UIButton(119, 87, 114, 64, label='Button 1', color=color565(200, 50, 50), text_color=color565(255, 255, 255), margin=5, action=on_button_click))

    for btn in buttons:
        btn.draw(ui)

    ui.fade_in(fade_time=0.4)

    while True:
        # Handle button touches
        for btn in buttons:
            btn.get_touch(ui)
        time.sleep(0.05)


main()