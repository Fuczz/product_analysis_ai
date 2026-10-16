"""Pipeline dùng chung cho main.py, app.py (Streamlit) và build_site.py (web tĩnh)."""
import pandas as pd
import config as C
from generate_data import generate_events
from validation import validate_events
import segmentation as S
import journey as J
import alerting as A
import ai_summary as AI

def run_pipeline(n_users: int = C.N_USERS, k: int = C.N_CLUSTERS,
                 session_gap: int = C.SESSION_GAP_MINUTES,
                 z_thresh: float = -3.0, weeks_back: int = 4,
                 min_drop_pct: float = 20.0, cooldown_days: int = 3,
                 events: pd.DataFrame | None = None, seed: int = C.SEED,
                 inject_dirty: bool = False) -> dict:
    """events=None -> sinh dữ liệu giả lập; hoặc truyền DataFrame event của bạn
    (cột: event_id, user_id, event_name, timestamp, platform)."""
    true = None
    if events is None:
        C.N_USERS = n_users
        events, true = generate_events(seed)
        if inject_dirty:     # chèn vài event bẩn để chứng minh validation
            events = pd.concat([events, pd.DataFrame([
                {"event_id": "bad1", "user_id": 1, "event_name": "hack_event", "timestamp": "2026-08-02", "platform": "web"},
                {"event_id": "bad2", "user_id": 2, "event_name": "purchase", "timestamp": "not-a-date", "platform": "web"},
                {"event_id": events.event_id.iloc[0], "user_id": 3, "event_name": "purchase", "timestamp": "2026-08-02", "platform": "ios"},
            ])], ignore_index=True)
    events, errors = validate_events(events)

    feats = S.build_features(events)
    seg, sil = S.segment_users(feats, k=k)
    seg = S.name_segments(seg)
    prof = S.profile(seg)
    check = pd.crosstab(seg.segment, true.reindex(seg.index)) if true is not None else None

    e = J.sessionize(events, gap_minutes=session_gap)
    paths = J.session_paths(e)
    top = J.top_paths(paths, n=10)
    fun = J.funnel(e)
    fun_seg = J.funnel_by_segment(e, seg)
    trans = J.transition_matrix(paths)

    alerts = A.run_alerts(events, z_thresh=z_thresh, weeks_back=weeks_back,
                          min_drop_pct=min_drop_pct, cooldown_days=cooldown_days)
    overall = A.daily_metrics(events)
    by_platform = A.daily_metrics(events, by="platform")["dau"].unstack()

    ctx = AI.build_context(prof, fun, top, alerts)
    summary = AI.summarize(ctx)
    return dict(events=events, errors=errors, seg=seg, sil=sil, prof=prof, check=check,
                sessions=e, paths=paths, top=top, funnel=fun, funnel_seg=fun_seg,
                trans=trans, alerts=alerts, overall=overall, by_platform=by_platform,
                ctx=ctx, summary=summary)
