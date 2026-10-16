"""Dựng trang web tĩnh docs/index.html (dùng cho GitHub Pages) từ kết quả chạy THẬT.

Chạy:
    python build_site.py
    python build_site.py --repo https://github.com/<user>/<repo> --app https://<app>.streamlit.app
Sau đó bật GitHub Pages: Settings -> Pages -> Branch: main, thư mục /docs.
"""
import argparse, html, shutil
from pathlib import Path
import pandas as pd
import plotly
import config as C
from pipeline import run_pipeline
import viz

DOCS = C.BASE_DIR / "docs"
MODULES = [("config.py", "Cấu hình + event schema"), ("generate_data.py", "Sinh dữ liệu giả lập"),
           ("validation.py", "Validation event"), ("segmentation.py", "Segmentation"),
           ("journey.py", "Journey analysis"), ("alerting.py", "Cảnh báo"),
           ("ai_summary.py", "AI tóm tắt"), ("pipeline.py", "Pipeline dùng chung"),
           ("app.py", "App Streamlit"), ("diagrams.py", "Vẽ sơ đồ")]

CSS = """
:root{--ink:#12303B;--teal:#0E7C86;--amber:#F2A541;--red:#C8553D;--mist:#E6F2F3;--line:#D5E3E6}
*{box-sizing:border-box}html{scroll-behavior:smooth}
body{margin:0;font:16px/1.65 "Segoe UI",Roboto,Helvetica,Arial,sans-serif;color:var(--ink);background:#fff}
a{color:var(--teal)}
header.hero{background:var(--ink);color:#fff;padding:72px 24px 56px}
.wrap{max-width:1120px;margin:0 auto}
.hero h1{font-size:clamp(28px,5vw,46px);line-height:1.15;margin:0 0 14px}
.hero p{max-width:760px;color:#C9DDE1;font-size:18px;margin:0 0 28px}
.btns{display:flex;gap:12px;flex-wrap:wrap}
.btn{display:inline-block;padding:11px 20px;border-radius:8px;text-decoration:none;font-weight:600;border:1.5px solid #fff;color:#fff}
.btn.primary{background:var(--amber);border-color:var(--amber);color:var(--ink)}
nav{position:sticky;top:0;background:#fff;border-bottom:1px solid var(--line);z-index:5}
nav{padding:0 24px}nav .wrap{display:flex;gap:6px;overflow-x:auto;padding:10px 0}nav a:first-child{margin-left:-14px}
nav a{white-space:nowrap;padding:6px 14px;border-radius:999px;text-decoration:none;color:var(--ink);font-size:15px}
nav a:hover{background:var(--mist)}
section{padding:56px 24px}section:nth-of-type(even){background:#F7FBFB}
h2{font-size:30px;margin:0 0 8px}h3{font-size:20px;margin:28px 0 8px}
.lead{color:#4B6A73;margin:0 0 28px;max-width:760px}
.grid{display:grid;gap:18px}.g3{grid-template-columns:repeat(auto-fit,minmax(260px,1fr))}
.g4{grid-template-columns:repeat(auto-fit,minmax(200px,1fr))}
.card{background:#fff;border:1px solid var(--line);border-radius:14px;padding:20px 22px}
.card h4{margin:0 0 6px;font-size:18px}.card p{margin:0;color:#3F5D66}
.kpi{text-align:left}.kpi b{display:block;font-size:34px;color:var(--teal);line-height:1.1}
.kpi span{color:#4B6A73;font-size:14px}
figure{margin:0 0 22px;background:#fff;border:1px solid var(--line);border-radius:14px;padding:10px;overflow:hidden}
figure img{max-width:100%;height:auto;display:block;margin:0 auto}
figcaption{font-size:14px;color:#4B6A73;padding:8px 10px 2px}
.two{display:grid;gap:18px;grid-template-columns:repeat(auto-fit,minmax(420px,1fr))}
.two>*,.grid>*{min-width:0}
@media(max-width:560px){.two{grid-template-columns:1fr}}
.tw{overflow-x:auto}
table.t{border-collapse:collapse;width:100%;font-size:14px;background:#fff}
table.t th{background:var(--ink);color:#fff;text-align:left;padding:8px 10px;font-weight:600}
table.t td{padding:7px 10px;border-bottom:1px solid var(--line)}
table.t tr:nth-child(even) td{background:#F7FBFB}
pre{background:#10222B;color:#E6F2F3;padding:16px 18px;border-radius:10px;overflow:auto;font:13px/1.55 Consolas,"Courier New",monospace;margin:0}
details{background:#fff;border:1px solid var(--line);border-radius:10px;margin:10px 0}
summary{cursor:pointer;padding:12px 16px;font-weight:600}
details pre{border-radius:0 0 10px 10px}
.sev-CRITICAL{color:var(--red);font-weight:700}.sev-WARNING{color:#B7791F;font-weight:700}
.note{background:#FFF6E5;border:1px solid #F2D9A6;border-radius:10px;padding:14px 18px}
footer{background:var(--ink);color:#C9DDE1;padding:28px 24px;font-size:14px}
code.i{background:var(--mist);padding:2px 6px;border-radius:5px;font-size:.92em}
"""

