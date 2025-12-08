import time
from ili9341 import color565
from firmware import HUIModule, UIScreen, UIButton, UIText

APP_NAME    = 'testing'
APP_AUTHOR  = 'Phoenix'
APP_VERSION = '1.0.0'

def main(ui=None, on_exit=None):
    # Initialize UI
    if ui is None:
        ui = HUIModule()
        ui.begin()

    # Create screen
    screen = UIScreen(ui, background=color565(0, 0, 0), taskbarcolor=color565(50, 50, 50), taskbar_text='testing', taskbar_text_color=color565(255, 255, 255), on_exit=on_exit)
    screen.start(ui)

    buttons = []

    try:
        ui.fade_in(fade_time=0.4)
    except:
        try: ui.on()
        except: pass

    # Main event loop
    while True:
        for b in buttons:
            b.get_touch(ui)  # triggers action() if pressed
        time.sleep(0.05)

main()
