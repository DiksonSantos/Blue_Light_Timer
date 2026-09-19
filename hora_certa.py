#!/home/dikson/.MiniConda_/envs/Dados/bin/python
# coding: utf-8
from datetime import date, time as dtime
from astral import LocationInfo
from astral.sun import sun
import pytz

# Configuração da localização: Salto-SP
city = LocationInfo("Salto", "Brazil", "America/Sao_Paulo", -23.2000, -47.2856)
local_tz = pytz.timezone('America/Sao_Paulo')

def get_today_sun_times():
    """
    Calcula e retorna MORNING_START (Nascer do Sol) e EVENING_START (Pôr do Sol)
    para o dia atual (em BRT), arredondado para minutos.
    """
    today = date.today()

    # Calcula sun com data local
    s = sun(city.observer, date=today, tzinfo=local_tz)

    # Extrai horários já em timezone local
    morning_start_dt = s["sunrise"].time()
    evening_start_dt = s["sunset"].time()

    # Arredonda para minutos (remove segundos)
    morning_start = dtime(morning_start_dt.hour, morning_start_dt.minute)
    evening_start = dtime(evening_start_dt.hour, evening_start_dt.minute)

    return {
        "MORNING_START": morning_start,
        "EVENING_START": evening_start
    }

# O bloco abaixo é opcional. Mantido apenas para que o script possa ser executado
# individualmente para fins de teste, mas não será executado quando importado.
if __name__ == "__main__":
    times = get_today_sun_times()
    print(f"Hoje: Nascer {times['MORNING_START']}, Pôr {times['EVENING_START']} Do_Sól")


# from datetime import date, timedelta, time as dtime
# from astral import LocationInfo
# from astral.sun import sun
# import pytz  # Para timezone
#
# # Configuração da localização: Salto-SP
# city = LocationInfo("Salto", "Brazil", "America/Sao_Paulo", -23.2000, -47.2856)
#
# # Timezone local (BRT = UTC-3)
# local_tz = pytz.timezone('America/Sao_Paulo')
#
# # Período: Novembro 2025 (mude para o que quiser)
# start_date = date(2025, 11, 1)
# end_date = date(2025, 11, 30)
#
# # Dicionário para horários exatos por dia (corrigido para BRT)
# daily_transitions = {}
#
# current_date = start_date
# while current_date <= end_date:
#     # Calcula sun com data local
#     s = sun(city.observer, date=current_date, tzinfo=local_tz)
#
#     # Extrai horários já em timezone local
#     morning_start = s["sunrise"].time()  # time object (HH:MM:SS) em BRT
#     evening_start = s["sunset"].time()   # time object (HH:MM:SS) em BRT
#
#     # Arredonda para minutos (remove segundos)
#     morning_start = dtime(morning_start.hour, morning_start.minute)
#     evening_start = dtime(evening_start.hour, evening_start.minute)
#
#     day_key = current_date.day
#     daily_transitions[day_key] = {
#         "MORNING_START": morning_start,
#         "EVENING_START": evening_start
#     }
#
#     current_date += timedelta(days=1)
#
# # Exemplo de uso/impressão
# print("Horários Exatos por Dia - Novembro 2025 (Salto-SP, BRT)")
# print("=" * 50)
# for day, times in sorted(daily_transitions.items()):
#     print(f"Dia {day:2d}: Nascer {times['MORNING_START']}, Pôr {times['EVENING_START']}")
#
# # Para integrar: daily_transitions[8] para 08/11/2025
