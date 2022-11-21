#!/usr/bin/env python
# coding: utf-8

from datetime import datetime
import time
import subprocess



MN = [*range(6, 13)]
TD = [*range(13, 18)]
NT = [*range(18, 24)]
MD = [*range(0, 6)]


while True:
    time.sleep(30)
    current_hora = datetime.now()

    # NOITE (EVENING)
    if current_hora.hour in NT:
        time.sleep(5)
        subprocess.call('sct 3500', shell=True)

    # MADRUGADA & ATÉ 06 DA MANHÃ:
    elif current_hora.hour in MD:
        time.sleep(5)
        subprocess.call('sct 3200', shell=True)

    # MORNING Das 06 AO MEIO DIA:
    elif current_hora.hour in MN:
        time.sleep(5)
        #print('MANHÃ')
        subprocess.call('sct 4500', shell=True)

    # VESPERTINO
    elif current_hora.hour in TD:
        time.sleep(5)
        subprocess.call('sct 6100', shell=True)


# https://www.eizo.com/library/basics/color_temperature_on_an_LCD_monitor/
