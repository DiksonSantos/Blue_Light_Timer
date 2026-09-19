#!/home/dikson/.MiniConda_/envs/Dados/bin/python
# coding: utf-8

# 07/05/2026 -> Adicionada Transição suave para troca de Temperatura & Brilho.
# 13/05/2026 -> Adicionado período late_night (21h–00h), meio-termo entre evening e night.
# 08/06/2026 -> Controle automático de frequência do eDP-1: 144Hz na tomada, 60Hz na bateria.
# 08/06/2026 -> Brilho eDP-1 reduzido 35% na bateria; HDMI não é afetado.
# 14/08/2026 -> Ajustadas temperaturas morning/evening e alinhado expected_sct_gamma.
# 14/08/2026 -> Alinhado com as novas temperaturas dos SETTINGS:
#  morning 4000K.
#  4000K usa valor interpolado a partir do anterior 4500K.
# 16/08/2026 -> evening agora tem 2 valores possíveis (perfil
# gaming/movie alternado por update_evening_profile):
# 4300K (gaming) e 3500K (movie, original).

import subprocess
from datetime import datetime, time as dtime
import time
import re
from hora_certa import get_today_sun_times

"""
PARAR SERVIÇO;
systemctl --user stop pos_blue.service

IMPEDIR QUE REINICIE AUTOMATICAMENTE;
systemctl --user stop pos_blue.service && systemctl --user disable pos_blue.service

CONFIRMAR QUE PAROU;
systemctl --user status pos_blue.service

REATIVAR;
systemctl --user enable --now pos_blue.service
"""

# CONTEM MELHORIAS NOS HORARIOS DE TRANSIÇÃO 07-11-25
# v2: Transições graduais entre períodos (sem clarão abrupto ao meio-dia)
# v3: Novo período late_night das 21h às 00h (meio-termo entre evening e night)
# v4: Frequência eDP-1 automática — 144Hz (AC) / 60Hz (bateria), sem reaplica se já estiver certo
# v5: Brilho eDP-1 escalado por BATTERY_BRIGHTNESS_FACTOR (0.65) fora da tomada; HDMI inalterado

# === CONFIGURAÇÕES GERAIS ===
BRIGHTNESS_PATH = "/sys/class/backlight/intel_backlight/brightness"
LOG_FILE = "/tmp/pos_Blue_Brilho.log"
HDMI_OUTPUT = "HDMI-1-0"
EDP_OUTPUT  = "eDP-1"

# Caminhos para detecção de fonte de energia
AC_ONLINE_PATH = "/sys/class/power_supply/ACAD/online"

# Frequências alvo por fonte de energia
HZ_ON_AC      = 144.00
HZ_ON_BATTERY = 60.01

# Modo de resolução fixo do eDP-1 (deve bater com o listado em xrandr)
EDP_MODE = "1920x1080"

# Estado da última frequência aplicada (evita reaplicação desnecessária)
_last_edp_hz = None

# Fator de redução de brilho do eDP-1 quando na bateria (0.65 = 35% menos)
BATTERY_BRIGHTNESS_FACTOR = 0.65

# Estado do último brilho aplicado (evita escrita desnecessária no backlight)
_last_brightness = None

# Estado do último gamma/brilho aplicados no HDMI (evita reaplicar xrandr sem necessidade,
# que é o que causa o piscar do monitor externo — antes era chamado todo ciclo, sempre)
_last_hdmi_gamma = None
_last_hdmi_brightness = None

# Duração da janela de transição em minutos (ex: 20 = 10 min antes e 10 min depois da virada)
TRANSITION_MINUTES = 1

# Horário fixo de início da madrugada profunda (late_night → night)
LATE_NIGHT_START = dtime(21, 0)

