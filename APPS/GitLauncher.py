# Auto-generated Zeno UI screen
# App: GitLauncher (v1.0.0) by Phoenix

import time
from ili9341 import color565
from firmware import HUIModule, UIScreen, UIButton, UIText

APP_NAME    = 'GitLauncher'
APP_AUTHOR  = 'Phoenix'
APP_VERSION = '1.0.0'

def main(ui=None, on_exit=None):
    # Create UI context if not provided
    if ui is None:
        ui = HUIModule()
        ui.begin()

    # Create screen
    screen = UIScreen(ui, background=color565(255, 255, 255), taskbarcolor=color565(128, 0, 64), taskbar_text='GitLauncher', taskbar_text_color=color565(255, 255, 255), on_exit=on_exit)

    screen.start(ui)

    # Draw layers (colored rectangles)
    screen.layer(6, 40, 305, 25, color565(80, 80, 80))
    screen.layer(6, 69, 305, 165, color565(216, 216, 216))
    screen.layer(10, 44, 176, 17, color565(216, 216, 216))

    # Create and draw texts (UIText)

    # Create and draw buttons
    buttons = []
    def on_button_click():
        print('Button Search pressed')

    buttons.append(UIButton(190, 43, 64, 19, label='Search', color=color565(200, 50, 50), text_color=color565(255, 255, 255), margin=5, action=on_button_click))
    buttons.append(UIButton(258, 44, 49, 17, label='Download', color=color565(200, 50, 50), text_color=color565(255, 255, 255), margin=5, action=on_button_click))

    for btn in buttons:
        btn.draw(ui)

    ui.fade_in(fade_time=0.4)

    while True:
        # Handle button touches
        for btn in buttons:
            btn.get_touch(ui)
        time.sleep(0.05)


main()