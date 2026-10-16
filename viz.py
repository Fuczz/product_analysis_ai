"""Biểu đồ Plotly tương tác - dùng chung cho app.py và build_site.py."""
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler
import segmentation as S

INK, TEAL, AMBER, RED, MIST = "#12303B", "#0E7C86", "#F2A541", "#C8553D", "#E6F2F3"
PALETTE = [TEAL, AMBER, RED, "#6C5B7B", "#4C78A8", "#59A14F"]
FONT = dict(family="Segoe UI, Roboto, Helvetica, Arial, sans-serif", color=INK, size=13)

def _base(fig, title, height=420):
    fig.update_layout(title=dict(text=title, x=0.01, font=dict(size=17)), height=height,
                      font=FONT, paper_bgcolor="white", plot_bgcolor="white",
                      margin=dict(l=50, r=20, t=60, b=50),
                      legend=dict(orientation="h", y=-0.2))
    fig.update_xaxes(gridcolor="#E7EEF0", zeroline=False)
    fig.update_yaxes(gridcolor="#E7EEF0", zeroline=False)
    return fig

def fig_silhouette(sil: dict, chosen_k: int):
    ks = list(sil)
    colors = [AMBER if k == chosen_k else TEAL for k in ks]
    fig = go.Figure(go.Bar(x=[f"k={k}" for k in ks], y=[sil[k] for k in ks],
                           marker_color=colors, text=[f"{sil[k]:.3f}" for k in ks],
                           textposition="outside"))
    fig.update_yaxes(range=[0, max(sil.values()) * 1.2])
    return _base(fig, "Chọn số cụm k bằng silhouette (cao hơn = tách cụm tốt hơn)", 340)

def fig_segments_pca(seg: pd.DataFrame, max_points: int = 1200):
    """Chiếu các đặc trưng của user xuống 2 chiều (PCA) để nhìn thấy các cụm."""
    X = StandardScaler().fit_transform(np.log1p(seg[S.CLUSTER_FEATURES]))
    xy = PCA(2, random_state=0).fit_transform(X)
    d = pd.DataFrame(xy, columns=["pc1", "pc2"], index=seg.index)
    d["segment"] = seg["segment"]
    d = d.sample(min(max_points, len(d)), random_state=0)
    fig = go.Figure()
    for i, (name, g) in enumerate(d.groupby("segment")):
        fig.add_trace(go.Scatter(x=g.pc1, y=g.pc2, mode="markers", name=name,
                                 marker=dict(size=6, opacity=.65, color=PALETTE[i % len(PALETTE)])))
    fig.update_xaxes(title="PC1"); fig.update_yaxes(title="PC2")
    return _base(fig, "Bản đồ người dùng theo segment (PCA 2 chiều)", 460)

def fig_segment_share(prof: pd.DataFrame):
    p = prof.sort_values("users")
    fig = go.Figure(go.Bar(y=p.index, x=p["users"], orientation="h", marker_color=TEAL,
                           text=[f"{v}%" for v in p["share_%"]], textposition="outside"))
    fig.update_xaxes(range=[0, p["users"].max() * 1.25])
    return _base(fig, "Số user theo segment", 340)

def fig_funnel(fun: pd.DataFrame):
    fig = go.Figure(go.Funnel(y=fun.step, x=fun.sessions, textinfo="value+percent previous",
                              marker=dict(color=[TEAL, "#2A93A0", "#56ABB4", AMBER, RED][:len(fun)])))
    return _base(fig, "Funnel theo session (số session, % so với bước trước)", 400)

def fig_funnel_by_segment(fs: pd.DataFrame):
    fig = go.Figure(go.Heatmap(z=fs.values, x=list(fs.columns), y=list(fs.index),
                               colorscale=[[0, MIST], [1, TEAL]], text=fs.values, texttemplate="%{text:.1f}%",
                               colorbar=dict(title="%")))
    return _base(fig, "% session đạt từng bước, theo segment (tính từ app_open)", 340)

