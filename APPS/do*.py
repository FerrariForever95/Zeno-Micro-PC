# Auto-generated Zeno UI Studio screen
# App: do* (v1.0.0) by User

import time
from Graphics import color565 ,UIScreen, UIButton, UIText, UISlider, UIToggleSwitch, UIProgressBar, UIPanel
import zeno

APP_NAME    = 'do*'
APP_AUTHOR  = 'User'
APP_VERSION = '1.0.0'

ui = zeno.ui

def on_exit():
    raise APP_EXIT

def main():

    screen = UIScreen(ui, background=color565(0, 0, 0), taskbarcolor=color565(38, 49, 62), taskbar_text='simple application demo', taskbar_text_color=color565(255, 255, 255), on_exit=on_exit)

    screen.start(ui)

    screen.layer(2, 38, 314, 200, color565(74, 113, 47))

    UIText(42, 60, 'Simple Toggle Switch', color=color565(255, 255, 255)).draw(ui)

    buttons = []
    sliders = []
    toggles = []
    progress_bars = []
    panels = []

    toggles.append(UIToggleSwitch(246, 53, 50, state=True))

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