# === CONFIGURAÇÕES OTIMIZADAS PARA HDMI ===
# 14/08/2026 -> Ajustes de temperatura/brilho:
#              morning 4500K → 4000K
#              evening 3500K → 4300K
#              Demais valores mantidos conforme configuração atual.
# 16/08/2026 -> evening agora tem dois perfis, alternados automaticamente
#              pelo CPU governor (ver EVENING_PROFILES / update_evening_profile):
#              performance (jogos AAA) → 4300K | qualquer outro → 3500K (filmes/vídeos)
SETTINGS = {
    "morning": {
        "brightness": 9060,
        "color_temp": 4000,
        "gamma_hdmi": "1.00:0.95:0.90",
        "hdmi_brightness": 0.80
    },
    "afternoon": {
        "brightness": 14400,
        "color_temp": 6500,
        "gamma_hdmi": "1.00:1.00:1.00",
        "hdmi_brightness": 1.00
    },
    "evening": {
        # Valor inicial (será sobrescrito por update_evening_profile() a cada
        # ciclo do loop, de acordo com o CPU governor). Mantido aqui só para
        # o script funcionar mesmo antes da primeira checagem do governor.
        "brightness": 4000,
        "color_temp": 3500,
        "gamma_hdmi": "1.00:0.90:0.60",
        "hdmi_brightness": 0.50
    },
    "late_night": {
        "brightness": 2200,          # meio-termo entre evening(4000) e night(1000)
        "color_temp": 3000,          # meio-termo entre evening(atual) e night(2700)
        "gamma_hdmi": "1.00:0.80:0.35",  # meio-termo entre evening e night
        "hdmi_brightness": 0.40      # meio-termo entre evening(0.50) e night(0.30)
    },
    "night": {
        "brightness": 1000,
        "color_temp": 2700,
        "gamma_hdmi": "1.00:0.70:0.15",
        "hdmi_brightness": 0.30
    }
}

# === PERFIS DO PERÍODO EVENING (alternados pelo CPU governor) ===
# gaming: usado quando o governor está em 'performance' (jogos AAA) — mais
#         frio/vívido (color_temp) e mais claro (brightness), pra ver detalhe
#         em jogos com cenas escuras (RE9 Requiem, Mafia: The Old Country,
#         Ace Combat 7) sem forçar a vista.
# movie:  usado em qualquer outro governor — mais quente e mais escuro,
#         melhor pra assistir filmes/vídeos por muito tempo sem cansar.
# gamma_hdmi e hdmi_brightness ficam iguais nos dois perfis (só afetam o
# monitor HDMI externo, não o brilho do painel interno).
EVENING_PROFILES = {
    "gaming": {
        "brightness": 7000,   # 16/08/2026: subido de 4000 → 7000 a pedido,
                               # pra melhor visibilidade em jogos escuros
        "color_temp": 4300,
        "gamma_hdmi": "1.00:0.90:0.60",
        "hdmi_brightness": 0.50
    },
    "movie": {
        "brightness": 4000,
        "color_temp": 3500,
        "gamma_hdmi": "1.00:0.90:0.60",
        "hdmi_brightness": 0.50
    }
}

# Caminho do governor da CPU (cpu0 como referência — a maioria dos sistemas
# usa a mesma política de governor em todos os núcleos)
CPU_GOVERNOR_PATH = "/sys/devices/system/cpu/cpu0/cpufreq/scaling_governor"

# Governor que caracteriza "jogo AAA rodando" (gamemode, feral gamemode,
# powerprofilesctl, etc. tipicamente forçam 'performance' nesse momento)
GAMING_GOVERNOR = "performance"

# Estado do último perfil evening aplicado (só pra log, não crítico)
_last_evening_profile = None

def get_cpu_governor():
    """Lê o governor atual da CPU. Retorna None se não conseguir ler
    (ex: rodando em sandbox/VM sem cpufreq, ou CPU sem esse sysfs)."""
    try:
        with open(CPU_GOVERNOR_PATH, "r") as f:
            return f.read().strip()
    except Exception as e:
        log_message(f"Erro ao ler CPU governor: {e}")
        return None

