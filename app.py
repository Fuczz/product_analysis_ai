"""Streamlit app: chạy trực quan Segmentation, Journey, Alerting.

Chạy:  streamlit run app.py
"""
import pandas as pd
import streamlit as st
import config as C
from pipeline import run_pipeline
import viz

st.set_page_config(page_title="Product Analytics + AI", page_icon="📈", layout="wide")
st.title("📈 Product Analytics + AI tóm tắt hành vi người dùng")
st.caption("Segmentation · Journey analysis · Cảnh báo engagement giảm bất thường")

# ---------- Sidebar: tham số ----------
with st.sidebar:
    st.header("Nguồn dữ liệu")
    up = st.file_uploader("Tải CSV event của bạn (tuỳ chọn)", type="csv",
                          help="Cột bắt buộc: " + ", ".join(C.EVENT_SCHEMA["required"]))
    st.download_button("Tải file CSV mẫu", data=b"event_id,user_id,event_name,timestamp,platform\n"
                       b"e1,1,app_open,2026-08-01 10:00:00,android\n",
                       file_name="events_mau.csv", mime="text/csv")
    st.header("Tham số")
    n_users = st.slider("Số user giả lập", 300, 3000, C.N_USERS, 100, disabled=up is not None)
    dirty = st.checkbox("Chèn vài event lỗi để thử validation", value=True, disabled=up is not None)
    k = st.slider("Số segment (k)", 2, 6, C.N_CLUSTERS)
    gap = st.slider("Khoảng lặng kết thúc session (phút)", 5, 120, C.SESSION_GAP_MINUTES, 5)
    st.subheader("Cảnh báo")
    z_thresh = st.slider("Ngưỡng robust z-score", -8.0, -1.5, -3.0, 0.5,
                         help="Càng âm càng khó báo (ít báo thừa).")
    weeks_back = st.slider("Số tuần dùng làm baseline", 2, 8, 4)
    min_drop = st.slider("Mức giảm tối thiểu (%)", 5, 60, 20, 5)
    cooldown = st.slider("Cooldown giữa 2 cảnh báo (ngày)", 0, 7, 3)

@st.cache_data(show_spinner="Đang chạy pipeline...")
def compute(n_users, k, gap, z_thresh, weeks_back, min_drop, cooldown, csv_bytes, dirty):
    ev = None
    if csv_bytes is not None:
        import io
        ev = pd.read_csv(io.BytesIO(csv_bytes))
    return run_pipeline(n_users=n_users, k=k, session_gap=gap, z_thresh=z_thresh,
                        weeks_back=weeks_back, min_drop_pct=min_drop,
                        cooldown_days=cooldown, events=ev, inject_dirty=dirty)

try:
    R = compute(n_users, k, gap, z_thresh, weeks_back, min_drop, cooldown,
                up.getvalue() if up else None, dirty)
except Exception as ex:
    st.error(f"Không chạy được pipeline: {ex}")
    st.stop()

# ---------- KPI ----------
ev = R["events"]
c1, c2, c3, c4 = st.columns(4)
c1.metric("Event hợp lệ", f"{len(ev):,}")
c2.metric("Số user", f"{ev.user_id.nunique():,}")
c3.metric("Số session", f"{len(R['paths']):,}")
c4.metric("Số cảnh báo", len(R["alerts"]))
if len(R["errors"]):
    st.warning(f"{len(R['errors'])} event bị loại do sai schema.")
    with st.expander("Xem event lỗi"):
        st.dataframe(R["errors"].head(200))

t1, t2, t3, t4, t5 = st.tabs(["👥 Segmentation", "🧭 Journey", "🚨 Cảnh báo", "🤖 AI tóm tắt", "📐 Sơ đồ"])

with t1:
    a, b = st.columns([3, 2])
    a.plotly_chart(viz.fig_segments_pca(R["seg"]), width="stretch")
    b.plotly_chart(viz.fig_silhouette(R["sil"], k), width="stretch")
    st.plotly_chart(viz.fig_segment_share(R["prof"]), width="stretch")
    st.subheader("Profile từng segment")
    st.dataframe(R["prof"], width="stretch")
    if R["check"] is not None:
        with st.expander("Đối chiếu với nhóm ẩn thật (chỉ có ở dữ liệu giả lập)"):
            st.dataframe(R["check"])

with t2:
    a, b = st.columns(2)
    a.plotly_chart(viz.fig_funnel(R["funnel"]), width="stretch")
    b.plotly_chart(viz.fig_funnel_by_segment(R["funnel_seg"]), width="stretch")
    st.plotly_chart(viz.fig_sankey(R["paths"]), width="stretch")
    st.plotly_chart(viz.fig_transition(R["trans"]), width="stretch")
    st.subheader("Top đường đi phổ biến")
    st.dataframe(R["top"], width="stretch")

with t3:
    st.plotly_chart(viz.fig_dau(R["by_platform"], R["alerts"]), width="stretch")
    st.plotly_chart(viz.fig_alert_baseline(R["overall"]["dau"], weeks_back), width="stretch")
    if R["alerts"]:
        st.dataframe(pd.DataFrame([{
            "Ngày": a.date.date(), "Mức": a.severity, "Metric": a.metric, "Phạm vi": a.scope,
            "Giá trị": a.value, "Baseline": a.baseline, "Giảm %": a.drop_pct, "z": a.z}
            for a in R["alerts"]]), width="stretch")
    else:
        st.info("Không có cảnh báo với tham số hiện tại - thử hạ ngưỡng z hoặc mức giảm tối thiểu.")

with t4:
    st.text(R["summary"])
    st.caption("Chưa đặt ANTHROPIC_API_KEY nên đang dùng bản tóm tắt template offline. "
               "Đặt biến môi trường ANTHROPIC_API_KEY để gọi Claude thật.")
    with st.expander("JSON số liệu gửi cho AI (AI chỉ diễn giải, không tự tính)"):
        st.json(R["ctx"])

with t5:
    for name, cap in [("flow", "Luồng hoạt động"), ("architecture", "Kiến trúc"), ("erd", "ERD")]:
        p = C.BASE_DIR / "docs" / "assets" / f"{name}.png"
        if p.exists():
            st.subheader(cap); st.image(str(p))
