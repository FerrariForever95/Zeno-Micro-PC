# Auto-generated Zeno UI screen
# App: Settings (v1.0.0) by Phoenix

import time
from ili9341 import color565
from firmware import HUIModule, UIScreen, UIButton

APP_NAME    = 'Settings'
APP_AUTHOR  = 'Phoenix'
APP_VERSION = '1.0.0'

def main(ui=None, on_exit=None):
    # Create UI context if not provided
    if ui is None:
        ui = HUIModule()
        ui.begin()

    # Create screen
    screen = UIScreen(ui, background=color565(255, 255, 255), taskbarcolor=color565(50, 50, 50), taskbar_text='Settings', taskbar_text_color=color565(255, 255, 255), on_exit=on_exit)

    screen.start(ui)

    # Draw layers (colored rectangles)
    screen.layer(2, 46, 315, 32, color565(80, 80, 80))
    screen.layer(3, 85, 313, 31, color565(80, 80, 80))
    screen.layer(3, 117, 313, 121, color565(80, 80, 80))

    # Create and draw buttons
    buttons = []
    def on_button_click():
        print('Button Performance pressed')

    buttons.append(UIButton(7, 52, 92, 22, label='Performance', color=color565(20, 32, 248), text_color=color565(255, 255, 255), margin=5, action=on_button_click))
    buttons.append(UIButton(107, 52, 98, 22, label='Balanced', color=color565(91, 126, 247), text_color=color565(255, 255, 255), margin=5, action=on_button_click))
    buttons.append(UIButton(210, 52, 102, 22, label='Power Saving', color=color565(87, 220, 31), text_color=color565(255, 255, 255), margin=5, action=on_button_click))
    buttons.append(UIButton(9, 90, 147, 22, label='WiFi On', color=color565(200, 50, 50), text_color=color565(255, 255, 255), margin=5, action=on_button_click))
    buttons.append(UIButton(163, 90, 147, 22, label='WiFI  Off', color=color565(200, 50, 50), text_color=color565(255, 255, 255), margin=5, action=on_button_click))

    for btn in buttons:
        btn.draw(ui)

    ui.fade_in(fade_time=0.4)

    while True:
        # Handle button touches
        for btn in buttons:
            btn.get_touch(ui)
        time.sleep(0.05)


main()