def update_evening_profile():
    """
    Escolhe o perfil do 'evening' com base no CPU governor atual e atualiza
    SETTINGS['evening'] in-place. Chamado a cada ciclo do loop principal,
    então a troca de perfil (ex: ao abrir/fechar um jogo AAA) é detectada
    em poucos segundos, sem precisar reiniciar o serviço.
    """
    global _last_evening_profile

    governor = get_cpu_governor()
    profile_name = "gaming" if governor == GAMING_GOVERNOR else "movie"
    SETTINGS["evening"] = EVENING_PROFILES[profile_name]

    if profile_name != _last_evening_profile:
        log_message(
            f"Perfil evening → {profile_name.upper()} "
            f"(governor='{governor}', {SETTINGS['evening']['color_temp']}K)"
        )
        _last_evening_profile = profile_name

# === CACHE DE TEMPOS DE TRANSIÇÃO DIÁRIA ===
_DAILY_TRANSITION_CACHE = {"day": -1, "times": None}

def get_daily_transitions():
    """Retorna os horários de transição (MORNING/EVENING) baseados no nascer/pôr do sol de HOJE."""
    global _DAILY_TRANSITION_CACHE
    now = datetime.now()

    if now.day != _DAILY_TRANSITION_CACHE["day"]:
        log_message(f"--- RECALCULANDO: Novo dia ({now.day}) ---")
        try:
            sun_times = get_today_sun_times()
            _DAILY_TRANSITION_CACHE["times"] = sun_times
            _DAILY_TRANSITION_CACHE["day"] = now.day
        except Exception as e:
            log_message(f"ERRO ao calcular sun times: {e}. Usando fallback.")
            _DAILY_TRANSITION_CACHE["times"] = {
                "MORNING_START": dtime(6, 30),
                "EVENING_START": dtime(18, 00)
            }

    times = _DAILY_TRANSITION_CACHE["times"]

    return {
        "NIGHT_START":      dtime(0, 0),
        "AFTERNOON_START":  dtime(12, 0),
        "MORNING_START":    times["MORNING_START"],
        "EVENING_START":    times["EVENING_START"],
        "LATE_NIGHT_START": LATE_NIGHT_START        # fixo: 21h
    }


# === FUNÇÕES AUXILIARES ===

def log_message(message):
    with open(LOG_FILE, "a") as log:
        log.write(f"{datetime.now()} - {message}\n")

def is_monitor_off():
    try:
        result = subprocess.check_output("xset -display :0 q", shell=True, text=True, timeout=5)
        return "Monitor is Off" in result
    except:
        return False

def set_brightness(value):
    global _last_brightness
    # Aplica fator de bateria apenas no eDP-1 (este path controla só a tela embutida)
    effective = int(value * BATTERY_BRIGHTNESS_FACTOR) if not is_on_ac() else int(value)
    if _last_brightness == effective:
        log_message(f"Brilho principal {effective} OK → brilho pulado")
        return
    try:
        with open(BRIGHTNESS_PATH, 'w') as f:
            f.write(str(effective))
        source_label = "AC" if is_on_ac() else f"bateria ×{BATTERY_BRIGHTNESS_FACTOR}"
        log_message(f"Brilho principal → {effective} ({source_label})")
        _last_brightness = effective
    except Exception as e:
        log_message(f"Erro brilho principal: {e}")

def get_current_gamma_primary():
    try:
        output = subprocess.check_output("xrandr --verbose", shell=True, text=True)
        for line in output.splitlines():
            if re.search(r"^\s+Gamma:", line):
                match = re.search(r"Gamma:\s*([\d.]+):([\d.]+):([\d.]+)", line)
                if match:
                    return f"{match.group(1)}:{match.group(2)}:{match.group(3)}"
        return None
    except Exception as e:
        log_message(f"Erro ao ler gamma: {e}")
        return None

