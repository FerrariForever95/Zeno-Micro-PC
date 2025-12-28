# Auto-generated Zeno UI screen
# App: Settings (v1.0.0) by Phoenix

import time
from ili9341 import color565
from firmware import HUIModule, UIScreen, UIButton, UIText

APP_NAME    = 'Settings'
APP_AUTHOR  = 'Phoenix'
APP_VERSION = '1.0.0'

def main(ui=None, on_exit=None):
    # Create UI context if not provided
    if ui is None:
        ui = HUIModule()
        ui.begin()

    # Create screen
    screen = UIScreen(ui, background=color565(255, 255, 255), taskbarcolor=color565(172, 87, 87), taskbar_text='Settings', taskbar_text_color=color565(255, 255, 255), on_exit=on_exit)

    screen.start(ui)

    # Draw layers (colored rectangles)
    screen.layer(2, 38, 316, 27, color565(138, 138, 138))
    screen.layer(5, 41, 256, 20, color565(238, 238, 238))
    screen.layer(2, 66, 316, 171, color565(154, 154, 154))

    # Create and draw texts (UIText)
    UIText(134, 49, 'Search any Settings', color=color565(64, 0, 64)).draw(ui)

    # Create and draw buttons
    buttons = []
    def on_button_click():
        print('Button Search pressed')

    buttons.append(UIButton(264, 41, 51, 20, label='Search', color=color565(219, 219, 219), text_color=color565(64, 0, 64), margin=5, action=on_button_click))
    buttons.append(UIButton(5, 69, 310, 16, label='Wi-Fi and Internet', color=color565(199, 199, 199), text_color=color565(2, 2, 2), margin=5, action=on_button_click))
    buttons.append(UIButton(5, 103, 310, 16, label='Display and Brightness', color=color565(202, 202, 202), text_color=color565(6, 6, 6), margin=5, action=on_button_click))
    buttons.append(UIButton(5, 86, 310, 16, label='Bluetooth Connections', color=color565(202, 202, 202), text_color=color565(64, 0, 64), margin=5, action=on_button_click))
    buttons.append(UIButton(5, 120, 310, 16, label='Storage', color=color565(202, 202, 202), text_color=color565(64, 0, 64), margin=5, action=on_button_click))
    buttons.append(UIButton(5, 137, 310, 16, label='Security', color=color565(202, 202, 202), text_color=color565(64, 0, 64), margin=5, action=on_button_click))
    buttons.append(UIButton(5, 154, 310, 16, label='System Performance', color=color565(202, 202, 202), text_color=color565(64, 0, 64), margin=5, action=on_button_click))
    buttons.append(UIButton(5, 171, 310, 16, label='System Updates', color=color565(202, 202, 202), text_color=color565(64, 0, 64), margin=5, action=on_button_click))
    buttons.append(UIButton(5, 188, 310, 16, label='Devloper Options', color=color565(202, 202, 202), text_color=color565(64, 0, 64), margin=5, action=on_button_click))
    buttons.append(UIButton(5, 205, 310, 30, label='About Device', color=color565(202, 202, 202), text_color=color565(64, 0, 64), margin=5, action=on_button_click))

    for btn in buttons:
        btn.draw(ui)

    ui.fade_in(fade_time=0.4)

    while True:
        # Handle button touches
        for btn in buttons:
            btn.get_touch(ui)
        time.sleep(0.05)


main()