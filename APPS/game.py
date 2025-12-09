import time
from ili9341 import color565
from firmware import HUIModule, UIScreen, UIButton, UIText

APP_NAME    = 'game'
APP_AUTHOR  = 'shanmukh'
APP_VERSION = '1'

def main(ui=None, on_exit=None):
    # Initialize UI
    if ui is None:
        ui = HUIModule()
        ui.begin()

    # Create screen
    screen = UIScreen(ui, background=color565(255, 255, 255), taskbarcolor=color565(255, 0, 128), taskbar_text='game', taskbar_text_color=color565(255, 255, 255), on_exit=on_exit)
    screen.start(ui)

    buttons = []

    btn_1 = UIButton(x=62, y=114, w=80, h=30, label="on", color=color565(128, 0, 255), text_color=color565(255, 255, 255), margin=5, action=off)
    btn_1.draw(ui)
    buttons.append(btn_1)

    btn_2 = UIButton(x=193, y=114, w=80, h=30, label="off", color=color565(170, 0, 0), text_color=color565(255, 255, 255), margin=5, action=on)
    btn_2.draw(ui)
    buttons.append(btn_2)

    txt_1 = UIText(x=137, y=46, text="Text", fg=color565(255, 255, 255))
    txt_1.draw(ui)

    txt_2 = UIText(x=150, y=51, text="touch on or off", fg=color565(0, 0, 0))
    txt_2.draw(ui)

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

# --- Button Actions ---
def off():
    print('Action off() called')

def on():
    print('Action on() called')