def gamma_close(g_a, g_b, tol=0.05):
    """
    Compara duas strings de gamma 'R:G:B' com tolerância numérica.
    Necessário porque o xrandr arredonda/quantiza o gamma ao ler de volta
    (ex: 1.0:1.22:1.49 configurado vira 1.0:1.2:1.5 no 'xrandr --verbose'),
    então uma comparação de string exata nunca bate e o sct fica sendo
    reaplicado a cada ciclo sem necessidade.
    """
    if not g_a or not g_b:
        return False
    try:
        ra, ga, ba = [float(x) for x in g_a.split(":")]
        rb, gb, bb = [float(x) for x in g_b.split(":")]
    except ValueError:
        return False
    return abs(ra - rb) < tol and abs(ga - gb) < tol and abs(ba - bb) < tol

def apply_sct(temp):
    global _last_hdmi_gamma, _last_hdmi_brightness
    try:
        subprocess.call(f"sct {int(temp)}", shell=True)
        log_message(f"sct {int(temp)}K → principal")
        # sct mexe na rampa de gamma da TELA inteira (todos os outputs do X,
        # não só o eDP-1) — então qualquer chamada aqui também bagunça o
        # gamma/brilho do HDMI. Invalida o cache do HDMI para forçar
        # reaplicação logo em seguida, no mesmo ciclo do loop.
        _last_hdmi_gamma = None
        _last_hdmi_brightness = None
    except Exception as e:
        log_message(f"Erro sct: {e}")

def apply_hdmi_gamma_brightness(gamma, brightness):
    global _last_hdmi_gamma, _last_hdmi_brightness

    # Arredonda para não recriar micro-diferenças de ponto flutuante entre ciclos
    brightness_r = round(brightness, 3)

    # Pula se já é exatamente o que está aplicado — evita reaplicar xrandr todo
    # ciclo (2-3s) em período estável, que é o que fazia o HDMI piscar
    if _last_hdmi_gamma == gamma and _last_hdmi_brightness == brightness_r:
        log_message(f"HDMI {gamma} | {brightness_r:.3f} OK → xrandr pulado")
        return

    cmd = f"xrandr --output {HDMI_OUTPUT} --gamma {gamma} --brightness {brightness_r:.3f}"
    try:
        subprocess.call(cmd, shell=True)
        log_message(f"HDMI → gamma {gamma} | brilho {brightness_r:.3f}")
        _last_hdmi_gamma = gamma
        _last_hdmi_brightness = brightness_r
    except Exception as e:
        log_message(f"Erro xrandr HDMI: {e}")


# === CONTROLE DE FREQUÊNCIA eDP-1 POR FONTE DE ENERGIA ===

def is_on_ac():
    """Retorna True se o notebook estiver na tomada (ACAD/online == 1)."""
    try:
        with open(AC_ONLINE_PATH, 'r') as f:
            return f.read().strip() == "1"
    except Exception as e:
        log_message(f"Erro ao ler status AC ({AC_ONLINE_PATH}): {e} → assumindo AC")
        return True  # fallback seguro: não throttle em caso de dúvida

def get_current_edp_hz():
    """
    Lê a frequência atual do eDP-1 via xrandr --verbose.
    Procura a linha de modo marcada com '*' (ativo) no bloco do eDP-1.
    Retorna um int (ex: 144 ou 60) ou None se não conseguir ler.
    """
    try:
        output = subprocess.check_output(
            "xrandr --verbose", shell=True, text=True, timeout=5
        )
        in_edp_block = False
        for line in output.splitlines():
            # Detecta início do bloco eDP-1
            if re.match(r'^eDP-1\s', line):
                in_edp_block = True
                continue
            # Sai do bloco ao encontrar outra saída
            if in_edp_block and re.match(r'^\S', line):
                break
            # Dentro do bloco: procura linha de modo ativo (contém '*')
            if in_edp_block and '*' in line:
                match = re.search(r'([\d.]+)\*', line)
                if match:
                    return round(float(match.group(1)), 2)
        return None
    except Exception as e:
        log_message(f"Erro ao ler Hz eDP-1: {e}")
        return None

