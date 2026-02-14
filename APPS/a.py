# Auto-generated Zeno UI screen
# App: a (v1.0.0) by Phoenix

import time
from Graphics import color565 ,UIScreen, UIButton, UIText, UISlider, UIToggleSwitch, UIProgressBar, UIPanel
import zeno

APP_NAME    = 'a'
APP_AUTHOR  = 'Phoenix'
APP_VERSION = '1.0.0'

ui = zeno.ui

def on_exit():
    pass

def main():

    screen = UIScreen(ui, background=color565(0, 0, 0), taskbarcolor=color565(50, 50, 50), taskbar_text='a', taskbar_text_color=color565(255, 255, 255), on_exit=on_exit)

    screen.start(ui)

    screen.layer(187, 65, 100, 40, color565(80, 80, 80))


    buttons = []
    sliders = []
    toggles = []
    progress_bars = []
    panels = []

    def on_button_click():
        print('Button Button 1 pressed')

    buttons.append(UIButton(56, 74, 100, 30, label='Button 1', color=color565(200, 50, 50), text_color=color565(255, 255, 255), margin=5, action=on_button_click))
    toggles.append(UIToggleSwitch(118, 143, 50, state=False))
    toggles.append(UIToggleSwitch(23, 128, 50, state=False))
    progress_bars.append(UIProgressBar(31, 47, 120, value=40))
    panels.append(UIPanel(25, 107, 150, 100))
    sliders.append(UISlider(146, 174, 120, value=50))

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
        for btn in buttons:
            btn.get_touch(ui)

        for slider in sliders:
            slider.handle_touch(ui)

        for toggle in toggles:
            toggle.handle_touch(ui)

        time.sleep(0.05)


main()