#!/usr/bin/env python
from datetime import datetime
import time
import subprocess

MN = [str(x).zfill(2) for x in range(6, 12)]
TD = [str(x).zfill(2) for x in range(12,18)]
NT = [str(x).zfill(2) for x in range(18, 24)]
MD = [str(x).zfill(2) for x in range(00, 6)]


# PEGA HORA MINUTO E SEGUNDO ATUAL
now = datetime.now()
# APENAS A HORA (sem minutos e segundos)
#current_hora = now.strftime("%H")

while True:
    time.sleep(3)
    current_hora = now.strftime("%H")
    # NOITE (EVENING)
    if current_hora in NT:
        time.sleep(5)
        subprocess.call('sct 3500', shell=True)
        
    
    # MADRUGADA & ATÉ 06 DA MANHÃ:
    elif current_hora in MD:
        time.sleep(5)
        subprocess.call('sct 3200', shell=True)
        
    # MANHÃ -> 06 AO MEIO DIA:
    elif current_hora in MN:
        time.sleep(1)
        #print('MANHÃ')
        subprocess.call('sct 4500', shell=True)

    # VESPERTINO
    elif current_hora in TD:
        time.sleep(5)
        subprocess.call('sct 6300', shell=True)

    
# https://www.eizo.com/library/basics/color_temperature_on_an_LCD_monitor/



#now = datetime.now()

# MOSTRA HORA MIN & SEGUNDO ATUAL
#current_time = now.strftime("%H:%M:%S")
#print("Current Time =", current_time)

# PEGA APENAS A HORA:
#current_hora = now.strftime("%H")

# CONVERTE EM UNIDADE 'INTEIRO'
#convert = int(current_hora)

#NT = [*range(18,24)]
#TD = [*range(13,18)]
#MD = [*range(0,7)]
#MN = [*range(6, 13)]

# COVNERTE A HORA PARA NUMERO INTEIRO
#convert = int(current_hora)
