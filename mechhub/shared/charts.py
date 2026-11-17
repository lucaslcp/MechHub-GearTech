"""Serviço compartilhado de Gráficos (Plotly).

As funções devolvem o gráfico em JSON; o template `base.html` desenha
qualquer elemento `<script type="application/json" class="mh-chart">`.
Assim todos os módulos usam o mesmo visual.
"""
import plotly.graph_objects as go

# Paleta "Oficina" (a mesma do CSS): grafite, laranja segurança, azul aço,
# cinza, vermelho (perdas) e verde. Em preto e branco as séries continuam
# distinguíveis pela posição e pelos rótulos de valor.
PALETTE = ["#2c313a", "#e8590c", "#2f6db5", "#8b929c", "#c92a2a", "#2b8a3e"]


def wrap_label(text, width: int = 18) -> str:
    """Quebra nomes longos em várias linhas (<br>) para os eixos dos gráficos."""
    words, lines, line = str(text).split(), [], ""
    for word in words:
        if line and len(line) + 1 + len(word) > width:
            lines.append(line)
            line = word
        else:
            line = f"{line} {word}".strip()
    lines.append(line)
    return "<br>".join(lines)


def _layout(fig: go.Figure, title: str, x_title: str = "", y_title: str = "") -> go.Figure:
    fig.update_layout(
        title={"text": title, "x": 0, "xanchor": "left", "font": {"size": 14, "color": "#16191f"}},
        template="plotly_white",
        colorway=PALETTE,
        font={"family": "IBM Plex Sans, Segoe UI, system-ui, sans-serif", "size": 12, "color": "#2c313a"},
        margin={"l": 60, "r": 24, "t": 56, "b": 48},
        legend={"orientation": "h", "y": -0.2},
        hovermode="x unified",
        height=360,
        separators=",.",  # vírgula decimal e ponto de milhar (padrão brasileiro)
    )
    fig.update_xaxes(title_text=x_title, showgrid=False, linecolor="#d6d7d3")
    fig.update_yaxes(title_text=y_title, gridcolor="#ecece9", zerolinecolor="#d6d7d3", rangemode="tozero")
    return fig


def bar_chart(categories, values, title, y_title="", x_title="", color=PALETTE[0], text_format=".2f") -> str:
    fig = go.Figure(go.Bar(x=[wrap_label(c) for c in categories], y=list(values), marker_color=color,
                           texttemplate=f"%{{y:{text_format}}}", textposition="outside", cliponaxis=False))
    _layout(fig, title, x_title, y_title)
    fig.update_layout(hovermode="closest")
    return fig.to_json()


def grouped_bar_chart(categories, series: dict, title, y_title="", x_title="") -> str:
    fig = go.Figure()
    for name, values in series.items():
        fig.add_trace(go.Bar(name=name, x=[wrap_label(c) for c in categories], y=list(values)))
    _layout(fig, title, x_title, y_title)
    fig.update_layout(barmode="group", hovermode="closest")
    return fig.to_json()


def line_chart(x, series: dict, title, x_title="", y_title="", markers=True) -> str:
    fig = go.Figure()
    for name, values in series.items():
        fig.add_trace(go.Scatter(name=name, x=list(x), y=list(values),
                                 mode="lines+markers" if markers else "lines"))
    _layout(fig, title, x_title, y_title)
    return fig.to_json()


def dual_axis_chart(x, left: tuple, right: tuple, title, x_title="", kind_left="bar") -> str:
    """Duas grandezas com unidades diferentes no mesmo gráfico.

    `left` e `right` são tuplas (nome, valores, título_do_eixo).
    """
    l_name, l_values, l_axis = left
    r_name, r_values, r_axis = right
    fig = go.Figure()
    if kind_left == "bar":
        fig.add_trace(go.Bar(name=l_name, x=list(x), y=list(l_values), marker_color=PALETTE[0]))
    else:
        fig.add_trace(go.Scatter(name=l_name, x=list(x), y=list(l_values), mode="lines", line={"color": PALETTE[0]}))
    fig.add_trace(go.Scatter(name=r_name, x=list(x), y=list(r_values), yaxis="y2",
                             mode="lines+markers", line={"color": PALETTE[1], "width": 3}))
    _layout(fig, title, x_title, l_axis)
    fig.update_layout(yaxis2={"title": {"text": r_axis}, "overlaying": "y", "side": "right", "showgrid": False,
                               "rangemode": "tozero"},
                      margin={"l": 60, "r": 64, "t": 56, "b": 48})
    return fig.to_json()


def waterfall_chart(labels, values, title, y_title="") -> str:
    """Primeiro valor absoluto e os demais como variações (ex.: perdas de potência)."""
    measures = ["absolute"] + ["relative"] * (len(values) - 2) + ["total"]
    fig = go.Figure(go.Waterfall(
        x=list(labels), y=list(values), measure=measures,
        decreasing={"marker": {"color": PALETTE[4]}},
        increasing={"marker": {"color": PALETTE[2]}},
        totals={"marker": {"color": PALETTE[0]}},
        texttemplate="%{y:.3f}", textposition="outside", cliponaxis=False,
    ))
    _layout(fig, title, "", y_title)
    fig.update_layout(hovermode="closest", showlegend=False)
    return fig.to_json()
