"""Vẽ sơ đồ kiến trúc, luồng hoạt động và ERD bằng Graphviz -> docs/assets/*.png

Chạy:  pip install graphviz   (và cài Graphviz: https://graphviz.org/download/)
       python diagrams.py
"""
import graphviz
import config as C

FONT = "Liberation Sans"      # đổi thành "Arial" nếu chạy trên Windows
INK, TEAL, AMBER, MIST, RED = "#12303B", "#0E7C86", "#F2A541", "#E6F2F3", "#C8553D"

def _g(name, rankdir="TB", **kw):
    g = graphviz.Digraph(name, format="png")
    g.attr(rankdir=rankdir, dpi="200", bgcolor="white", fontname=FONT, pad="0.3", **kw)
    g.attr("node", fontname=FONT, fontsize="13", color=INK, penwidth="1.4")
    g.attr("edge", fontname=FONT, fontsize="11", color=INK, penwidth="1.3")
    return g

def activity_diagram():
    g = _g("activity", nodesep="0.35", ranksep="0.38")
    g.node("start", "", shape="circle", style="filled", fillcolor=INK, width="0.25")
    g.node("end", "", shape="doublecircle", style="filled", fillcolor=INK, width="0.22")
    act = dict(shape="box", style="rounded,filled", fillcolor=MIST)
    g.node("ev", "App / SDK gửi event", **act)
    g.node("val", "validation.py\nKiểm tra schema, trùng, timestamp", **act)
    g.node("ok", "Event hợp lệ?", shape="diamond", style="filled", fillcolor=AMBER)
    g.node("bad", "Ghi vào bảng event lỗi\n(báo cáo chất lượng dữ liệu)", shape="box", style="rounded,filled", fillcolor="#F6D5CC")
    g.node("store", "Event store", shape="cylinder", style="filled", fillcolor="white")
    g.node("fork", "", shape="box", style="filled", fillcolor=INK, height="0.06", width="5.4")
    g.node("seg", "segmentation.py\nFeature → chuẩn hoá → KMeans\n→ đặt tên segment", **act)
    g.node("jou", "journey.py\nSession hoá → path → funnel\n→ ma trận chuyển bước", **act)
    g.node("ale", "alerting.py\nMetric theo ngày → baseline cùng thứ\n→ robust z-score", **act)
    g.node("join", "", shape="box", style="filled", fillcolor=INK, height="0.06", width="5.4")
    g.node("ctx", "ai_summary.py · build_context()\nGom số liệu thật thành JSON", **act)
    g.node("sev", "Có cảnh báo?", shape="diamond", style="filled", fillcolor=AMBER)
    g.node("push", "Gửi cảnh báo\n(Slack / Email)", shape="box", style="rounded,filled", fillcolor="#F6D5CC")
    g.node("llm", "LLM tóm tắt, nêu giả thuyết, brief A/B\n(không có API key → template offline)", **act)
    g.node("dash", "Dashboard theo vai trò\nProduct / Marketing / Admin", **act)

    g.edge("start", "ev"); g.edge("ev", "val"); g.edge("val", "ok")
    g.edge("ok", "bad", label=" Không"); g.edge("bad", "end", style="dashed", constraint="false")
    g.edge("ok", "store", label=" Có"); g.edge("store", "fork")
    for n in ("seg", "jou", "ale"):
        g.edge("fork", n); g.edge(n, "join")
    g.edge("join", "ctx"); g.edge("ctx", "sev")
    g.edge("sev", "push", label=" Có"); g.edge("sev", "llm", label=" Không")
    g.edge("push", "llm"); g.edge("llm", "dash"); g.edge("dash", "end")
    g.render(str(C.ASSETS_DIR / "flow"), cleanup=True)