def apply_edp_refresh_rate():
    """
    Aplica 144Hz (AC) ou 60Hz (bateria) ao eDP-1, mas apenas se a frequência
    atual for diferente da desejada. Segue a mesma lógica de 'pular se já estiver correto'.
    """
    global _last_edp_hz, _last_brightness

    target_hz = HZ_ON_AC if is_on_ac() else HZ_ON_BATTERY

    # Pula se o último estado já é o desejado (evita xrandr desnecessário)
    if _last_edp_hz == target_hz:
        log_message(f"eDP-1 {target_hz}Hz OK → frequência pulada")
        return

    # Confirma lendo o valor real do sistema antes de aplicar
    current_hz = get_current_edp_hz()
    if current_hz == target_hz:
        log_message(f"eDP-1 {target_hz}Hz já ativo (xrandr) → frequência pulada")
        _last_edp_hz = target_hz
        return

    # Fonte de energia mudou → invalida cache de brilho para forçar reaplicação imediata
    _last_brightness = None

    # Aplica a mudança
    source_label = "AC" if target_hz == HZ_ON_AC else "bateria"
    log_message(
        f"eDP-1: fonte={source_label} | atual={current_hz}Hz → aplicando {target_hz}Hz"
    )
    try:
        subprocess.call(
            f"xrandr --output {EDP_OUTPUT} --mode {EDP_MODE} --rate {target_hz}",
            shell=True
        )
        _last_edp_hz = target_hz
    except Exception as e:
        log_message(f"Erro ao setar frequência eDP-1: {e}")


# === INTERPOLAÇÃO ENTRE CONFIGURAÇÕES ===

def lerp(a, b, t):
    """Interpolação linear entre a e b com fator t em [0.0, 1.0]."""
    return a + (b - a) * t

def lerp_gamma(g_a, g_b, t):
    """Interpola duas strings de gamma no formato 'R:G:B'."""
    ra, ga, ba = [float(x) for x in g_a.split(":")]
    rb, gb, bb = [float(x) for x in g_b.split(":")]
    r = lerp(ra, rb, t)
    g = lerp(ga, gb, t)
    b = lerp(ba, bb, t)
    return f"{r:.2f}:{g:.2f}:{b:.2f}"

def time_to_minutes(t):
    """Converte um objeto time em minutos desde meia-noite."""
    return t.hour * 60 + t.minute + t.second / 60.0

def get_interpolated_config(now_minutes, T):
    """
    Retorna uma configuração interpolada se estiver dentro de uma janela de transição.
    Caso contrário retorna a configuração pura do período atual.
    """
    half = TRANSITION_MINUTES / 2.0

    # Monta lista de (minuto_da_virada, periodo_anterior, periodo_seguinte)
    transitions = [
        (time_to_minutes(T["MORNING_START"]),    "night",      "morning"),
        (time_to_minutes(T["AFTERNOON_START"]),  "morning",    "afternoon"),
        (time_to_minutes(T["EVENING_START"]),    "afternoon",  "evening"),
        (time_to_minutes(T["LATE_NIGHT_START"]), "evening",    "late_night"),
        # Virada de meia-noite: trata como 1440 min para facilitar a conta
        (time_to_minutes(T["NIGHT_START"]) + 1440, "late_night", "night"),
    ]

    for (pivot, period_from, period_to) in transitions:
        dist = now_minutes - pivot   # negativo = antes da virada, positivo = depois

        if -half <= dist <= half:
            # t vai de 0.0 (início da janela) até 1.0 (fim da janela)
            t = (dist + half) / TRANSITION_MINUTES
            cfg_from = SETTINGS[period_from]
            cfg_to   = SETTINGS[period_to]

            blended = {
                "brightness":      lerp(cfg_from["brightness"],      cfg_to["brightness"],      t),
                "color_temp":      lerp(cfg_from["color_temp"],      cfg_to["color_temp"],      t),
                "gamma_hdmi":      lerp_gamma(cfg_from["gamma_hdmi"], cfg_to["gamma_hdmi"],     t),
                "hdmi_brightness": lerp(cfg_from["hdmi_brightness"], cfg_to["hdmi_brightness"], t),
            }
            log_message(
                f"[TRANSIÇÃO {period_from}→{period_to}] t={t:.2f} | "
                f"brilho={int(blended['brightness'])} | temp={int(blended['color_temp'])}K"
            )
            return blended, True  # True = está em transição

    # Fora de qualquer janela → período puro
    period = get_time_period_pure(now_minutes, T)
    return SETTINGS[period], False


