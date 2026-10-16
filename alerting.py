"""PHẦN 3 - CẢNH BÁO engagement giảm bất thường.

Phương pháp: so sánh giá trị hôm nay với 'baseline cùng thứ trong các tuần trước'
(để loại ảnh hưởng mùa vụ theo thứ) và dùng robust z-score (median + MAD) để
không bị outlier làm nhiễu. Có cooldown để tránh spam cảnh báo.
"""
from dataclasses import dataclass
import numpy as np
import pandas as pd

@dataclass
class Alert:
    date: pd.Timestamp
    metric: str
    scope: str
    value: float
    baseline: float
    drop_pct: float
    z: float
    severity: str

def daily_metrics(events: pd.DataFrame, by: str | None = None) -> pd.DataFrame:
    e = events.assign(date=events["timestamp"].dt.normalize())
    keys = ["date"] if by is None else ["date", by]
    out = e.groupby(keys).agg(dau=("user_id", "nunique"), events=("event_id", "count"),
                              purchases=("event_name", lambda s: (s == "purchase").sum()))
    return out

def robust_z(x, history):
    med = np.median(history)
    # 1.4826: đưa MAD về cùng thang với độ lệch chuẩn
    mad = np.median(np.abs(history - med)) * 1.4826
    mad = max(mad, 0.05 * med, 1e-9)   # sàn chống chia cho 0
    return (x - med) / mad, med

def detect_drops(series: pd.Series, metric: str, scope: str = "all",
                 weeks_back: int = 4, z_thresh: float = -3.0, min_drop_pct: float = 20.0,
                 cooldown_days: int = 3) -> list[Alert]:
    series = series.asfreq("D", fill_value=0)
    alerts, last_alert = [], None
    for i in range(7 * weeks_back, len(series)):
        day, x = series.index[i], series.iloc[i]
        # baseline = cùng thứ trong các tuần trước
        hist = np.array([series.iloc[i - 7 * k]
                         for k in range(1, weeks_back + 1)])
        z, base = robust_z(x, hist)
        drop = (base - x) / base * 100 if base > 0 else 0
        if z <= z_thresh and drop >= min_drop_pct:
            if last_alert is not None and \
               (day - last_alert).days <= cooldown_days:
                continue
            sev = "CRITICAL" if drop >= 40 or z <= -6 else "WARNING"
            alerts.append(Alert(day, metric, scope, float(x), float(base),
                                round(drop, 1), round(float(z), 1), sev))
            last_alert = day
    return alerts

def run_alerts(events: pd.DataFrame, **kw) -> list[Alert]:
    alerts = []
    overall = daily_metrics(events)
    for m in ["dau", "events"]:
        alerts += detect_drops(overall[m], m, "toàn hệ thống", **kw)
    by_p = daily_metrics(events, by="platform")
    for platform, sub in by_p.groupby(level="platform"):
        s = sub.droplevel("platform")["dau"]
        alerts += detect_drops(s, "dau", f"platform={platform}", **kw)
    return sorted(alerts, key=lambda a: (a.date, a.scope))
