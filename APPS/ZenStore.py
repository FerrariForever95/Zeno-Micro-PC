# Auto-generated Zeno UI screen
# App: ZenStore (v1.0.0) by Phoenix

import time
from ili9341 import color565
from firmware import HUIModule, UIScreen, UIButton

APP_NAME    = 'ZenStore'
APP_AUTHOR  = 'Phoenix'
APP_VERSION = '1.0.0'

def main(ui=None, on_exit=None):
    # Create UI context if not provided
    if ui is None:
        ui = HUIModule()
        ui.begin()

    # Create screen
    screen = UIScreen(ui, background=color565(255, 255, 255), taskbarcolor=color565(131, 141, 237), taskbar_text='ZenStore', taskbar_text_color=color565(255, 255, 255), on_exit=on_exit)

    screen.start(ui)

    # Draw layers (colored rectangles)
    screen.layer(2, 37, 315, 10, color565(80, 80, 80))
    screen.layer(2, 49, 316, 38, color565(192, 192, 192))
    screen.layer(2, 88, 316, 149, color565(235, 235, 235))

    # Create and draw buttons
    buttons = []
    def on_button_click():
        print('Button Install pressed')

    buttons.append(UIButton(5, 53, 84, 30, label='Install', color=color565(223, 223, 223), text_color=color565(0, 0, 0), margin=5, action=on_button_click))
    buttons.append(UIButton(91, 53, 84, 30, label='Uninstall', color=color565(223, 223, 223), text_color=color565(0, 0, 0), margin=5, action=on_button_click))
    buttons.append(UIButton(177, 53, 137, 30, label='Search', color=color565(223, 223, 223), text_color=color565(0, 0, 0), margin=5, action=on_button_click))

    for btn in buttons:
        btn.draw(ui)

    ui.fade_in(fade_time=0.4)

    while True:
        # Handle button touches
        for btn in buttons:
            btn.get_touch(ui)
        time.sleep(0.05)


main()