def get_time_period_pure(now_minutes, T):
    """Determina o período sem considerar janelas de transição."""
    morning    = time_to_minutes(T["MORNING_START"])
    afternoon  = time_to_minutes(T["AFTERNOON_START"])
    evening    = time_to_minutes(T["EVENING_START"])
    late_night = time_to_minutes(T["LATE_NIGHT_START"])

    if now_minutes < morning:
        return "night"
    elif now_minutes < afternoon:
        return "morning"
    elif now_minutes < evening:
        return "afternoon"
    elif now_minutes < late_night:
        return "evening"
    else:
        return "late_night"


# === LOOP PRINCIPAL ===
while True:
    time.sleep(2)
    now = datetime.now()
    t_now = now.time()
    now_minutes = time_to_minutes(t_now)

    # Atualiza o perfil evening (gaming/movie) de acordo com o CPU governor
    # ANTES de calcular a config do ciclo, para já valer neste mesmo ciclo.
    update_evening_profile()

    T_DAILY = get_daily_transitions()

    cfg, in_transition = get_interpolated_config(now_minutes, T_DAILY)

    # Log de status
    period_label = "TRANSIÇÃO" if in_transition else get_time_period_pure(now_minutes, T_DAILY).upper()
    log_message(
        f"\n=== {now.strftime('%H:%M:%S')} | Período: {period_label} | "
        f"Morning: {T_DAILY['MORNING_START']} | Evening: {T_DAILY['EVENING_START']} | "
        f"Late Night: {T_DAILY['LATE_NIGHT_START']} ==="
    )

    if is_monitor_off():
        log_message("Monitor off → pulando")
        time.sleep(12)
        continue

    # 1. Brilho principal
    set_brightness(cfg["brightness"])

    # 2. sct no principal
    # Durante transição, aplica sct a cada ciclo para acompanhar a interpolação.
    # Fora de transição, verifica se gamma já está correto antes de aplicar.
    if in_transition:
        apply_sct(cfg["color_temp"])
    else:
        current_gamma = get_current_gamma_primary()
        expected_sct_gamma = {
            2700: "1.0:1.5:2.6",
            3000: "1.0:1.4:2.2",   # late_night
            3500: "1.0:1.3:1.9",   # evening — perfil movie
            4000: "1.0:1.25:1.65", # morning
            4300: "1.0:1.22:1.49", # evening — perfil gaming
            6500: "1.0:1.0:1.0"
        }.get(int(cfg["color_temp"]))

        if not gamma_close(current_gamma, expected_sct_gamma):
            log_message(f"Gamma principal errado ({current_gamma}) → aplicando sct {int(cfg['color_temp'])}K")
            apply_sct(cfg["color_temp"])
            time.sleep(1.5)
        else:
            log_message(f"Gamma principal {int(cfg['color_temp'])}K OK → sct pulado")

    # 3. HDMI: gamma + brilho interpolados
    apply_hdmi_gamma_brightness(cfg["gamma_hdmi"], cfg["hdmi_brightness"])

    # 4. Frequência eDP-1: 144Hz (tomada) ou 60Hz (bateria) — pula se já estiver correto
    apply_edp_refresh_rate()

    # Durante transição, ciclo mais curto para animação mais suave
    time.sleep(3 if not in_transition else 2)
