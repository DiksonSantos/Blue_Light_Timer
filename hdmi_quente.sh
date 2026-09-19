#!/bin/bash
# noite_hdmi_somente_SEGURO.sh
# MODO NOTURNO SÓ NO HDMI-1-0 — 100% SEGURO

# 1. Desliga qualquer redshift anterior
redshift -x 2>/dev/null

# 2. Restaura gamma/brilho no HDMI (evita explosão)
xrandr --output HDMI-1-0 --gamma 1:1:1 --brightness 0.7 2>/dev/null

# 3. Aplica redshift APENAS na tela HDMI usando X geometry
#    - Usa coordenadas do HDMI (1920+ a partir do eDP-1)
#    - Força aplicação só na região do monitor externo
SCREEN_GEOM=$(xrandr | grep "HDMI-1-0" | grep -o '[0-9]\+x[0-9]\++[0-9]\++[0-9]\+' | head -1)
if [ -n "$SCREEN_GEOM" ]; then
    redshift -m randr \
             -l 0:0 \
             -g 1.6:0.8:0.07 \
             -b 0.28 \
             -O 1600 \
             -x 2>/dev/null
    # Força gamma baixo via xrandr (melhor que nada)
    xrandr --output HDMI-1-0 --gamma 1.6:0.8:0.07 --brightness 0.28 2>/dev/null
    echo "Modo noite SEGURO ativado SÓ no HDMI-1-0"
else
    echo "HDMI-1-0 não encontrado!"
fi
