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
    screen = UIScreen(ui, background=color565(255, 255, 255), taskbarcolor=color565(128, 0, 64), taskbar_text='ZenStore', taskbar_text_color=color565(255, 255, 255), on_exit=on_exit)

    screen.start(ui)

    # Draw layers (colored rectangles)
    screen.layer(1, 37, 317, 17, color565(80, 80, 80))
    screen.layer(1, 55, 318, 37, color565(192, 192, 192))
    screen.layer(1, 93, 318, 146, color565(229, 229, 229))
    screen.layer(3, 95, 313, 70, color565(190, 190, 190))
    screen.layer(3, 166, 314, 70, color565(193, 193, 193))

    # Create and draw buttons
    buttons = []
    def on_button_click():
        print('Button Install pressed')

    buttons.append(UIButton(3, 58, 100, 30, label='Install', color=color565(224, 224, 224), text_color=color565(0, 0, 0), margin=5, action=on_button_click))
    buttons.append(UIButton(107, 58, 100, 30, label='Uninstall', color=color565(223, 223, 223), text_color=color565(0, 0, 0), margin=5, action=on_button_click))
    buttons.append(UIButton(211, 58, 105, 30, label='Search', color=color565(223, 223, 223), text_color=color565(0, 0, 0), margin=5, action=on_button_click))

    for btn in buttons:
        btn.draw(ui)

    ui.fade_in(fade_time=0.4)

    while True:
        # Handle button touches
        for btn in buttons:
            btn.get_touch(ui)
        time.sleep(0.05)


main()