import plotly.graph_objects as go

data = [
    {"periodo": "Madrugada", "hora": "00:00–07:00", "brilho": 1000, "temp": 2700, "hdmi": 0.45, "cor": "#ffb366"},
    {"periodo": "Manhã", "hora": "07:00–12:00", "brilho": 9060, "temp": 4500, "hdmi": 0.8, "cor": "#ffd480"},
    {"periodo": "Tarde", "hora": "12:00–17:30", "brilho": 14400, "temp": 6500, "hdmi": 1.0, "cor": "#ffffff"},
    {"periodo": "Noite", "hora": "17:30–00:00", "brilho": 4000, "temp": 3500, "hdmi": 0.55, "cor": "#ff9966"}
]

fig = go.Figure()

fig.add_trace(go.Scatter(
    x=[d["temp"] for d in data],
    y=[d["brilho"] for d in data],
    mode="lines+markers",
    name="Brilho (lux aproximado)",
    line=dict(color="orange", width=3)
))

fig.add_trace(go.Scatter(
    x=[d["temp"] for d in data],
    y=[d["hdmi"] for d in data],
    mode="lines+markers",
    name="Fator HDMI",
    yaxis="y2",
    line=dict(color="blue", width=3, dash="dot")
))

fig.update_layout(
    title="Ciclo Diário — Temperatura de Cor, Brilho e Fator HDMI",
    xaxis=dict(title="Temperatura de Cor (K)", tickvals=[2700, 3500, 4500, 6500]),
    yaxis=dict(title="Brilho (unidade relativa)"),
    yaxis2=dict(title="Fator HDMI", overlaying="y", side="right", range=[0.4, 1.05]),
    legend=dict(x=0.02, y=0.98),
    hovermode="x unified",
)

for d in data:
    fig.add_annotation(
        x=d["temp"],
        y=d["brilho"],
        text=f"{d['periodo']}<br>{d['hora']}",
        showarrow=True,
        arrowhead=2,
        ax=0,
        ay=-40,
        bgcolor=d["cor"],
        bordercolor="gray"
    )

fig.show()