def fig_transition(tm: pd.DataFrame):
    fig = go.Figure(go.Heatmap(z=tm.values, x=list(tm.columns), y=list(tm.index),
                               colorscale=[[0, "white"], [1, AMBER]], text=tm.values,
                               texttemplate="%{text:.2f}", colorbar=dict(title="P")))
    fig.update_yaxes(autorange="reversed", title="Từ event")
    fig.update_xaxes(title="Sang event")
    return _base(fig, "Ma trận chuyển bước (xác suất event A → event B)", 460)

def fig_sankey(paths: pd.Series, max_steps: int = 5, top_n_paths: int = 400):
    """Sankey các bước đầu của session. Node theo (thứ tự bước, event) nên không có chu trình."""
    from collections import Counter
    links = Counter()
    for p in paths.sample(min(len(paths), 20000), random_state=0):
        seq = list(p)[:max_steps]
        seq = seq + (["Rời đi"] if len(p) <= max_steps else [])
        for i, (a, b) in enumerate(zip(seq[:-1], seq[1:])):
            links[((i, a), (i + 1, b))] += 1
    links = {k: v for k, v in links.items() if v >= 15}
    nodes = sorted({n for k in links for n in k})
    idx = {n: i for i, n in enumerate(nodes)}
    fig = go.Figure(go.Sankey(
        node=dict(label=[f"{n[1]}" for n in nodes], pad=14, thickness=16,
                  color=[RED if n[1] == "Rời đi" else TEAL for n in nodes]),
        link=dict(source=[idx[a] for a, b in links], target=[idx[b] for a, b in links],
                  value=list(links.values()), color="rgba(14,124,134,0.25)")))
    return _base(fig, "Hành trình người dùng trong session (5 bước đầu)", 480)

def fig_dau(by_platform: pd.DataFrame, alerts: list):
    fig = go.Figure()
    for i, c in enumerate(by_platform.columns):
        fig.add_trace(go.Scatter(x=by_platform.index, y=by_platform[c], name=c, mode="lines",
                                 line=dict(width=2.2, color=PALETTE[i % len(PALETTE)])))
    a_dau = [a for a in alerts if a.metric == "dau" and a.scope.startswith("platform=")]
    for a in a_dau:
        plat = a.scope.split("=")[1]
        if plat in by_platform.columns:
            fig.add_trace(go.Scatter(
                x=[a.date], y=[a.value], mode="markers", showlegend=False,
                marker=dict(size=13, color=RED, symbol="x", line=dict(width=1, color="white")),
                hovertemplate=f"<b>{a.severity}</b><br>{a.scope}<br>{a.date.date()}<br>"
                              f"DAU {a.value:.0f} vs baseline {a.baseline:.0f}<br>"
                              f"giảm {a.drop_pct}% (z={a.z})<extra></extra>"))
    fig.update_yaxes(title="DAU")
    return _base(fig, "DAU theo nền tảng - dấu ✕ đỏ là cảnh báo", 440)

def fig_alert_baseline(overall_series: pd.Series, weeks_back: int = 4):
    """Minh hoạ baseline cùng thứ: đường thực tế so với trung vị 4 tuần trước cùng thứ."""
    s = overall_series.asfreq("D", fill_value=0)
    base = pd.Series([np.median([s.iloc[i - 7 * k] for k in range(1, weeks_back + 1)])
                      if i >= 7 * weeks_back else np.nan for i in range(len(s))], index=s.index)
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=s.index, y=s, name="DAU thực tế", line=dict(color=TEAL, width=2.4)))
    fig.add_trace(go.Scatter(x=base.index, y=base, name="Baseline (trung vị cùng thứ)",
                             line=dict(color=AMBER, width=2, dash="dash")))
    return _base(fig, "DAU toàn hệ thống so với baseline cùng thứ", 380)
