#!/home/dikson//home/dikson/.virtualenvs/Testes/bin/python
# coding: utf-8

import plotly.graph_objects as go

data = [
    dict(temp=6500, gamma="1.0:1.0:1.0", r=1.0, g=1.0, b=1.0),
    dict(temp=4500, gamma="1.0:1.2:1.4", r=1.0, g=1.2, b=1.4),
    dict(temp=3500, gamma="1.0:1.3:1.9", r=1.0, g=1.3, b=1.9),
    dict(temp=2700, gamma="1.0:1.5:2.6", r=1.0, g=1.5, b=2.6),
]

fig = go.Figure()

fig.add_trace(go.Scatter(x=[d['temp'] for d in data], y=[d['r'] for d in data],
                         mode='lines+markers', name='R (Vermelho)', line=dict(color='red')))
fig.add_trace(go.Scatter(x=[d['temp'] for d in data], y=[d['g'] for d in data],
                         mode='lines+markers', name='G (Verde)', line=dict(color='green')))
fig.add_trace(go.Scatter(x=[d['temp'] for d in data], y=[d['b'] for d in data],
                         mode='lines+markers', name='B (Azul)', line=dict(color='blue')))

fig.update_layout(
    title="Gamma Real do Driver X11 (Medido com xrandr --verbose) × sct Temperature",
    xaxis=dict(title="Temperatura (sct, K)", tickmode='array', tickvals=[2700,3500,4500,6500]),
    yaxis=dict(title="Gamma (R:G:B)", range=[0.8, 2.8]),
    legend=dict(x=0.01, y=0.99),
    hovermode="x unified",
    annotations=[
        dict(x=temp, y=2.7, text=gamma, showarrow=False, font=dict(size=10))
        for temp, gamma in zip([d['temp'] for d in data], [d['gamma'] for d in data])
    ]
)

fig.show()


# conda install plotly -c conda-forge

"""
Temperatura (K):  2700    3500    4500    6500
Gamma R:         1.0     1.0     1.0     1.0
Gamma G:         1.5     1.3     1.2     1.0
Gamma B:         2.6     1.9     1.4     1.0
 """
