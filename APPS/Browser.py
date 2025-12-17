# Auto-generated Zeno UI screen
# App: Browser (v1.0.0) by Phoenix

import time
from ili9341 import color565
from firmware import HUIModule, UIScreen, UIButton, UIText

APP_NAME    = 'Browser'
APP_AUTHOR  = 'Phoenix'
APP_VERSION = '1.0.0'

def main(ui=None, on_exit=None):
    # Create UI context if not provided
    if ui is None:
        ui = HUIModule()
        ui.begin()

    # Create screen
    screen = UIScreen(ui, background=color565(191, 191, 191), taskbarcolor=color565(95, 36, 5), taskbar_text='Browser', taskbar_text_color=color565(255, 255, 255), on_exit=on_exit)

    screen.start(ui)

    # Draw layers (colored rectangles)
    screen.layer(3, 39, 313, 39, color565(255, 255, 255))
    screen.layer(7, 43, 248, 31, color565(219, 219, 219))
    screen.layer(4, 81, 311, 153, color565(207, 207, 207))

    # Create and draw texts (UIText)

    # Create and draw buttons
    buttons = []
    def on_button_click():
        print('Button Search pressed')

    buttons.append(UIButton(258, 44, 53, 29, label='Search', color=color565(98, 98, 255), text_color=color565(255, 255, 255), margin=5, action=on_button_click))

    for btn in buttons:
        btn.draw(ui)

    ui.fade_in(fade_time=0.4)

    while True:
        # Handle button touches
        for btn in buttons:
            btn.get_touch(ui)
        time.sleep(0.05)


main()