def table(df, index=True, classes="t"):
    return '<div class="tw">' + df.to_html(classes=classes, border=0, index=index, escape=True) + "</div>"

def fig_html(fig):
    return fig.to_html(full_html=False, include_plotlyjs=False,
                       config={"displaylogo": False, "responsive": True})

def img(name, cap):
    return f'<figure><img src="assets/{name}" alt="{html.escape(cap)}"><figcaption>{html.escape(cap)}</figcaption></figure>'

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default="", help="URL repo GitHub")
    ap.add_argument("--app", default="", help="URL app Streamlit đã deploy")
    a = ap.parse_args()

    R = run_pipeline(inject_dirty=True)
    ev, prof, fun = R["events"], R["prof"], R["funnel"]
    DOCS.mkdir(exist_ok=True); (DOCS / "assets").mkdir(exist_ok=True)
    shutil.copy(Path(plotly.__file__).parent / "package_data" / "plotly.min.js", DOCS / "assets" / "plotly.min.js")

    worst = fun.dropna().sort_values("drop_off_%", ascending=False).iloc[0]
    alert_rows = pd.DataFrame([{
        "Ngày": x.date.date(), "Mức": f'<span class="sev-{x.severity}">{x.severity}</span>',
        "Metric": x.metric, "Phạm vi": x.scope, "Thực tế": int(x.value), "Baseline": int(x.baseline),
        "Giảm": f"{x.drop_pct}%", "z": x.z} for x in R["alerts"]])
    alert_tbl = ('<div class="tw">' + alert_rows.to_html(classes="t", border=0, index=False, escape=False) + "</div>")

    btns = []
    if a.app: btns.append(f'<a class="btn primary" href="{html.escape(a.app)}">▶ Chạy app trực tiếp</a>')
    if a.repo: btns.append(f'<a class="btn" href="{html.escape(a.repo)}">Mã nguồn trên GitHub</a>')
    btns.append('<a class="btn" href="#ket-qua">Xem kết quả</a>')

    code_blocks = "".join(
        f'<details><summary><code class="i">{n}</code> — {d}</summary>'
        f'<pre>{html.escape((C.BASE_DIR / n).read_text(encoding="utf-8"))}</pre></details>'
        for n, d in MODULES if (C.BASE_DIR / n).exists())

    page = f"""<!doctype html><html lang="vi"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Product Analytics + AI · Segmentation, Journey, Cảnh báo</title>
<meta name="description" content="Demo Python: phân nhóm người dùng, phân tích hành trình và cảnh báo engagement giảm bất thường.">
<style>{CSS}</style>
<script src="assets/plotly.min.js"></script></head><body>
<header class="hero"><div class="wrap">
<h1>Product Analytics có AI tóm tắt hành vi người dùng</h1>
<p>Ba kỹ thuật cốt lõi — <b>Segmentation</b>, <b>Journey analysis</b> và <b>cảnh báo engagement giảm bất thường</b> —
cài đặt bằng Python, chạy trên dữ liệu giả lập và hiển thị bằng biểu đồ tương tác. Mọi số liệu trên trang này
được sinh ra từ chính mã nguồn trong repo.</p>
<div class="btns">{"".join(btns)}</div></div></header>
<nav><div class="wrap"><a href="#van-de">Vấn đề</a><a href="#thiet-ke">Thiết kế</a><a href="#ket-qua">Kết quả</a>
<a href="#canh-bao">Cảnh báo</a><a href="#ai">AI tóm tắt</a><a href="#ma-nguon">Mã nguồn</a><a href="#chay-thu">Chạy thử</a><a href="#han-che">Hạn chế</a></div></nav>

<section id="van-de"><div class="wrap">
<h2>Vấn đề và mục tiêu</h2>
<p class="lead">Chỉ nhìn tổng DAU hay doanh thu thì không biết ai đang dùng thế nào, họ rơi ở đâu và khi nào có sự cố. Ba kỹ thuật này trả lời ba câu hỏi đó.</p>
<div class="grid g3">
<div class="card"><h4>👥 Segmentation — “Ai là ai?”</h4><p>Chia user thành nhóm có hành vi giống nhau (RFM + hành vi, K-Means) để cá nhân hoá thay vì một chiến dịch cho tất cả.</p></div>
<div class="card"><h4>🧭 Journey — “Đi đường nào, rơi ở đâu?”</h4><p>Session hoá event, tìm đường đi phổ biến, funnel và ma trận chuyển bước để thấy điểm nghẽn.</p></div>
<div class="card"><h4>🚨 Cảnh báo — “Có gì bất thường?”</h4><p>So hôm nay với baseline cùng thứ, dùng median + MAD (robust z-score) để phát hiện sớm và chỉ ra giảm ở đâu.</p></div>
</div></div></section>

<section id="thiet-ke"><div class="wrap">
<h2>Thiết kế hệ thống</h2>
<p class="lead">Event đi qua validation vào event store, ba module phân tích chạy song song, kết quả được gom thành JSON cho AI diễn giải và đổ ra dashboard.</p>
{img("architecture.png", "Kiến trúc tổng thể")}
<div class="two">{img("flow.png", "Luồng hoạt động (activity diagram)")}{img("erd.png", "Mô hình dữ liệu (ERD)")}</div>
</div></section>

<section id="ket-qua"><div class="wrap">
<h2>Kết quả chạy thật</h2>
<p class="lead">Dữ liệu giả lập {ev.user_id.nunique():,} user trong {C.N_DAYS} ngày, có chèn sẵn một sự cố làm nền tảng Android giảm hoạt động ở cuối kỳ. Di chuột lên biểu đồ để xem chi tiết.</p>
<div class="grid g4" style="margin-bottom:26px">
<div class="card kpi"><b>{len(ev):,}</b><span>event hợp lệ (đã loại {len(R["errors"])} event sai schema)</span></div>
<div class="card kpi"><b>{len(R["paths"]):,}</b><span>session</span></div>
<div class="card kpi"><b>{worst["drop_off_%"]}%</b><span>mất ở bước → {worst["step"]} (điểm nghẽn lớn nhất)</span></div>
<div class="card kpi"><b>{len(R["alerts"])}</b><span>cảnh báo phát ra</span></div></div>

<h3>1 · Segmentation</h3>
<div class="two"><figure>{fig_html(viz.fig_segments_pca(R["seg"]))}</figure>
<figure>{fig_html(viz.fig_silhouette(R["sil"], C.N_CLUSTERS))}</figure></div>
{table(prof.reset_index(), index=False)}

<h3>2 · Journey analysis</h3>
<div class="two"><figure>{fig_html(viz.fig_funnel(fun))}</figure>
<figure>{fig_html(viz.fig_funnel_by_segment(R["funnel_seg"]))}</figure></div>
<figure>{fig_html(viz.fig_sankey(R["paths"]))}</figure>
<figure>{fig_html(viz.fig_transition(R["trans"]))}</figure>
<h3>Top đường đi phổ biến</h3>{table(R["top"], index=False)}
</div></section>

<section id="canh-bao"><div class="wrap">
<h2>Cảnh báo engagement giảm bất thường</h2>
<p class="lead">Ở mức toàn hệ thống DAU chỉ giảm khoảng một phần tư, nhưng khi chia theo nền tảng thì Android giảm hơn một nửa. Cảnh báo theo phạm vi giúp thấy đúng nguồn gốc sự cố.</p>
<figure>{fig_html(viz.fig_dau(R["by_platform"], R["alerts"]))}</figure>
<figure>{fig_html(viz.fig_alert_baseline(R["overall"]["dau"]))}</figure>
{alert_tbl}
</div></section>

<section id="ai"><div class="wrap">
<h2>AI tóm tắt</h2>
<p class="lead">AI chỉ nhận JSON số liệu đã tính sẵn và chỉ được diễn giải, không tự tính hay bịa số. Bản dưới đây là chế độ template offline; đặt <code class="i">ANTHROPIC_API_KEY</code> để gọi Claude thật.</p>
<pre>{html.escape(R["summary"])}</pre>
</div></section>

<section id="ma-nguon"><div class="wrap">
<h2>Mã nguồn</h2>
<p class="lead">Mỗi file một nhiệm vụ. Bấm để xem toàn bộ nội dung.</p>
{code_blocks}
</div></section>

<section id="chay-thu"><div class="wrap">
<h2>Chạy thử trên máy bạn</h2>
<div class="grid g3">
<div class="card"><h4>1 · Cài đặt</h4><pre>git clone &lt;URL repo&gt;
cd product-analytics-ai
pip install -r requirements.txt</pre></div>
<div class="card"><h4>2 · Chạy trực quan</h4><pre>streamlit run app.py</pre><p style="margin-top:10px">Chỉnh tham số, hoặc tải CSV event của bạn lên.</p></div>
<div class="card"><h4>3 · Chạy dòng lệnh</h4><pre>python main.py</pre><p style="margin-top:10px">In kết quả và lưu <code class="i">output/dashboard.png</code>.</p></div>
</div></div></section>

<section id="han-che"><div class="wrap">
<h2>Hạn chế cần nói thẳng</h2>
<div class="note"><ul style="margin:0;padding-left:20px">
<li>Dữ liệu là giả lập có chủ đích nên các nhóm dễ tách; trên dữ liệu thật kết quả sẽ nhiễu hơn. Trang này chứng minh cơ chế chạy được, không chứng minh độ chính xác ngoài thực tế.</li>
<li>Silhouette cao nhất ở k=3; với k=4 nhóm “xem nhiều, ít mua” bị gộp vào nhóm “thỉnh thoảng”. Tên segment đặt bằng luật cứng nên chưa ổn định.</li>
<li>Cooldown 3 ngày và ngưỡng z khiến số cảnh báo ít hơn số ngày thực sự giảm; cần tinh chỉnh bằng precision/recall trên sự cố đã biết.</li>
<li>Baseline cùng thứ chưa xử lý ngày lễ, đợt khuyến mãi.</li></ul></div>
</div></section>
<footer><div class="wrap">Dựng từ <code class="i">build_site.py</code> · đồ án môn Lập trình Python · MIT License</div></footer>
<script>
// Vẽ lại biểu đồ theo đúng độ rộng ô lưới sau khi trang đã bố cục xong
function fitPlots(){{document.querySelectorAll('.js-plotly-plot').forEach(function(d){{Plotly.Plots.resize(d)}})}}
window.addEventListener('load',function(){{fitPlots();setTimeout(fitPlots,400)}});
</script>
</body></html>"""
    (DOCS / "index.html").write_text(page, encoding="utf-8")
    (DOCS / ".nojekyll").write_text("")
    print(f"Đã dựng docs/index.html ({len(page)/1e6:.2f} MB)")

if __name__ == "__main__":
    main()