def architecture_diagram():
    g = _g("arch", rankdir="LR", nodesep="0.3", ranksep="0.55")
    box = dict(shape="box", style="rounded,filled", fillcolor=MIST)
    with g.subgraph(name="cluster_in") as c:
        c.attr(label="Thu thập", style="rounded", color=TEAL, fontname=FONT, fontcolor=TEAL)
        c.node("sdk", "SDK / Event schema", **box); c.node("val", "Validation", **box)
    with g.subgraph(name="cluster_store") as c:
        c.attr(label="Lưu trữ", style="rounded", color=TEAL, fontname=FONT, fontcolor=TEAL)
        c.node("db", "Event store\n(CSV → PostgreSQL)", shape="cylinder", style="filled", fillcolor="white")
    with g.subgraph(name="cluster_an") as c:
        c.attr(label="Phân tích (phần được giao)", style="rounded,filled", fillcolor="#FFF3DE", color=AMBER, fontname=FONT, fontcolor=INK)
        c.node("seg", "Segmentation\nKMeans + RFM", **box)
        c.node("jou", "Journey\nSession · Funnel · Markov", **box)
        c.node("ale", "Alerting\nRobust z-score", **box)
    with g.subgraph(name="cluster_ai") as c:
        c.attr(label="AI", style="rounded", color=TEAL, fontname=FONT, fontcolor=TEAL)
        c.node("ctx", "Context JSON", **box); c.node("llm", "Claude API\n/ template", **box)
    with g.subgraph(name="cluster_out") as c:
        c.attr(label="Đầu ra", style="rounded", color=TEAL, fontname=FONT, fontcolor=TEAL)
        c.node("dash", "Dashboard\ntheo vai trò", **box); c.node("notif", "Cảnh báo\nSlack / Email", **box)
    g.edge("sdk", "val"); g.edge("val", "db")
    for n in ("seg", "jou", "ale"):
        g.edge("db", n); g.edge(n, "ctx")
    g.edge("ctx", "llm"); g.edge("llm", "dash"); g.edge("ale", "notif", style="dashed")
    g.edge("seg", "jou", label=" funnel theo segment", style="dotted", constraint="false")
    g.render(str(C.ASSETS_DIR / "architecture"), cleanup=True)

def erd():
    g = _g("erd", rankdir="LR", nodesep="0.45", ranksep="0.9")
    g.attr("node", shape="plaintext")
    def table(name, pk, cols, head=TEAL):
        rows = "".join(f'<TR><TD ALIGN="LEFT" PORT="{c.split()[0]}">{c}</TD></TR>' for c in cols)
        return (f'<<TABLE BORDER="1" CELLBORDER="0" CELLSPACING="0" CELLPADDING="5" BGCOLOR="white">'
                f'<TR><TD BGCOLOR="{head}"><FONT COLOR="white"><B>{name}</B></FONT></TD></TR>'
                f'<TR><TD ALIGN="LEFT"><B>{pk}</B></TD></TR>{rows}</TABLE>>')
    g.node("USER", table("USER", "PK user_id", ["platform", "first_seen"]))
    g.node("SESSION", table("SESSION", "PK session_id", ["FK user_id", "started_at", "ended_at"]))
    g.node("EVENT", table("EVENT", "PK event_id", ["FK user_id", "FK session_id", "event_name", "timestamp", "platform"]))
    g.node("SEGMENT", table("SEGMENT", "PK segment_id", ["name", "model_version"], head=AMBER))
    g.node("SNAP", table("SEGMENT_SNAPSHOT", "PK snapshot_id", ["FK user_id", "FK segment_id", "snapshot_date"], head=AMBER))
    g.node("METRIC", table("METRIC_DAILY", "PK date + scope", ["dau", "events", "purchases"], head=RED))
    g.node("ALERT", table("ALERT", "PK alert_id", ["FK metric (date, scope)", "drop_pct", "z_score", "severity"], head=RED))
    g.node("REPORT", table("INSIGHT_REPORT", "PK report_id", ["ai_summary", "created_at"], head=INK))
    g.edge("USER", "SESSION", label=" 1 — N"); g.edge("SESSION", "EVENT", label=" 1 — N")
    g.edge("USER", "EVENT", label=" 1 — N", style="dashed")
    g.edge("USER", "SNAP", label=" 1 — N"); g.edge("SEGMENT", "SNAP", label=" 1 — N")
    g.edge("METRIC", "ALERT", label=" 1 — N"); g.edge("ALERT", "REPORT", label=" N — N", style="dashed")
    g.edge("SEGMENT", "REPORT", label=" N — N", style="dashed")
    g.render(str(C.ASSETS_DIR / "erd"), cleanup=True)

if __name__ == "__main__":
    activity_diagram(); architecture_diagram(); erd()
    print("Đã vẽ: docs/assets/flow.png, architecture.png, erd.png")
