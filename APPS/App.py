# Auto-generated Zeno UI Studio screen
# App: App (v1.0.0) by Phoenix

import time
from Graphics import color565 ,UIScreen, UIButton, UIText, UISlider, UIToggleSwitch, UIProgressBar, UIPanel
import zeno

APP_NAME    = 'App'
APP_AUTHOR  = 'Phoenix'
APP_VERSION = '1.0.0'

ui = zeno.ui

def on_exit():
    raise APP_EXIT

def main():

    screen = UIScreen(ui, background=color565(255, 255, 255), taskbarcolor=color565(50, 50, 50), taskbar_text='App', taskbar_text_color=color565(255, 255, 255), on_exit=on_exit)

    screen.start(ui)

    screen.layer(102, 76, 40, 40, color565(0, 0, 0))
    screen.layer(142, 76, 40, 40, color565(0, 128, 0))
    screen.layer(182, 76, 40, 40, color565(0, 0, 0))
    screen.layer(142, 116, 40, 20, color565(0, 0, 0))
    screen.layer(182, 116, 60, 20, color565(0, 128, 0))
    screen.layer(82, 116, 60, 20, color565(0, 128, 0))
    screen.layer(82, 36, 20, 80, color565(0, 128, 0))
    screen.layer(102, 36, 140, 40, color565(0, 128, 0))
    screen.layer(222, 76, 20, 40, color565(0, 128, 0))
    screen.layer(117, 136, 90, 40, color565(0, 0, 0))
    screen.layer(82, 136, 38, 80, color565(0, 128, 0))
    screen.layer(120, 176, 20, 20, color565(0, 0, 0))
    screen.layer(187, 176, 20, 20, color565(0, 0, 0))
    screen.layer(207, 136, 35, 80, color565(0, 128, 0))
    screen.layer(120, 196, 87, 20, color565(0, 128, 0))
    screen.layer(140, 176, 47, 20, color565(0, 128, 0))


    buttons = []
    sliders = []
    toggles = []
    progress_bars = []
    panels = []


    for panel in panels:
        panel.draw(ui)

    for bar in progress_bars:
        bar.draw(ui)

    for slider in sliders:
        slider.draw(ui)

    for toggle in toggles:
        toggle.draw(ui)

    for btn in buttons:
        btn.draw(ui)

    ui.fade_in(fade_time=0.4)

    while True:
        screen.check(ui)
        for btn in buttons:
            btn.get_touch(ui)

        for slider in sliders:
            slider.handle_touch(ui)

        for toggle in toggles:
            toggle.handle_touch(ui)


        time.sleep(0.05)


main()