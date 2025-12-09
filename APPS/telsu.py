import time
from ili9341 import color565
from firmware import HUIModule, UIScreen, UIButton, UIText

APP_NAME    = 'telsu'
APP_AUTHOR  = 'nenu'
APP_VERSION = '1'

def main(ui=None, on_exit=None):
    # Initialize UI
    if ui is None:
        ui = HUIModule()
        ui.begin()

    # Create screen
    screen = UIScreen(ui, background=color565(128, 0, 64), taskbarcolor=color565(255, 255, 255), taskbar_text='telsu', taskbar_text_color=color565(0, 0, 0), on_exit=on_exit)
    screen.start(ui)

    buttons = []

    txt_1 = UIText(x=91, y=61, text="naku telsu le voi", fg=color565(255, 255, 255))
    txt_1.draw(ui)

    btn_1 = UIButton(x=139, y=112, w=80, h=30, label="sarle", color=color565(0, 0, 255), text_color=color565(255, 255, 255), margin=5, action=None)
    btn_1.draw(ui)
    buttons.append(btn_1)

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
