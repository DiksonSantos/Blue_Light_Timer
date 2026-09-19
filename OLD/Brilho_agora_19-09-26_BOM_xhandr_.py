#!/usr/bin/env python3
# coding: utf-8
# ================================================================
#  Brilho_Agora.py — status atual de brilho/gamma dos monitores
# ================================================================
# Substitui o antigo Brilho_Agora.sh.
# 16/08/2026 -> Criado em Python: separa por monitor (principal/externo),
#              mostra brilho em % + valor bruto do backlight, e corrige
#              a leitura do gamma do HDMI (o driver NVIDIA reporta o
#              gamma invertido via 'xrandr --verbose' — ver nota no
#              Blue_Brilho.sh de 16/08/2026). "Brightness:" do eDP-1
#              não é mais mostrado, pois não reflete o brilho real da
#              tela (o backlight não é controlado via xrandr).
# ================================================================

import subprocess
import re
import sys

# === CONFIGURAÇÕES (mesmos nomes usados no Blue_Brilho.sh) ===
HDMI_OUTPUT = "HDMI-1-0"
EDP_OUTPUT = "eDP-1"
BACKLIGHT_BRIGHTNESS_PATH = "/sys/class/backlight/intel_backlight/brightness"
BACKLIGHT_MAX_PATH = "/sys/class/backlight/intel_backlight/max_brightness"
LOG_FILE = "/tmp/pos_Blue_Brilho.log"
LOG_LINES = 4

# === CORES ===
RESET = '\033[0m'
BOLD = '\033[1m'
DIM = '\033[2m'
WHITE = '\033[97m'
GRAY = '\033[38;5;245m'
CYAN = '\033[38;5;81m'
GREEN = '\033[38;5;114m'
BLUE = '\033[38;5;75m'
YELLOW = '\033[38;5;221m'


def linha():
    print(f"{GRAY}────────────────────────────────────────────────────────────────{RESET}")


def secao(titulo, linha_acima=False):
    if linha_acima:
        print()
        linha()
        print(f"{BOLD}{CYAN}{titulo}{RESET}")
    else:
        print(f"\n{BOLD}{CYAN}{titulo}{RESET}")
        linha()


def campo(nome, valor):
    print(f"  {WHITE}{nome+':':<12}{RESET} {valor}")


# === LEITURA DO BACKLIGHT (monitor principal) ===
def get_backlight_percent():
    """
    Lê o brilho atual e o máximo do backlight (eDP-1) e retorna
    (percentual, valor_atual, valor_maximo). Se não conseguir ler,
    retorna (None, None, None).
    """
    try:
        with open(BACKLIGHT_BRIGHTNESS_PATH) as f:
            atual = int(f.read().strip())
        with open(BACKLIGHT_MAX_PATH) as f:
            maximo = int(f.read().strip())
        pct = round((atual / maximo) * 100) if maximo else None
        return pct, atual, maximo
    except Exception as e:
        print(f"{DIM}  (erro ao ler backlight: {e}){RESET}")
        return None, None, None


# === LEITURA DO ESTADO DE UM OUTPUT VIA xrandr --verbose ===
def get_output_state(output_name):
    """
    Lê Gamma e Brightness de um output específico via 'xrandr --verbose'.
    Retorna (gamma_str, brightness_float) ou (None, None).
    """
    try:
        output = subprocess.check_output(
            "xrandr --verbose", shell=True, text=True, timeout=5
        )
    except Exception as e:
        print(f"{DIM}  (erro ao rodar xrandr: {e}){RESET}")
        return None, None

    in_block = False
    gamma = None
    brightness = None
    for line in output.splitlines():
        if re.match(rf'^{re.escape(output_name)}\s', line):
            in_block = True
            continue
        if in_block and re.match(r'^\S', line):
            break
        if in_block:
            m = re.search(r"Gamma:\s*([\d.]+):([\d.]+):([\d.]+)", line)
            if m:
                gamma = f"{m.group(1)}:{m.group(2)}:{m.group(3)}"
            m2 = re.search(r"Brightness:\s*([\d.]+)", line)
            if m2:
                brightness = float(m2.group(1))
    return gamma, brightness


def invert_gamma(g):
    """Inverte 'R:G:B' (1/x) — corrige a leitura invertida do driver NVIDIA."""
    if not g:
        return None
    try:
        r, gg, b = [float(x) for x in g.split(":")]
        return f"{1/r if r else 0:.2f}:{1/gg if gg else 0:.2f}:{1/b if b else 0:.2f}"
    except (ValueError, ZeroDivisionError):
        return None


# === LOG RECENTE ===
def get_recent_log(n=LOG_LINES):
    try:
        with open(LOG_FILE) as f:
            linhas = [l.rstrip("\n") for l in f if l.strip()]
    except Exception as e:
        return [f"(erro ao ler log: {e})"]

    limpo = []
    ts_pattern = re.compile(r'^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d+ - ')
    for l in linhas[-n:]:
        limpo.append(ts_pattern.sub('', l))
    return limpo


# === MAIN ===
def main():
    print(f"{BOLD}{CYAN}══════════════════ STATUS DE BRILHO/GAMMA ══════════════════{RESET}")

    # --- Monitor Principal ---
    secao(f"🖥  MONITOR PRINCIPAL — {EDP_OUTPUT}")
    pct, atual, maximo = get_backlight_percent()
    if pct is not None:
        campo("Brilho", f"{YELLOW}{pct}%{RESET} {DIM}({atual}/{maximo}){RESET}")
    else:
        campo("Brilho", f"{DIM}indisponível{RESET}")

    gamma_edp, _ = get_output_state(EDP_OUTPUT)
    campo("Gamma", gamma_edp or f"{DIM}indisponível{RESET}")
    # Nota: "Brightness:" do xrandr para o eDP-1 é ignorado de propósito —
    # o backlight da tela interna não é controlado via xrandr --brightness,
    # então esse valor não reflete o brilho real (fica sempre travado em 1.0).

    # --- Monitor Externo ---
    secao(f"🖵  MONITOR EXTERNO — {HDMI_OUTPUT}")
    gamma_hdmi_raw, brightness_hdmi = get_output_state(HDMI_OUTPUT)
    gamma_hdmi = invert_gamma(gamma_hdmi_raw)
    if brightness_hdmi is not None:
        campo("Brilho", f"{YELLOW}{round(brightness_hdmi * 100)}%{RESET} {DIM}({brightness_hdmi:.3f}){RESET}")
    else:
        campo("Brilho", f"{DIM}indisponível{RESET}")
    campo("Gamma", gamma_hdmi or f"{DIM}indisponível (monitor desconectado?){RESET}")

    # --- Log recente ---
    secao("📋 LOG RECENTE", linha_acima=True)
    for l in get_recent_log():
        print(f"  {GREEN}{l}{RESET}")

    print()


if __name__ == "__main__":
    main()
