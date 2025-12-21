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
    screen = UIScreen(ui, background=color565(251, 230, 221), taskbarcolor=color565(0, 0, 255), taskbar_text='trail', taskbar_text_color=color565(227, 253, 250), on_exit=on_exit)

    screen.start_withoutexit(ui)

    # Draw layers (colored rectangles)

    # Create and draw texts (UIText)
    UIText(177, 56, '', color=color565(0, 0, 0))

    # Create and draw buttons
    buttons = []
    def on_button_click():
        print('Button pingulaa pressed')

    buttons.append(UIButton(88, 83, 140, 54, label='pingulaa', color=color565(200, 50, 50), text_color=color565(255, 255, 255), margin=5, action=on_button_click))

    for btn in buttons:
        btn.draw(ui)

    ui.fade_in(fade_time=0.4)

    while True:
        # Handle button touches
        for btn in buttons:
            btn.get_touch(ui)
        time.sleep(0.05)


main()