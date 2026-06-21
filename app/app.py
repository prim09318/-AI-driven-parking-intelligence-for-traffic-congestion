"""
EaseTraffic Command Center — FINAL MERGED
==========================================
Run: streamlit run app/streamlit_app.py

Changes applied from new code:
1. Marquee notice bar (25s, slower than old 40s scroll)
2. Session-state navigation — sidebar buttons + home cards both work
3. Overview Map kept from original (full featured)
4. Incident Logs — complete new page with log, update, history, stats
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
import folium, h3, json, ast, os, datetime, warnings, random, math
from pathlib import Path
from streamlit_folium import st_folium
from folium.plugins import HeatMap
from dotenv import load_dotenv
import google.generativeai as genai

load_dotenv()
warnings.filterwarnings("ignore")
random.seed(42)

# ── Paths ──────────────────────────────────────────────────────────────────
ROOT      = Path(__file__).resolve().parent.parent
PROCESSED = ROOT / "data" / "processed"

# ── Constants ──────────────────────────────────────────────────────────────
TIER_COLORS = {"Critical":"#e74c3c","High":"#e67e22","Medium":"#f1c40f",
               "Low":"#2ecc71","Very Low":"#3498db"}
TIER_ORDER  = ["Critical","High","Medium","Low","Very Low"]
DAY_ORDER   = ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]
SLOTS       = [(6,"06:00–14:00"),(14,"14:00–22:00"),(22,"22:00–06:00")]

DEVELOPERS  = ["Himanshu Gupta (primo9318)", "Team s8ul"]
PROJECT_VER = "v2.0 | Gridlock Hackathon 2.0"

NOTICES = [
    "[CRITICAL] Koramangala 2nd Block — 40% surge in double-parking this week. Deploy additional unit.",
    "[RESOLVED] KR Puram Main Road violation cluster cleared by patrol team. Violations down 65%.",
    "[HIGH ALERT] Shivajinagar junction violations up 28%. Patrol recommended 08:00–10:00 IST.",
    "[UPDATE] Outer Ring Road (Kadubisanahalli) enters Wildcard watch — 22 violations in last 14 days.",
    "[NOTICE] Weekend patrol coverage increased for Frazer Town zone — effective this Saturday.",
    "[SYSTEM] Dataset: 298,000 records | 764 zones | Jan–May 2024 | All systems operational.",
    "[RESOLVED] Upparpet — Sagar Theatre cluster reduced after targeted enforcement on Wednesday.",
    "[CRITICAL] Dispensary Road scooter cluster — 3rd consecutive week in Critical tier.",
]

# ══════════════════════════════════════════════════════════════════════════
# PAGE CONFIG & CSS
# ══════════════════════════════════════════════════════════════════════════
st.set_page_config(
    page_title="EaseTraffic — Bengaluru Traffic Intelligence",
    page_icon="🚔", layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
/* ── Base ── */
[data-testid="stAppViewContainer"] { background:#0b101e; color:#e0e0e0; }
[data-testid="stSidebar"]          { background:#151a28; border-right:1px solid #2a3143; }
[data-testid="stSidebar"] *        { font-size:1.05rem !important; }
h1  { font-size:2.2rem !important; font-weight:800 !important; color:#fff; }
h2  { font-size:1.7rem !important; font-weight:700 !important; color:#fff; }
h3  { font-size:1.35rem !important; font-weight:600 !important; color:#fff; }
p, li, label, .stMarkdown { font-size:1.0rem !important; }
[data-testid="stMetricValue"] { font-size:2.2rem !important; color:#3498db; }

/* ── Notice bar — marquee style from new code, speed tuned to 25s ── */
.notice-bar {
    background-color: #c0392b;
    color: white;
    padding: 9px 15px;
    font-weight: bold;
    border-radius: 6px;
    margin-bottom: 20px;
    display: flex;
    align-items: center;
    overflow: hidden;
    animation: pulse 2s infinite;
}
@keyframes pulse {
    0%   { box-shadow: 0 0 0 0 rgba(231,76,60,0.7); }
    70%  { box-shadow: 0 0 0 10px rgba(231,76,60,0); }
    100% { box-shadow: 0 0 0 0 rgba(231,76,60,0); }
}
.notice-label {
    margin-right:14px; white-space:nowrap;
    font-size:1.0rem; letter-spacing:0.5px;
}
.notice-bar-text { overflow:hidden; white-space:nowrap; width:100%; }
.marquee {
    display:inline-block; padding-left:100%;
    animation: marquee 40s linear infinite;
    font-size:0.97rem;
}
@keyframes marquee {
    0%   { transform: translate(0,0); }
    100% { transform: translate(-100%,0); }
}

/* ── Nav cards ── */
.nav-card {
    background:#1e2433; border:1px solid #2a3143; border-radius:12px;
    padding:26px 20px; text-align:center;
    transition:transform 0.2s, box-shadow 0.2s, border-color 0.2s;
    height:100%;
}
.nav-card:hover {
    transform:translateY(-5px);
    box-shadow:0 8px 20px rgba(0,0,0,0.4);
    border-color:#3498db;
}
.nav-icon  { font-size:3rem; margin-bottom:12px; }
.nav-title { font-size:1.3rem !important; font-weight:bold; color:#fff; margin-bottom:8px; }
.nav-desc  { font-size:0.88rem !important; color:#a0aabf; margin:0; }

/* ── KPI cards ── */
.kpi-card {
    background:#1e2433; border-radius:12px;
    padding:20px 18px; border-top:4px solid;
    text-align:center;
}
.kpi-card h2 { font-size:2rem !important; margin:4px 0; color:#fff; }
.kpi-card p  { font-size:0.88rem !important; color:#a0aabf; margin:0; }

/* ── Mission cards ── */
.mission-card { border-radius:12px; padding:16px 20px; margin:6px 0; border-left:5px solid; }
.firefighter  { border-color:#e74c3c; background:#1f1217; }
.preventative { border-color:#f1c40f; background:#1f1e10; }
.wildcard     { border-color:#3498db; background:#101820; }
.mission-card h4 { margin:0 0 8px; font-size:1.05rem !important; color:#fff; }
.mission-card p  { margin:3px 0; font-size:0.9rem !important; color:#ccc; }

/* ── Incident log ── */
.incident-card {
    background:#1e2433; border-radius:10px;
    padding:16px 20px; margin:8px 0;
    border-left:5px solid;
}
.inc-critical { border-color:#e74c3c; }
.inc-high     { border-color:#e67e22; }
.inc-resolved { border-color:#2ecc71; }
.inc-pending  { border-color:#f1c40f; }
.inc-dispatched { border-color:#3498db; }
.incident-card h4 { margin:0 0 6px; color:#fff; font-size:1rem !important; }
.incident-card p  { margin:2px 0; font-size:0.85rem !important; color:#ccc; }

/* ── Shift colours ── */
.shift-morning   { background:#0f1f10; border-left:4px solid #2ecc71; border-radius:8px; padding:12px 16px; }
.shift-evening   { background:#0f1020; border-left:4px solid #3498db; border-radius:8px; padding:12px 16px; }
.shift-night     { background:#1a0f20; border-left:4px solid #9b59b6; border-radius:8px; padding:12px 16px; }

/* ── Tables ── */
.stDataFrame { font-size:0.95rem !important; }
</style>
""", unsafe_allow_html=True)




# ══════════════════════════════════════════════════════════════════════════
# SESSION STATE NAVIGATION
# ══════════════════════════════════════════════════════════════════════════
if "current_page" not in st.session_state:
    st.session_state["current_page"] = "Home"

def navigate(page_name):
    st.session_state["current_page"] = page_name


# ══════════════════════════════════════════════════════════════════════════
# INCIDENT LOG STATE
# ══════════════════════════════════════════════════════════════════════════
def init_incidents():
    if "incidents" not in st.session_state:
        ist = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=5,minutes=30)))
        base_dt = ist - datetime.timedelta(hours=48)
        preset = [
            {"ticket":"BLR-38291","type":"Double Parking","vehicle":"CAR",
             "location":"Upparpet — Elite Junction","plate":"KA01AB1234",
             "status":"Dispatched","severity":"Critical",
             "reported_by":"BLR0042","notes":"Blocking left lane entirely",
             "timestamp":(base_dt+datetime.timedelta(hours=2)).strftime("%d %b %Y %H:%M"),
             "resolved_at":"","resolved_by":""},
            {"ticket":"BLR-38456","type":"No Parking","vehicle":"SCOOTER",
             "location":"Shivajinagar — Safina Plaza Junction","plate":"KA05CD5678",
             "status":"Pending","severity":"High",
             "reported_by":"BLR0015","notes":"Row of scooters on footpath",
             "timestamp":(base_dt+datetime.timedelta(hours=5)).strftime("%d %b %Y %H:%M"),
             "resolved_at":"","resolved_by":""},
            {"ticket":"BLR-38512","type":"Wrong Parking","vehicle":"TANKER",
             "location":"Upparpet — Sagar Theatre","plate":"KA03EF9012",
             "status":"Towed","severity":"Critical",
             "reported_by":"BLR0088","notes":"Tanker parked since previous night",
             "timestamp":(base_dt+datetime.timedelta(hours=9)).strftime("%d %b %Y %H:%M"),
             "resolved_at":(base_dt+datetime.timedelta(hours=11)).strftime("%d %b %Y %H:%M"),
             "resolved_by":"BLR0033"},
            {"ticket":"BLR-38634","type":"Parking near Bus Stop","vehicle":"CAR",
             "location":"Frazer Town — Coles Road","plate":"KA02GH3456",
             "status":"Resolved","severity":"Medium",
             "reported_by":"BLR0021","notes":"Bus stop blocked",
             "timestamp":(base_dt+datetime.timedelta(hours=14)).strftime("%d %b %Y %H:%M"),
             "resolved_at":(base_dt+datetime.timedelta(hours=16)).strftime("%d %b %Y %H:%M"),
             "resolved_by":"BLR0021"},
            {"ticket":"BLR-38701","type":"No Parking","vehicle":"MOTOR CYCLE",
             "location":"Koramangala — 2nd Block","plate":"KA01IJ7890",
             "status":"Pending","severity":"Low",
             "reported_by":"BLR0057","notes":"Parked on junction yellow line",
             "timestamp":(base_dt+datetime.timedelta(hours=20)).strftime("%d %b %Y %H:%M"),
             "resolved_at":"","resolved_by":""},
            {"ticket":"BLR-38802","type":"Double Parking","vehicle":"PASSENGER AUTO",
             "location":"KR Puram — MBT Road","plate":"KA04KL1122",
             "status":"Pending","severity":"High",
             "reported_by":"BLR0099","notes":"Autos doubled on both sides",
             "timestamp":(base_dt+datetime.timedelta(hours=26)).strftime("%d %b %Y %H:%M"),
             "resolved_at":"","resolved_by":""},
        ]
        st.session_state["incidents"] = preset

init_incidents()


# ══════════════════════════════════════════════════════════════════════════
# DATA LOADING
# ══════════════════════════════════════════════════════════════════════════
@st.cache_data(show_spinner="Loading zone profiles…")
def load_zone_profiles():
    zp = pd.read_parquet(PROCESSED / "zone_profiles_day3.parquet")
    for col in ["top_violations","top_vehicles","hourly_counts","daily_counts"]:
        if col in zp.columns:
            zp[col] = zp[col].apply(lambda v: json.loads(v) if isinstance(v,str) else v)
    if "zone_label" not in zp.columns:
        zp["zone_label"] = zp["police_station"] + " — " + zp.get("top_junction","").fillna("Area")
    return zp

@st.cache_data(show_spinner="Loading hex map data…")
def load_hex():
    p = PROCESSED / "h3_priority_scores_enriched.parquet"
    if not p.exists(): p = PROCESSED / "h3_priority_scores.parquet"
    return pd.read_parquet(p)

@st.cache_data(show_spinner="Loading patrol calendar…")
def load_calendar():
    return pd.read_parquet(PROCESSED / "patrol_calendar.parquet")

@st.cache_data(show_spinner="Loading violation map layer…")
def load_vmap():
    return pd.read_parquet(PROCESSED / "violations_with_h3.parquet")

@st.cache_resource(show_spinner="Connecting to Gemini…")
def load_gemini():
    key = os.getenv("GOOGLE_API_KEY","")
    if not key: return None, None
    genai.configure(api_key=key)
    return genai.GenerativeModel("gemini-2.5-flash"), genai.GenerativeModel("gemini-2.5-pro")

try:
    zone_df     = load_zone_profiles()
    hex_df      = load_hex()
    calendar_df = load_calendar()
    vmap_df     = load_vmap()
except Exception as e:
    st.error(f"Data loading error: {e}. Ensure Day 3 processed files exist.")
    st.stop()

gemini_flash, gemini_pro = load_gemini()

def get_ist():
    return datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=5,minutes=30)))


# ══════════════════════════════════════════════════════════════════════════
# OFFICER ROSTER GENERATOR
# ══════════════════════════════════════════════════════════════════════════
FIRST_NAMES = ["Arjun","Priya","Ravi","Meena","Kiran","Deepa","Suresh","Anita",
               "Mohan","Lakshmi","Raj","Sunita","Vijay","Rekha","Arun","Usha",
               "Ganesh","Kavya","Prakash","Shilpa","Mahesh","Divya","Sanjay","Pooja",
               "Ramesh","Geeta","Naresh","Nisha","Sunil","Radha","Ajay","Seema",
               "Dinesh","Asha","Harish","Jyothi","Vinod","Savitha","Rohit","Sindhu"]
LAST_NAMES  = ["Kumar","Sharma","Singh","Patil","Reddy","Gowda","Rao","Iyer","Nair","Desai"]

@st.cache_data(show_spinner="Generating officer roster…")
def generate_officer_roster(n_officers: int):
    rng = random.Random(99)
    officers = []
    for i in range(1, n_officers+1):
        name = f"{rng.choice(FIRST_NAMES)} {rng.choice(LAST_NAMES)}"
        officers.append({
            "Roll No": f"BLR{i:04d}",
            "Name"   : name,
            "Rank"   : rng.choice(["Constable","Head Constable","ASI","SI"]),
            "Division": rng.choice(["North","South","East","West","Central"]),
        })
    officers_df = pd.DataFrame(officers)

    ranked = zone_df.sort_values("ensemble_score", ascending=False).reset_index(drop=True)
    critical = ranked[ranked["priority_tier"]=="Critical"]["zone_label"].tolist() or ranked["zone_label"].tolist()[:5]
    high     = ranked[ranked["priority_tier"]=="High"]["zone_label"].tolist()     or ranked["zone_label"].tolist()[:5]
    medium   = ranked[ranked["priority_tier"]=="Medium"]["zone_label"].tolist()   or ranked["zone_label"].tolist()[:5]
    low      = ranked[ranked["priority_tier"].isin(["Low","Very Low"])]["zone_label"].tolist() or ranked["zone_label"].tolist()[:5]

    shift_cycle = ["Morning","Evening","Night"]
    shift_hours = {"Morning":"06:00–14:00","Evening":"14:00–22:00","Night":"22:00–06:00"}

    schedule_rows = []
    for week in range(1,4):
        shift_name = shift_cycle[(week-1)%3]
        for day_idx, day in enumerate(DAY_ORDER):
            avail = officers_df.copy().sample(frac=1, random_state=week*10+day_idx).reset_index(drop=True)
            off_idx = 0
            for z_idx, z_row in ranked.head(50).iterrows():
                required = 4 if z_row["priority_tier"]=="Critical" else 2 if z_row["priority_tier"]=="High" else 1
                for _ in range(required):
                    if off_idx < len(avail):
                        o = avail.iloc[off_idx]
                        # Alternate zones: even day=busy, odd day=quieter
                        if day_idx % 2 == 0:
                            pool = (critical+high) if shift_name=="Morning" else (high+medium)
                        else:
                            pool = medium + low
                        zone = pool[off_idx % len(pool)] if pool else z_row["zone_label"]
                        schedule_rows.append({
                            "week":week,"day":day,"shift":shift_name,
                            "shift_hours":shift_hours[shift_name],
                            "roll":o["Roll No"],"name":o["Name"],
                            "rank":o["Rank"],"division":o["Division"],
                            "zone":zone,"tier":z_row["priority_tier"],
                        })
                        off_idx += 1

    schedule_df = pd.DataFrame(schedule_rows)

    # Master timetable — zone level
    master_rows = []
    for week in range(1,4):
        for day in DAY_ORDER:
            for shift_name in ["Morning","Evening","Night"]:
                slot = schedule_df[(schedule_df["week"]==week)&
                                   (schedule_df["day"]==day)&
                                   (schedule_df["shift"]==shift_name)]
                zg = slot.groupby("zone").agg(
                    officer_count=("roll","count"),
                    officers=("roll",  lambda x:", ".join(x)),
                    names   =("name",  lambda x:", ".join(x)),
                    tier    =("tier",  "first"),
                ).reset_index()
                zg["week"]=week; zg["day"]=day; zg["shift"]=shift_name
                master_rows.append(zg)
    master_df = pd.concat(master_rows,ignore_index=True) if master_rows else pd.DataFrame()
    return officers_df, schedule_df, master_df


# ══════════════════════════════════════════════════════════════════════════
# SCHEDULER HELPERS
# ══════════════════════════════════════════════════════════════════════════
def compute_adj_score(row, hour, day_name, boost=3.0):
    hc    = row["hourly_counts"]
    dc    = row["daily_counts"]
    tot_h = max(sum(hc.values()),1)
    tot_d = max(sum(dc.values()),1)
    t_rel = hc.get(hour,hc.get(str(hour),0))/tot_h
    d_rel = dc.get(day_name,dc.get(str(day_name),0))/tot_d
    return row["ensemble_score"]*(1+boost*t_rel+0.5*d_rel)

@st.cache_data(show_spinner=False)
def get_scored_df(hour, day_name):
    rows = []
    for _,row in zone_df.iterrows():
        rows.append({**row.to_dict(),"adj_score":round(compute_adj_score(row,hour,day_name),1)})
    return pd.DataFrame(rows).sort_values("adj_score",ascending=False)

def get_stratified_missions(hour, day_name):
    scored = get_scored_df(hour,day_name)
    ff = scored.iloc[0].to_dict() if len(scored)>0 else None
    pv = scored[scored["priority_tier"].isin(["Medium","Low","Very Low"])&(scored["trend"]=="increasing")]
    pv = pv.iloc[0].to_dict() if len(pv)>0 else None
    wc = scored[scored["wildcard_eligible"]==1].sort_values("surge_pct",ascending=False) if "wildcard_eligible" in scored.columns else pd.DataFrame()
    wc = wc.iloc[0].to_dict() if len(wc)>0 else None
    return {"firefighter":ff,"preventative":pv,"wildcard":wc}

def get_full_queue(hour, day_name, top_n=50):
    scored = get_scored_df(hour,day_name).head(top_n)
    return scored[["zone_label","priority_tier","adj_score","ensemble_score",
                   "peak_hour","peak_day","trend","violation_count"]].rename(columns={
        "zone_label":"Zone","priority_tier":"Tier","adj_score":"Adj Score",
        "ensemble_score":"Base Score","peak_hour":"Peak Hr","peak_day":"Peak Day",
        "trend":"Trend","violation_count":"Total Violations"})


# ══════════════════════════════════════════════════════════════════════════
# GENAI
# ══════════════════════════════════════════════════════════════════════════
SYSTEM_PROMPT = """\
You are EaseTraffic, AI assistant for Bengaluru Traffic Police.
Always cite specific numbers. Cover ALL priority tiers. Be operational.
Keep answers under 250 words unless a detailed breakdown is requested.
"""
def build_context(hour=None,day_name=None):
    lines=["=== BENGALURU PARKING VIOLATION INTELLIGENCE ===\n"]
    if hour is not None and day_name is not None:
        m=get_stratified_missions(hour,day_name)
        lines.append(f"CURRENT MISSIONS ({hour:02d}:00 {day_name}):")
        if m["firefighter"]: lines.append(f"🔴 {m['firefighter']['zone_label']} Score:{m['firefighter']['adj_score']:.0f}")
        if m["preventative"]: lines.append(f"🟡 {m['preventative']['zone_label']} Trend:increasing")
        else: lines.append("🟡 No preventative zone (all mid/low stable)")
        if m["wildcard"]: lines.append(f"🔵 {m['wildcard']['zone_label']} Surge:{m['wildcard'].get('surge_pct',0):+.0f}%")
        lines.append("")
    for tier,lim in [("Critical",20),("High",15),("Medium",10),("Low",8),("Very Low",5)]:
        tzones=zone_df[zone_df["priority_tier"]==tier].nlargest(lim,"ensemble_score")
        if len(tzones)==0: continue
        lines.append(f"\n{tier.upper()} ({(zone_df['priority_tier']==tier).sum()} zones):")
        for _,r in tzones.iterrows():
            tv=r["top_violations"] if isinstance(r["top_violations"],list) else []
            lines.append(f"  • {r['zone_label']} | Score:{r['ensemble_score']:.0f} | "
                         f"Violations:{r['violation_count']:,} | Peak:{r['peak_hour']}:00 {r['peak_day']} | "
                         f"Trend:{r['trend']} | Top:{', '.join(tv[:2]) if tv else 'N/A'}")
    return "\n".join(lines)

def ask_gemini(q,use_pro=False,hour=None,day_name=None):
    if not gemini_flash: return "⚠️ Gemini not connected — add GOOGLE_API_KEY to .env"
    ctx=build_context(hour=hour,day_name=day_name)
    prompt=f"{SYSTEM_PROMPT}\n\n{ctx}\n\nInspector: {q}\n\nEaseTraffic:"
    try:
        model=gemini_pro if use_pro else gemini_flash
        return model.generate_content(prompt).text
    except Exception as e:
        return f"⚠️ Gemini error: {e}"


# ══════════════════════════════════════════════════════════════════════════
# NOTICE BAR
# ══════════════════════════════════════════════════════════════════════════
def render_notice_bar():
    ist = get_ist()
    all_n = NOTICES + [f"🕐 {ist.strftime('%H:%M IST | %a %d %b')}"]
    text  = "  &nbsp;&nbsp;|&nbsp;&nbsp;  ".join(all_n)
    st.markdown(f"""
    <div class="notice-bar">
      <div class="notice-label">⚠️ LIVE ALERTS:</div>
      <div class="notice-bar-text">
        <div class="marquee">{text}</div>
      </div>
    </div>""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════
# SIDEBAR — session-state navigation buttons
# ══════════════════════════════════════════════════════════════════════════
with st.sidebar:
    st.markdown("## 🚔 EaseTraffic")
    st.caption("BTP Traffic Command Center")
    st.divider()

    pages = [
        ("🏠","Home"),
        ("🗺️","Violation Map"),
        ("🚨","Live Queue"),
        ("👮","Officer Roster"),
        ("📝","Incident Logs"),
        ("📊","Statistics"),
        ("🔍","Zone Deep Dive"),
        ("🤖","AI Assistant"),
    ]
    for icon, pname in pages:
        label = f"**{icon} {pname}**" if st.session_state["current_page"]==pname else f"{icon} {pname}"
        btn_type = "primary" if st.session_state["current_page"]==pname else "secondary"
        st.button(label, key=f"nav_{pname}", on_click=navigate,
                  args=(pname,), use_container_width=True, type=btn_type)

    st.divider()
    ist = get_ist()
    st.markdown(f"**🕐 IST:** `{ist.strftime('%H:%M')}  {ist.strftime('%A')}`")
    st.markdown(f"**📅 Date:** `{ist.strftime('%d %b %Y')}`")
    st.divider()

    total_v  = int(zone_df["violation_count"].sum())
    n_zones  = len(zone_df)
    n_crit   = int((zone_df["priority_tier"]=="Critical").sum())
    n_surge  = int(zone_df["wildcard_eligible"].sum()) if "wildcard_eligible" in zone_df.columns else 0
    n_open   = sum(1 for i in st.session_state["incidents"] if i["status"] not in ["Resolved","Towed"])

    st.markdown(f"**Violations:** `{total_v:,}`")
    st.markdown(f"**Zones:** `{n_zones:,}`")
    st.markdown(f"**Critical:** `{n_crit}`")
    st.markdown(f"**Open Incidents:** `{n_open}`")
    st.divider()
    st.caption(f"Dataset: Jan–May 2024\n\n{PROJECT_VER}")
    st.caption(f"Built by: {', '.join(DEVELOPERS)}")

cp = st.session_state["current_page"]

# ══════════════════════════════════════════════════════════════════════════
# PAGE: HOME
# ══════════════════════════════════════════════════════════════════════════
if cp == "Home":
    render_notice_bar()

    st.markdown("""
    <div style="text-align:center;padding:36px 0 16px">
      <div style="font-size:4rem">🚔</div>
      <h1 style="font-size:2.8rem !important;
                 background:linear-gradient(90deg,#e74c3c,#e67e22,#f1c40f);
                 -webkit-background-clip:text;-webkit-text-fill-color:transparent;
                 margin:8px 0">
        EaseTraffic Command Center
      </h1>
      <p style="font-size:1.15rem !important;color:#a0aabf;max-width:600px;margin:0 auto">
        AI-Driven Parking Enforcement Intelligence for Bengaluru Traffic Police.<br>
        Detect hotspots · Prioritise enforcement · Predict surges · Deploy smarter.
      </p>
    </div>
    """, unsafe_allow_html=True)

    st.divider()

    # Live KPIs
    ist   = get_ist()
    m_now = get_stratified_missions(ist.hour,ist.strftime("%A"))
    ff    = m_now["firefighter"]
    n_inc = len(st.session_state["incidents"])
    n_open_i = sum(1 for i in st.session_state["incidents"] if i["status"] not in ["Resolved","Towed"])

    k1,k2,k3,k4,k5 = st.columns(5)
    kpis = [
        (k1,"#e74c3c","📋",f"{total_v:,}","Total Violations","Jan–May 2024"),
        (k2,"#e67e22","🗺️",f"{n_zones:,}","Zones Tracked","City-wide"),
        (k3,"#e74c3c","🔴",str(n_crit),"Critical Zones","Active now"),
        (k4,"#3498db","📈",str(n_surge),"Surging Zones","Wildcard eligible"),
        (k5,"#f1c40f","📝",str(n_open_i),"Open Incidents","Awaiting action"),
    ]
    for col,color,icon,val,title,sub in kpis:
        with col:
            st.markdown(f"""
            <div class="kpi-card" style="border-color:{color}">
              <div style="font-size:1.8rem">{icon}</div>
              <h2>{val}</h2>
              <p><b>{title}</b><br>{sub}</p>
            </div>""", unsafe_allow_html=True)

    # Current priority alert
    if ff:
        tv = ff.get("top_violations",[])
        if isinstance(tv,str):
            try: tv=json.loads(tv)
            except: tv=[]
        st.markdown(f"""
        <div style="background:#1f1217;border:1px solid #e74c3c;border-left:6px solid #e74c3c;
                    border-radius:12px;padding:18px 22px;margin:18px 0">
          <h3 style="color:#e74c3c;margin:0 0 6px">🔴 Current Priority Alert — {ist.strftime('%H:%M IST')}</h3>
          <p style="font-size:1.1rem !important;color:#fff;margin:4px 0">
            <b>{ff.get('zone_label','—')}</b> &nbsp;|&nbsp;
            Score: <b>{ff.get('adj_score',0):.1f}</b> &nbsp;|&nbsp;
            Tier: <b>{ff.get('priority_tier','—')}</b>
          </p>
          <p style="color:#ccc;margin:4px 0">
            Offenses: {', '.join(tv[:2]) if tv else 'N/A'} &nbsp;|&nbsp;
            Peak: {ff.get('peak_hour','—')}:00 IST &nbsp;|&nbsp;
            Trend: {ff.get('trend','—').upper()}
          </p>
        </div>""", unsafe_allow_html=True)

    st.markdown("### Navigate to")
    # Row 1 — 4 cards
    nav_items = [
        ("🗺️","Violation Map",   "City-wide heatmap, H3 priority zones, location filter by station."),
        ("🚨","Live Queue",       "Stratified missions: Firefighter · Preventative · Wildcard surge."),
        ("👮","Officer Roster",   "Weekly shift schedule with rotation. Master timetable by slot."),
        ("📝","Incident Logs",    "Register violations, update status, track resolution history."),
        ("📊","Statistics",       "ML insights, SHAP weights, temporal patterns, surge analytics."),
        ("🔍","Zone Deep Dive",   "Drill into any of 764 zones — stats, charts, peer comparison."),
        ("🤖","AI Assistant",     "Ask plain-English questions — Gemini 2.5 answers with real data."),
    ]
    row1 = st.columns(4)
    row2 = st.columns(3)
    for i,(icon,title,desc) in enumerate(nav_items):
        col = row1[i] if i<4 else row2[i-4]
        pname = title
        with col:
            st.markdown(f"""
            <div class="nav-card">
              <div class="nav-icon">{icon}</div>
              <div class="nav-title">{title}</div>
              <div class="nav-desc">{desc}</div>
            </div>""", unsafe_allow_html=True)
            st.button(f"Open {title}", key=f"home_nav_{title}",
                      on_click=navigate, args=(pname,),
                      use_container_width=True)

    st.markdown("---")
    # Tier snapshot
    st.markdown("### City Priority Snapshot")
    tc = zone_df["priority_tier"].value_counts().reindex(TIER_ORDER).fillna(0)
    fig = go.Figure(go.Bar(
        x=tc.index, y=tc.values,
        marker_color=[TIER_COLORS[t] for t in tc.index],
        text=tc.values.astype(int), textposition="outside",
        hovertemplate="%{x}: %{y} zones<extra></extra>"
    ))
    fig.update_layout(paper_bgcolor="#0b101e",plot_bgcolor="#0b101e",
        font_color="white",font_size=13,showlegend=False,height=260,
        margin=dict(t=10,b=20,l=20,r=20),yaxis_title="Zones")
    st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")
    st.markdown(f"""<div style="text-align:center;color:#555;font-size:0.88rem;padding:8px 0">
      {PROJECT_VER} &nbsp;·&nbsp; {', '.join(DEVELOPERS)}
      &nbsp;·&nbsp; Gridlock Hackathon 2.0 | Flipkart × Bengaluru Traffic Police
    </div>""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════
# PAGE: VIOLATION MAP  (full original version preserved)
# ══════════════════════════════════════════════════════════════════════════
elif cp == "Violation Map":
    render_notice_bar()
    st.title("🗺️ Bengaluru Violation Map")
    st.markdown("**Priority zones across the city — filter by tier, score, or location**")

    c1,c2,c3,c4 = st.columns(4)
    with c1:
        min_score = st.slider("Min Priority Score",0,80,0,5)
        map_style = st.selectbox("Map Style",
            ["OpenStreetMap","CartoDB dark_matter","CartoDB positron"])
    with c2:
        show_heat  = st.checkbox("Show Violation Heatmap",True)
        show_hexes = st.checkbox("Show Priority Hex Zones",True)
    with c3:
        tier_filter = st.multiselect("Filter Tiers",TIER_ORDER,default=TIER_ORDER)
    with c4:
        all_stations = sorted(zone_df["police_station"].dropna().unique().tolist())
        loc_filter   = st.selectbox("Filter by Police Station",["All"]+all_stations)

    filtered_hex = hex_df.copy()
    if loc_filter!="All":
        filtered_hex = filtered_hex[filtered_hex["police_station"]==loc_filter]

    m = folium.Map(location=[12.97,77.59],zoom_start=12,tiles=map_style)

    if show_heat:
        sample = vmap_df.sample(min(15000,len(vmap_df)),random_state=42)
        if loc_filter!="All" and "police_station" in vmap_df.columns:
            s2 = vmap_df[vmap_df["police_station"]==loc_filter]
            if len(s2)>0: sample=s2
        HeatMap(
            list(zip(sample["latitude"],sample["longitude"],sample["severity_score"].fillna(1))),
            radius=8,blur=10,max_zoom=14,
            gradient={"0.2":"blue","0.5":"lime","0.8":"orange","1.0":"red"}
        ).add_to(m)

    drawn=0
    if show_hexes:
        mh = filtered_hex[(filtered_hex["ensemble_score"]>=min_score)&
                          (filtered_hex["final_priority_tier"].isin(tier_filter))]
        for _,row in mh.iterrows():
            tier  = str(row.get("final_priority_tier","Very Low"))
            color = TIER_COLORS.get(tier,"#95a5a6")
            label = row.get("zone_label",row.get("police_station","—"))
            score = row["ensemble_score"]
            try:
                boundary = h3.cell_to_boundary(row["h3_id"])
                folium.Polygon(
                    locations=[[la,lo] for la,lo in boundary],
                    color=color,fill=True,fill_color=color,fill_opacity=0.55,weight=1,
                    popup=folium.Popup(
                        f"<b>{label}</b><br>Tier:{tier}<br>Score:{score:.1f}<br>"
                        f"Violations:{int(row['violation_count']):,}<br>"
                        f"Junction:{row['near_junction_ratio']*100:.0f}%",max_width=260),
                    tooltip=f"{tier} — {label[:32]} ({score:.0f})"
                ).add_to(m)
                drawn+=1
            except Exception:
                pass

    top10 = filtered_hex.nlargest(10,"ensemble_score")
    for rank,(_,row) in enumerate(top10.iterrows(),1):
        label=row.get("zone_label",row.get("police_station","—"))
        folium.Marker(
            location=[row["lat"],row["lon"]],
            tooltip=f"#{rank} {label[:30]} ({row['ensemble_score']:.0f})",
            popup=f"#{rank} {label}<br>Score:{row['ensemble_score']:.1f}",
            icon=folium.Icon(color="red",icon="exclamation-sign")
        ).add_to(m)

    folium.LayerControl().add_to(m)
    st_folium(m,width=1200,height=600)
    st.caption(f"Showing {drawn} zones | Score≥{min_score} | Station:{loc_filter} | Click hex for details")
    legend=" &nbsp; ".join(f'<span style="color:{TIER_COLORS[t]}">■</span> {t}' for t in TIER_ORDER)
    st.markdown("**Legend:** "+legend,unsafe_allow_html=True)

    if loc_filter!="All":
        st.markdown(f"---\n### 📍 {loc_filter} — Station Summary")
        sz = zone_df[zone_df["police_station"]==loc_filter]
        if len(sz)>0:
            s1,s2,s3,s4=st.columns(4)
            s1.metric("Zones",len(sz))
            s2.metric("Total Violations",f"{int(sz['violation_count'].sum()):,}")
            s3.metric("Highest Score",f"{sz['ensemble_score'].max():.1f}")
            s4.metric("Top Tier",sz.loc[sz["ensemble_score"].idxmax(),"priority_tier"])
            st.dataframe(
                sz[["zone_label","priority_tier","ensemble_score","violation_count",
                    "peak_hour","peak_day","trend"]]
                .sort_values("ensemble_score",ascending=False)
                .rename(columns={"zone_label":"Zone","priority_tier":"Tier",
                                  "ensemble_score":"Score","violation_count":"Violations",
                                  "peak_hour":"Peak Hr","peak_day":"Peak Day"}),
                use_container_width=True)


# ══════════════════════════════════════════════════════════════════════════
# PAGE: LIVE QUEUE
# ══════════════════════════════════════════════════════════════════════════
elif cp == "Live Queue":
    render_notice_bar()
    st.title("🚨 Live Enforcement Queue")
    st.markdown("**Stratified patrol missions + ranked city-wide enforcement priorities**")

    ist=get_ist()
    c1,c2,c3=st.columns(3)
    with c1: qh=st.slider("Hour (IST)",0,23,ist.hour)
    with c2: qd=st.selectbox("Day",DAY_ORDER,index=ist.weekday())
    with c3: top_n=st.slider("Queue size",10,50,20)

    missions=get_stratified_missions(qh,qd)
    st.markdown(f"### 🎯 Patrol Missions — {qh:02d}:00 on {qd}")

    def render_mission(col,icon,css,title,m,extra=""):
        with col:
            if m is None:
                st.markdown(f"""
                <div class="mission-card {css}">
                  <h4>{icon} {title}</h4>
                  <p>⚪ No qualifying zone — all Medium/Low zones are stable or decreasing.</p>
                </div>
                """, unsafe_allow_html=True)
            else:
                tv=m.get("top_violations",[]) or []
                tveh=m.get("top_vehicles",[]) or []
                if isinstance(tv,str):
                    try: tv=json.loads(tv)
                    except: tv=[]
                if isinstance(tveh,str):
                    try: tveh=json.loads(tveh)
                    except: tveh=[]
                st.markdown(f"""
                <div class="mission-card {css}">
                  <h4>{icon} {title}</h4>
                  <p><b>{m.get('zone_label','—')}</b></p>
                  <p>Tier: <b>{m.get('priority_tier','—')}</b> | Score: <b>{m.get('adj_score',0):.1f}</b></p>
                  <p>Peak: {m.get('peak_hour','—')}:00 on {m.get('peak_day','—')}</p>
                  <p>Offenses: {', '.join(tv[:2]) if tv else '—'}</p>
                  {extra}
                </div>
                """, unsafe_allow_html=True)

    mc1,mc2,mc3=st.columns(3)
    render_mission(mc1,"🔴","firefighter","#1 Firefighter",missions["firefighter"])
    pv=missions["preventative"]
    pv_x=f"<p>📈 INCREASING | Surge:{pv.get('surge_pct',0):+.0f}%</p>" if pv else ""
    render_mission(mc2,"🟡","preventative","Preventative",pv,pv_x)
    wc=missions["wildcard"]
    wc_x=f"<p>🔵 Surge:{wc.get('surge_pct',0):+.0f}% | {int(wc.get('recent_count',0))} recent</p>" if wc else ""
    render_mission(mc3,"🔵","wildcard","Wildcard Surge",wc,wc_x)

    # Mission map
    st.markdown("#### Mission Locations")
    m2=folium.Map(location=[12.97,77.59],zoom_start=12,tiles="OpenStreetMap")
    mp_cfg=[("🔴 Firefighter",missions["firefighter"],"red","exclamation-sign"),
            ("🟡 Preventative",missions["preventative"],"orange","eye-open"),
            ("🔵 Wildcard",missions["wildcard"],"blue","fire")]
    any_pin=False
    for lbl,md,color,icon_n in mp_cfg:
        if md:
            folium.Marker(
                location=[md["lat"],md["lon"]],
                tooltip=f"{lbl}: {md['zone_label'][:35]}",
                popup=f"<b>{lbl}</b><br>{md['zone_label']}<br>Score:{md['adj_score']:.1f}",
                icon=folium.Icon(color=color,icon=icon_n)
            ).add_to(m2)
            any_pin=True
    if any_pin: st_folium(m2,width=900,height=300)
    else: st.info("No mission zones to display.")

    # Full queue
    st.divider()
    st.markdown(f"### 📋 Full Queue — Top {top_n} Zones at {qh:02d}:00 on {qd}")
    queue=get_full_queue(qh,qd,top_n=top_n)
    def ct(v): c={"Critical":"#e74c3c","High":"#e67e22","Medium":"#c8a800","Low":"#27ae60","Very Low":"#2980b9"}; return f"color:{c.get(v,'white')};font-weight:bold"
    def tr(v): return f"color:{'#e74c3c' if v=='increasing' else '#2ecc71' if v=='decreasing' else '#aaa'}"
    st.dataframe(queue.style.applymap(ct,subset=["Tier"]).applymap(tr,subset=["Trend"]),
                 use_container_width=True,height=460)

    st.divider()
    st.markdown("#### 📏 Carriageway Impact Estimator")
    sel=st.selectbox("Select zone",zone_df.sort_values("ensemble_score",ascending=False)["zone_label"].tolist())
    sr=zone_df[zone_df["zone_label"]==sel]
    if len(sr)>0:
        sr=sr.iloc[0]; vc=int(sr["violation_count"]); fm=vc*4.5; fl=fm/3.5
        e1,e2,e3,e4=st.columns(4)
        e1.metric("Tier",sr["priority_tier"]); e2.metric("Violations",f"{vc:,}")
        e3.metric("Carriageway Freed",f"{fm:,.0f} m"); e4.metric("Lane-metres",f"{fl:,.0f}")


# ══════════════════════════════════════════════════════════════════════════
# PAGE: OFFICER ROSTER
# ══════════════════════════════════════════════════════════════════════════
elif cp == "Officer Roster":
    render_notice_bar()
    st.title("👮 Officer Patrol Roster")
    st.markdown("**Weekly shift schedule with rotation — data-driven zone allocation**")

    n_off=st.slider("Number of officers in roster",10,40,20,5)
    officers_df,schedule_df,master_df=generate_officer_roster(n_off)

    tab_roster,tab_weekly,tab_master=st.tabs(
        ["📋 Officer List","📅 Weekly Schedule","🗺️ Master Timetable"])

    with tab_roster:
        st.markdown(f"### {len(officers_df)} Officers — Current Roster")
        wk=st.radio("View shift week",[1,2,3],
            format_func=lambda w:f"Week {w} — {['Morning','Evening','Night'][w-1]} Shift",horizontal=True)
        sn={1:"Morning",2:"Evening",3:"Night"}[wk]
        sh_hours={"Morning":"06:00–14:00","Evening":"14:00–22:00","Night":"22:00–06:00"}[sn]
        css_shift={"Morning":"shift-morning","Evening":"shift-evening","Night":"shift-night"}[sn]
        st.markdown(f"""<div class="{css_shift}">
          <b>Week {wk} — {sn} Shift ({sh_hours})</b><br>
          <span style="font-size:0.88rem;color:#ccc">Rotation: Week 1=Morning | Week 2=Evening | Week 3=Night.
          Even days → Critical/High zones; Odd days → Medium/Low zones.</span>
        </div>""",unsafe_allow_html=True)
        st.markdown(" ")
        wk_sched=schedule_df[schedule_df["week"]==wk]
        summ=wk_sched.groupby(["roll","name","rank","division"]).agg(
            assignments=("zone","count"),
            unique_zones=("zone","nunique"),
            sample_zones=("zone",lambda x:" | ".join(x.unique()[:3]))
        ).reset_index().rename(columns={"roll":"Roll No","name":"Name","rank":"Rank",
            "division":"Division","assignments":"Assignments",
            "unique_zones":"Unique Zones","sample_zones":"Sample Zones"})
        st.dataframe(summ,use_container_width=True,height=420)

    with tab_weekly:
        st.markdown("### Individual Officer Weekly Schedule")
        c1,c2=st.columns(2)
        with c1: wkv=st.selectbox("Week",[1,2,3],
            format_func=lambda w:f"Week {w} ({['Morning','Evening','Night'][w-1]})")
        with c2:
            off_opts=officers_df["Roll No"].tolist()
            off_lbl={r:f"{r} — {n}" for r,n in zip(officers_df["Roll No"],officers_df["Name"])}
            sel_roll=st.selectbox("Officer Roll No",off_opts,format_func=lambda r:off_lbl.get(r,r))
        off_data=schedule_df[(schedule_df["week"]==wkv)&(schedule_df["roll"]==sel_roll)].sort_values(
            "day",key=lambda x:x.map({d:i for i,d in enumerate(DAY_ORDER)}))
        if len(off_data)==0:
            st.info("No assignments this week (rest day).")
        else:
            sn2=off_data["shift"].iloc[0]; sh2=off_data["shift_hours"].iloc[0]
            css2={"Morning":"shift-morning","Evening":"shift-evening","Night":"shift-night"}[sn2]
            st.markdown(f"""<div class="{css2}">
              <b>Officer: {off_lbl.get(sel_roll,sel_roll)}</b><br>
              Week {wkv} | {sn2} Shift | {sh2}
            </div>""",unsafe_allow_html=True)
            st.markdown(" ")
            ztm=zone_df.set_index("zone_label")["priority_tier"].to_dict()
            disp_off=off_data[["day","zone"]].rename(columns={"day":"Day","zone":"Assigned Zone"}).copy()
            disp_off["Tier"]=disp_off["Assigned Zone"].map(ztm).fillna("—")
            def ct2(v): c={"Critical":"#e74c3c","High":"#e67e22","Medium":"#c8a800","Low":"#27ae60","Very Low":"#2980b9"}; return f"color:{c.get(v,'white')};font-weight:bold"
            st.dataframe(disp_off.style.applymap(ct2,subset=["Tier"]),use_container_width=True)
            tc2=disp_off["Tier"].value_counts()
            cols5=st.columns(5)
            for col_t,tier in zip(cols5,TIER_ORDER):
                with col_t:
                    cnt=tc2.get(tier,0)
                    st.markdown(f"""<div style="text-align:center;background:#1e2433;border-radius:8px;
                    padding:10px;border-top:3px solid {TIER_COLORS[tier]}">
                    <b style="color:{TIER_COLORS[tier]};font-size:1.3rem">{cnt}</b>
                    <p style="margin:0;font-size:0.78rem;color:#a0aabf">{tier}</p></div>""",
                    unsafe_allow_html=True)

    with tab_master:
        st.markdown("### Master Timetable — Officer Deployment by Location")
        mt1,mt2,mt3=st.columns(3)
        with mt1: mtw=st.selectbox("Week",[1,2,3],format_func=lambda w:f"Week {w} ({['Morning','Evening','Night'][w-1]})",key="mtw")
        with mt2: mtd=st.selectbox("Day",DAY_ORDER,key="mtd")
        with mt3: mts=st.selectbox("Shift",["Morning","Evening","Night"],key="mts")
        search_loc=st.text_input("🔍 Search location",placeholder="e.g. Koramangala, Upparpet…")
        if len(master_df)>0:
            slot=master_df[(master_df["week"]==mtw)&(master_df["day"]==mtd)&(master_df["shift"]==mts)].copy()
            if search_loc:
                slot=slot[slot["zone"].str.contains(search_loc,case=False,na=False)]
            zsm=zone_df.set_index("zone_label")["ensemble_score"].to_dict()
            slot["score"]=slot["zone"].map(zsm).fillna(0)
            slot=slot.sort_values("score",ascending=False).reset_index(drop=True)
            sm1,sm2,sm3=st.columns(3)
            sm1.metric("Locations",len(slot))
            sm2.metric("Officers deployed",int(slot["officer_count"].sum()) if len(slot)>0 else 0)
            PAGE_SZ=20
            total_pages=max(1,math.ceil(len(slot)/PAGE_SZ))
            if "mt_page" not in st.session_state: st.session_state["mt_page"]=0
            if search_loc: st.session_state["mt_page"]=0
            pg=st.session_state["mt_page"]
            sm3.metric("Page",f"{pg+1}/{total_pages}")
            page_data=slot.iloc[pg*PAGE_SZ:(pg+1)*PAGE_SZ]
            def ct3(v): c={"Critical":"#e74c3c","High":"#e67e22","Medium":"#c8a800","Low":"#27ae60","Very Low":"#2980b9"}; return f"color:{c.get(v,'white')};font-weight:bold"
            dmaster=page_data[["zone","tier","officer_count","officers","names"]].rename(columns={
                "zone":"Location","tier":"Tier","officer_count":"Officers",
                "officers":"Roll Numbers","names":"Names"})
            st.dataframe(dmaster.style.applymap(ct3,subset=["Tier"]),use_container_width=True,height=480)
            pc1,pc2,pc3=st.columns([1,2,1])
            with pc1:
                if st.button("⬅️ Previous",disabled=pg==0):
                    st.session_state["mt_page"]=max(0,pg-1); st.rerun()
            with pc2:
                st.markdown(f"<div style='text-align:center;padding-top:8px'>Locations {pg*PAGE_SZ+1}–{min((pg+1)*PAGE_SZ,len(slot))} of {len(slot)}</div>",unsafe_allow_html=True)
            with pc3:
                if st.button("Next ➡️",disabled=pg>=total_pages-1):
                    st.session_state["mt_page"]=min(total_pages-1,pg+1); st.rerun()
            st.download_button("⬇️ Download CSV",slot.to_csv(index=False),
                f"timetable_w{mtw}_{mtd}_{mts}.csv","text/csv")
        else:
            st.warning("Master timetable not yet generated.")


# ══════════════════════════════════════════════════════════════════════════
# PAGE: INCIDENT LOGS  (complete new page)
# ══════════════════════════════════════════════════════════════════════════
elif cp == "Incident Logs":
    render_notice_bar()
    st.title("📝 Incident Tracking & Management")
    st.markdown("**Register violations · Update status · Track resolution · View history**")

    ist = get_ist()
    incidents = st.session_state["incidents"]

    # Summary metrics
    total_inc = len(incidents)
    open_inc  = sum(1 for i in incidents if i["status"] not in ["Resolved","Towed"])
    res_inc   = sum(1 for i in incidents if i["status"] in ["Resolved","Towed"])
    crit_inc  = sum(1 for i in incidents if i["severity"]=="Critical")
    m1,m2,m3,m4 = st.columns(4)
    m1.metric("Total Incidents",    total_inc)
    m2.metric("Open / Active",      open_inc, delta=f"-{res_inc} resolved")
    m3.metric("Resolved / Towed",   res_inc)
    m4.metric("Critical Severity",  crit_inc)

    st.divider()
    tab_log, tab_update, tab_history, tab_stats = st.tabs([
        "➕ Log New Violation",
        "✏️  Update Status",
        "📋 Incident History",
        "📊 Incident Analytics",
    ])

    # ── Tab 1: Log new ────────────────────────────────────────────────────
    with tab_log:
        st.markdown("### Report a New Parking Violation")
        with st.form("new_violation_form", clear_on_submit=True):
            fc1,fc2 = st.columns(2)
            with fc1:
                v_type    = st.selectbox("Violation Type",
                    ["No Parking","Wrong Parking","Double Parking",
                     "Parking near Bus Stop/School","Parking on Footpath",
                     "Parking opposite parked vehicle","Blocking Driveway"])
                v_vehicle = st.selectbox("Vehicle Type",
                    ["CAR","SCOOTER","MOTOR CYCLE","PASSENGER AUTO",
                     "BUS","TANKER","TRUCK","MAXI-CAB"])
                v_severity= st.selectbox("Severity",["Critical","High","Medium","Low"])
            with fc2:
                all_stations2 = sorted(zone_df["police_station"].dropna().unique().tolist())
                v_station = st.selectbox("Police Station", all_stations2)
                station_zones = zone_df[zone_df["police_station"]==v_station]["zone_label"].tolist()
                v_zone    = st.selectbox("Zone / Junction",
                    station_zones if station_zones else ["Unknown"])
                v_plate   = st.text_input("Vehicle Plate Number",
                    placeholder="e.g. KA01AB1234")
            v_officer = st.text_input("Reporting Officer Roll No",
                placeholder="e.g. BLR0042")
            v_notes   = st.text_area("Additional Notes",
                placeholder="Describe the situation, exact location, obstructions caused…",
                height=100)
            submitted = st.form_submit_button("🚨 Submit Violation Report", type="primary")

        if submitted:
            ticket = f"BLR-{random.randint(10000,99999)}"
            new_inc = {
                "ticket"     : ticket,
                "type"       : v_type,
                "vehicle"    : v_vehicle,
                "location"   : v_zone,
                "plate"      : v_plate.upper() if v_plate else "Unknown",
                "status"     : "Pending",
                "severity"   : v_severity,
                "reported_by": v_officer.upper() if v_officer else "Unknown",
                "notes"      : v_notes,
                "timestamp"  : ist.strftime("%d %b %Y %H:%M"),
                "resolved_at": "",
                "resolved_by": "",
            }
            st.session_state["incidents"].insert(0, new_inc)
            st.success(f"✅ Violation logged successfully! **Ticket ID: {ticket}**")
            st.info(f"Location: {v_zone} | Vehicle: {v_vehicle} | Severity: {v_severity}")

    # ── Tab 2: Update status ──────────────────────────────────────────────
    with tab_update:
        st.markdown("### Update Incident Status")

        open_tickets = [i for i in st.session_state["incidents"]
                        if i["status"] not in ["Resolved","Towed"]]
        if not open_tickets:
            st.success("✅ No open incidents — all cleared!")
        else:
            # Show open incidents as cards
            for inc in open_tickets:
                sev_css = {"Critical":"inc-critical","High":"inc-high",
                           "Medium":"inc-pending","Low":"inc-pending"}.get(inc["severity"],"inc-pending")
                st.markdown(f"""
                <div class="incident-card {sev_css}">
                  <h4>🎫 {inc['ticket']} — {inc['type']}</h4>
                  <p><b>Location:</b> {inc['location']} &nbsp;|&nbsp;
                     <b>Vehicle:</b> {inc['vehicle']} ({inc['plate']}) &nbsp;|&nbsp;
                     <b>Severity:</b> {inc['severity']}</p>
                  <p><b>Status:</b> {inc['status']} &nbsp;|&nbsp;
                     <b>Reported:</b> {inc['timestamp']} by {inc['reported_by']}</p>
                  <p><b>Notes:</b> {inc['notes'] or '—'}</p>
                </div>""", unsafe_allow_html=True)

            st.divider()
            st.markdown("#### Update a Specific Ticket")
            ticket_ids = [i["ticket"] for i in open_tickets]
            sel_ticket = st.selectbox("Select Ticket ID", ticket_ids)
            sel_inc    = next((i for i in st.session_state["incidents"]
                               if i["ticket"]==sel_ticket), None)

            if sel_inc:
                uc1,uc2,uc3 = st.columns(3)
                with uc1:
                    new_status = st.selectbox("New Status",
                        ["Pending","Dispatched","Towed","Resolved"])
                with uc2:
                    res_officer = st.text_input("Resolving Officer Roll No",
                        placeholder="e.g. BLR0033")
                with uc3:
                    res_notes = st.text_input("Resolution Notes",
                        placeholder="e.g. Vehicle moved, fine issued")

                if st.button("✅ Update Status", type="primary", key="update_btn"):
                    for i, inc in enumerate(st.session_state["incidents"]):
                        if inc["ticket"] == sel_ticket:
                            st.session_state["incidents"][i]["status"] = new_status
                            if new_status in ["Resolved","Towed"]:
                                st.session_state["incidents"][i]["resolved_at"] = ist.strftime("%d %b %Y %H:%M")
                                st.session_state["incidents"][i]["resolved_by"] = res_officer.upper() if res_officer else "Unknown"
                                if res_notes:
                                    st.session_state["incidents"][i]["notes"] += f" | RESOLVED: {res_notes}"
                            break
                    st.success(f"✅ {sel_ticket} updated to **{new_status}**")
                    st.rerun()

    # ── Tab 3: History ────────────────────────────────────────────────────
    with tab_history:
        st.markdown("### Full Incident History")

        # Filters
        hc1,hc2,hc3 = st.columns(3)
        with hc1:
            flt_status = st.multiselect("Filter by Status",
                ["Pending","Dispatched","Towed","Resolved"],
                default=["Pending","Dispatched","Towed","Resolved"])
        with hc2:
            flt_sev = st.multiselect("Filter by Severity",
                ["Critical","High","Medium","Low"],
                default=["Critical","High","Medium","Low"])
        with hc3:
            search_ticket = st.text_input("🔍 Search Ticket / Location", "")

        filtered_inc = [i for i in st.session_state["incidents"]
                        if i["status"] in flt_status and i["severity"] in flt_sev]
        if search_ticket:
            filtered_inc = [i for i in filtered_inc
                            if search_ticket.lower() in i["ticket"].lower()
                            or search_ticket.lower() in i["location"].lower()
                            or search_ticket.lower() in i["plate"].lower()]

        if not filtered_inc:
            st.info("No incidents match your filters.")
        else:
            for inc in filtered_inc:
                status_css = {
                    "Resolved":"inc-resolved","Towed":"inc-resolved",
                    "Dispatched":"inc-dispatched","Pending":"inc-pending"
                }.get(inc["status"],"inc-pending")
                status_icon = {"Resolved":"✅","Towed":"🚛","Dispatched":"🚔","Pending":"⏳"}.get(inc["status"],"⏳")
                st.markdown(f"""
                <div class="incident-card {status_css}">
                  <h4>{status_icon} {inc['ticket']} — {inc['type']} | {inc['severity']}</h4>
                  <p><b>Location:</b> {inc['location']} &nbsp;|&nbsp;
                     <b>Vehicle:</b> {inc['vehicle']} ({inc['plate']}) &nbsp;|&nbsp;
                     <b>Status:</b> <b>{inc['status']}</b></p>
                  <p><b>Reported:</b> {inc['timestamp']} by {inc['reported_by']}</p>
                  {"<p><b>Resolved:</b> " + inc['resolved_at'] + " by " + inc['resolved_by'] + "</p>" if inc.get('resolved_at') else ""}
                  <p><b>Notes:</b> {inc['notes'] or '—'}</p>
                </div>""", unsafe_allow_html=True)

    # ── Tab 4: Analytics ──────────────────────────────────────────────────
    with tab_stats:
        st.markdown("### Incident Analytics")
        if len(incidents) < 2:
            st.info("Add more incidents to see analytics.")
        else:
            inc_df = pd.DataFrame(incidents)
            ac1,ac2 = st.columns(2)
            with ac1:
                sc = inc_df["status"].value_counts()
                fig_s = px.pie(values=sc.values,names=sc.index,
                    color=sc.index,
                    color_discrete_map={"Resolved":"#2ecc71","Towed":"#27ae60",
                                        "Dispatched":"#3498db","Pending":"#f1c40f"},
                    title="Incidents by Status",hole=0.4)
                fig_s.update_layout(paper_bgcolor="#0b101e",font_color="white",
                    height=320,margin=dict(t=40,b=10,l=10,r=10))
                st.plotly_chart(fig_s, use_container_width=True)
            with ac2:
                sevc = inc_df["severity"].value_counts().reindex(
                    ["Critical","High","Medium","Low"]).fillna(0)
                fig_sv = px.bar(x=sevc.index,y=sevc.values,
                    color=sevc.index,
                    color_discrete_map={"Critical":"#e74c3c","High":"#e67e22",
                                        "Medium":"#f1c40f","Low":"#2ecc71"},
                    title="Incidents by Severity",text_auto=True)
                fig_sv.update_layout(paper_bgcolor="#0b101e",plot_bgcolor="#1e2433",
                    font_color="white",showlegend=False,height=320,
                    margin=dict(t=40,b=10,l=20,r=10))
                st.plotly_chart(fig_sv, use_container_width=True)

            tc = inc_df["type"].value_counts()
            fig_t = px.bar(x=tc.values,y=tc.index,orientation="h",
                color=tc.values,color_continuous_scale="Reds",
                title="Incidents by Violation Type",text_auto=True)
            fig_t.update_layout(paper_bgcolor="#0b101e",plot_bgcolor="#1e2433",
                font_color="white",showlegend=False,height=320,
                yaxis={"categoryorder":"total ascending"},
                margin=dict(t=40,b=10,l=200,r=80))
            st.plotly_chart(fig_t, use_container_width=True)


# ══════════════════════════════════════════════════════════════════════════
# PAGE: STATISTICS
# ══════════════════════════════════════════════════════════════════════════
elif cp == "Statistics":
    render_notice_bar()
    st.title("📊 Statistics & ML Insights")
    st.markdown("**Dataset analysis, model explainability, temporal patterns, tier distributions**")

    st1,st2,st3,st4 = st.tabs(
        ["🏙️ City Overview","⏰ Temporal","🤖 Model Insights","📈 Surge & Trends"])

    with st1:
        r1,r2 = st.columns(2)
        with r1:
            tc = zone_df["priority_tier"].value_counts().reindex(TIER_ORDER).fillna(0)
            fig1=px.bar(x=tc.index,y=tc.values,color=tc.index,color_discrete_map=TIER_COLORS,
                labels={"x":"Tier","y":"Zones"},title="Zones by Priority Tier",text_auto=True)
            fig1.update_layout(paper_bgcolor="#0b101e",plot_bgcolor="#1e2433",
                font_color="white",showlegend=False,height=340,margin=dict(t=40,b=20,l=20,r=20))
            st.plotly_chart(fig1,use_container_width=True)
        with r2:
            vbt=zone_df.groupby("priority_tier")["violation_count"].sum().reindex(TIER_ORDER)
            fig2=px.pie(values=vbt.values,names=vbt.index,color=vbt.index,
                color_discrete_map=TIER_COLORS,title="Violations by Tier (%)",hole=0.4)
            fig2.update_layout(paper_bgcolor="#0b101e",font_color="white",height=340,
                margin=dict(t=40,b=20,l=20,r=20))
            st.plotly_chart(fig2,use_container_width=True)
        top20=zone_df.nlargest(20,"violation_count")
        fig3=px.bar(top20,x="violation_count",y="zone_label",orientation="h",
            color="priority_tier",color_discrete_map=TIER_COLORS,
            labels={"violation_count":"Violations","zone_label":"Zone"},
            title="Top 20 Zones by Violations")
        fig3.update_layout(paper_bgcolor="#0b101e",plot_bgcolor="#1e2433",
            font_color="white",height=520,yaxis={"categoryorder":"total ascending"},
            margin=dict(t=40,b=20,l=200,r=20))
        st.plotly_chart(fig3,use_container_width=True)

        # Try loading static images from notebook outputs
        st.markdown("#### Notebook-Generated Analysis Charts")
        notebook_images = [
            ("temporal_01_heatmap_allzones.png", "Hour × Day Heatmap — All Zones (from Day 3 notebook)"),
            ("temporal_02_tier_surge_dist.png",  "Tier Distribution & Surge Histogram (from Day 3 notebook)"),
            ("temporal_03_tier_hourly_profiles.png", "Per-Tier Hourly Profiles (from Day 3 notebook)"),
        ]
        any_notebook_img = False
        for img_name, caption in notebook_images:
            # Try processed folder first, then root project folder
            candidates = [
                PROCESSED / img_name,
                ROOT / img_name,
                ROOT / "notebooks" / img_name,
            ]
            found = next((p for p in candidates if p.exists()), None)
            if found:
                try:
                    st.image(str(found), caption=caption, use_container_width=True)
                    st.markdown(" ")
                    any_notebook_img = True
                except Exception as img_err:
                    st.warning(f"Could not render {img_name}: {img_err}")
        if not any_notebook_img:
            st.info(
                "📂 Notebook charts not found in `data/processed/`.\n\n"
                "Run **day3_revised.ipynb** to generate them — "
                "they are saved automatically as PNG files during the EDA section."
            )

    with st2:
        all_hours={h:0 for h in range(24)}
        for _,row in zone_df.iterrows():
            for h,cnt in row["hourly_counts"].items():
                all_hours[int(float(h))] = all_hours.get(int(float(h)), 0) + cnt
        hours=list(range(24)); counts=[all_hours.get(h,0) for h in hours]
        hcolors=["#e74c3c" if h in list(range(7,11))+list(range(17,22)) else "#3498db" for h in hours]
        fig_h=go.Figure(go.Bar(x=hours,y=counts,marker_color=hcolors,
            hovertemplate="Hour %{x}:00 — %{y:,} violations<extra></extra>"))
        fig_h.update_layout(paper_bgcolor="#0b101e",plot_bgcolor="#1e2433",
            font_color="white",height=360,
            title="City-Wide Hourly Distribution (Red = Peak Hours)",
            xaxis_title="Hour (IST)",yaxis_title="Violations",
            xaxis=dict(tickvals=list(range(0,24,2))),
            margin=dict(t=40,b=30,l=40,r=20))
        st.plotly_chart(fig_h,use_container_width=True)
        all_days={d:0 for d in DAY_ORDER}
        for _,row in zone_df.iterrows():
            for d,cnt in row["daily_counts"].items():
                if d in all_days: all_days[d]+=cnt
        dcolors=["#e74c3c" if d in ["Saturday","Sunday"] else "#2ecc71" for d in DAY_ORDER]
        fig_d=go.Figure(go.Bar(x=DAY_ORDER,y=[all_days[d] for d in DAY_ORDER],
            marker_color=dcolors,hovertemplate="%{x} — %{y:,}<extra></extra>"))
        fig_d.update_layout(paper_bgcolor="#0b101e",plot_bgcolor="#1e2433",
            font_color="white",height=320,
            title="Day-of-Week Distribution (Red = Weekend)",
            yaxis_title="Violations",margin=dict(t=40,b=20,l=40,r=20))
        st.plotly_chart(fig_d,use_container_width=True)
        # Prophet forecast image
        prophet_candidates = [
            PROCESSED / "temporal_04_prophet_forecasts.png",
            ROOT / "temporal_04_prophet_forecasts.png",
            ROOT / "notebooks" / "temporal_04_prophet_forecasts.png",
        ]
        prophet_img = next((p for p in prophet_candidates if p.exists()), None)
        if prophet_img:
            try:
                st.image(str(prophet_img),
                         caption="30-Day Prophet Forecasts — Critical Zones (from Day 3 notebook)",
                         use_container_width=True)
            except Exception as img_err:
                st.warning(f"Could not render Prophet forecast image: {img_err}")
        else:
            st.info(
                "📂 Prophet forecast chart not found.\n\n"
                "Run **day3_revised.ipynb** Section 6 to generate `temporal_04_prophet_forecasts.png`."
            )

    with st3:
        st.markdown("""
        <div style="background:#1e2433;border-radius:12px;padding:20px 22px;
                    margin-bottom:16px;border-left:5px solid #9b59b6">
          <h4 style="color:#9b59b6;margin:0 0 8px">How EaseTraffic Scores Zones</h4>
          <p>Each of the 764 hex zones is scored by a <b>weighted ensemble</b>:</p>
          <p>• <b>60%</b> — Transparent formula (violation frequency × severity × road rank × junction × peak hour)</p>
          <p>• <b>40%</b> — XGBoost classifier probability (trained on top-25% pseudo-labels)</p>
          <p>SHAP reveals which features drive each zone's priority classification.</p>
        </div>""",unsafe_allow_html=True)
        feats=["violation_count","severity_sum","near_junction_ratio","peak_hour_ratio",
               "recurrence_rate","impact_sum","vehicle_weight_mean","road_rank_mean","multi_violation_ratio"]
        weights=[0.25,0.20,0.20,0.15,0.10,0.04,0.03,0.02,0.01]
        fig_feat=go.Figure(go.Bar(x=weights,y=feats,orientation="h",
            marker_color=["#e74c3c","#e67e22","#f1c40f","#2ecc71","#3498db",
                          "#9b59b6","#1abc9c","#e91e63","#607d8b"],
            text=[f"{w:.0%}" for w in weights],textposition="outside",
            hovertemplate="%{y}: %{x:.1%}<extra></extra>"))
        fig_feat.update_layout(paper_bgcolor="#0b101e",plot_bgcolor="#1e2433",
            font_color="white",height=360,
            title="Priority Score Formula — Feature Weights",
            xaxis_title="Weight",xaxis_tickformat=".0%",
            margin=dict(t=40,b=20,l=220,r=80))
        st.plotly_chart(fig_feat,use_container_width=True)
        sev_df=pd.DataFrame({
            "Code":[109,108,107,111,104,112,113],
            "Violation":["Parking opposite parked vehicle","Double Parking",
                          "Parking in Main Road","Near Bus Stop/School/Hospital",
                          "Near Road Crossing","Wrong Parking","No Parking"],
            "Weight":[5,5,4,4,3,2,1],
            "Impact":["🔴 Full lane blocked","🔴 Full lane blocked",
                       "🟠 High","🟠 High","🟡 Moderate","🟡 Moderate","🟢 Low"],
        })
        st.dataframe(sev_df,use_container_width=True)
        st.markdown("""
        <div style="background:#101820;border-radius:12px;padding:14px 20px;margin-top:10px;
                    border-left:5px solid #3498db">
          <b style="color:#3498db">⚠️ Transparency Note</b><br>
          This dataset contains <b>violation records</b>, not traffic flow measurements.
          Congestion scores are <b>weighted proxies</b>. CCTV or Waze integration would replace proxies with ground truth.
        </div>""",unsafe_allow_html=True)
        # SHAP image if exists
        # SHAP importance image
        shap_candidates = [
            PROCESSED / "shap_importance.png",
            ROOT / "shap_importance.png",
            ROOT / "notebooks" / "shap_importance.png",
        ]
        shap_img = next((p for p in shap_candidates if p.exists()), None)
        if shap_img:
            try:
                st.image(str(shap_img),
                         caption="SHAP Feature Importance — XGBoost Priority Classifier (from Day 2 notebook)",
                         use_container_width=True)
            except Exception as img_err:
                st.warning(f"Could not render SHAP image: {img_err}")
        else:
            st.info(
                "📂 SHAP chart not found.\n\n"
                "Run **day2_hotspot_model.ipynb** Section 6 to generate `shap_importance.png` "
                "— it is saved to `data/processed/` automatically."
            )

    with st4:
        if "surge_pct" in zone_df.columns:
            inc2=( zone_df["trend"]=="increasing").sum()
            dec2=(zone_df["trend"]=="decreasing").sum()
            sta2=(zone_df["trend"]=="stable").sum()
            c1s,c2s,c3s=st.columns(3)
            c1s.metric("Increasing",f"{inc2} zones","⬆️")
            c2s.metric("Stable",    f"{sta2} zones","➡️")
            c3s.metric("Decreasing",f"{dec2} zones","⬇️")
            fig_sc=px.scatter(zone_df,x="ensemble_score",y="surge_pct",
                color="priority_tier",color_discrete_map=TIER_COLORS,
                size="violation_count",size_max=20,
                hover_data=["zone_label","violation_count"],
                labels={"ensemble_score":"Priority Score","surge_pct":"Surge %","priority_tier":"Tier"},
                title="Surge % vs Priority Score")
            fig_sc.add_hline(y=10,line_dash="dash",line_color="#e74c3c",annotation_text="Wildcard +10%")
            fig_sc.add_hline(y=-10,line_dash="dash",line_color="#2ecc71",annotation_text="Decreasing -10%")
            fig_sc.update_layout(paper_bgcolor="#0b101e",plot_bgcolor="#1e2433",
                font_color="white",height=450,
                legend=dict(bgcolor="#1e2433"),margin=dict(t=40,b=20,l=40,r=20))
            st.plotly_chart(fig_sc,use_container_width=True)
            sc1,sc2=st.columns(2)
            with sc1:
                st.markdown("**🔺 Top 10 Increasing Zones**")
                up=zone_df[zone_df["trend"]=="increasing"].nlargest(10,"surge_pct")[
                    ["zone_label","priority_tier","surge_pct","recent_count","ensemble_score"]
                ].rename(columns={"zone_label":"Zone","priority_tier":"Tier",
                    "surge_pct":"Surge %","recent_count":"Recent 14d","ensemble_score":"Score"})
                up["Surge %"]=up["Surge %"].apply(lambda x:f"+{x:.0f}%")
                st.dataframe(up,use_container_width=True)
            with sc2:
                st.markdown("**🔻 Top 10 Decreasing Zones**")
                dn=zone_df[zone_df["trend"]=="decreasing"].nsmallest(10,"surge_pct")[
                    ["zone_label","priority_tier","surge_pct","recent_count","ensemble_score"]
                ].rename(columns={"zone_label":"Zone","priority_tier":"Tier",
                    "surge_pct":"Surge %","recent_count":"Recent 14d","ensemble_score":"Score"})
                dn["Surge %"]=dn["Surge %"].apply(lambda x:f"{x:.0f}%")
                st.dataframe(dn,use_container_width=True)
        else:
            st.info("Surge data not available — re-run day3_revised.ipynb.")


# ══════════════════════════════════════════════════════════════════════════
# PAGE: ZONE DEEP DIVE
# ══════════════════════════════════════════════════════════════════════════
elif cp == "Zone Deep Dive":
    render_notice_bar()
    st.title("🔍 Zone Deep Dive")
    st.caption(f"Explore any of {len(zone_df):,} zones across all priority tiers")

    tc_col,zc_col=st.columns([1,3])
    with tc_col: sel_tier=st.selectbox("Filter by Tier",["All"]+TIER_ORDER)
    with zc_col:
        filt=zone_df if sel_tier=="All" else zone_df[zone_df["priority_tier"]==sel_tier]
        filt=filt.sort_values("ensemble_score",ascending=False)
        sel_zone=st.selectbox(f"Select Zone ({len(filt)} available)",filt["zone_label"].tolist())

    row=zone_df[zone_df["zone_label"]==sel_zone].iloc[0]
    k1,k2,k3,k4,k5,k6=st.columns(6)
    k1.metric("Score",   f"{row['ensemble_score']:.1f}")
    k2.metric("Tier",    row["priority_tier"])
    k3.metric("Violations",f"{row['violation_count']:,}")
    k4.metric("Peak Hour",f"{row['peak_hour']}:00")
    k5.metric("Peak Day",row["peak_day"])
    k6.metric("Trend",   row["trend"].upper())
    st.markdown(
        f"**Morning:** `{row['best_morning_start']}:00–{row['best_morning_start']+2}:00` | "
        f"**Evening:** `{row['best_evening_start']}:00–{row['best_evening_start']+2}:00` | "
        f"**Weekend:** `{row['weekend_ratio']*100:.0f}%` | "
        f"**Junction:** `{row['near_junction_ratio']*100:.0f}%` | "
        f"**Severity:** `{row['severity_mean']:.2f}/5` | "
        f"**Surge:** `{row.get('surge_pct',0):+.0f}%`"
    )
    if row.get("wildcard_eligible",0):
        st.warning("🔵 Wildcard eligible — surging violations. Add to enhanced monitoring.")
    st.divider()

    dc=row["daily_counts"]
    d_counts=[dc.get(d,0) for d in DAY_ORDER]
    d_colors=["#e74c3c" if d in ["Saturday","Sunday"] else "#2ecc71" for d in DAY_ORDER]
    fig_d=go.Figure(go.Bar(x=[d[:3] for d in DAY_ORDER],y=d_counts,marker_color=d_colors,
        hovertemplate="%{x} — %{y} violations<extra></extra>"))
    fig_d.update_layout(title="Day-of-Week Violation Profile (Red=Weekend)",
        paper_bgcolor="#0b101e",plot_bgcolor="#1e2433",font_color="white",
        height=290,margin=dict(t=40,b=20,l=40,r=20))
    st.plotly_chart(fig_d,use_container_width=True)

    cl,cr=st.columns(2)
    with cl:
        st.markdown("**Top Violation Types**")
        tv=row["top_violations"] if isinstance(row["top_violations"],list) else []
        for v in tv: st.markdown(f"- {v}")
        if not tv: st.caption("No data")
    with cr:
        st.markdown("**Top Vehicle Types**")
        tveh=row["top_vehicles"] if isinstance(row["top_vehicles"],list) else []
        for v in tveh: st.markdown(f"- {v}")
        if not tveh: st.caption("No data")

    st.divider()
    s1,s2,s3=st.columns(3)
    s1.metric("Recent 14d",int(row.get("recent_count",0)))
    s2.metric("Prior 14d", int(row.get("prior_count",0)))
    s3.metric("Surge",     f"{row.get('surge_pct',0):+.0f}%",
              delta_color="inverse" if row.get("surge_pct",0)>0 else "normal")

    st.divider()
    m3=folium.Map(location=[row["lat"],row["lon"]],zoom_start=15,tiles="OpenStreetMap")
    try:
        boundary=h3.cell_to_boundary(row["h3_id"])
        folium.Polygon(locations=[[la,lo] for la,lo in boundary],
            color=TIER_COLORS.get(row["priority_tier"],"#aaa"),
            fill=True,fill_opacity=0.4,weight=2).add_to(m3)
    except Exception: pass
    folium.Marker(location=[row["lat"],row["lon"]],tooltip=sel_zone,
        icon=folium.Icon(color="red",icon="exclamation-sign")).add_to(m3)
    st_folium(m3,width=900,height=300)

    with st.expander(f"Compare with other {row['priority_tier']} zones",expanded=False):
        peers=zone_df[(zone_df["priority_tier"]==row["priority_tier"])&
                      (zone_df["zone_label"]!=sel_zone)].nlargest(10,"ensemble_score")[
            ["zone_label","ensemble_score","violation_count","peak_hour","peak_day","trend","surge_pct"]
        ].rename(columns={"zone_label":"Zone","ensemble_score":"Score",
            "violation_count":"Violations","peak_hour":"Peak Hr",
            "peak_day":"Peak Day","surge_pct":"Surge %"})
        peers["Surge %"]=peers["Surge %"].apply(lambda x:f"{x:+.0f}%")
        st.dataframe(peers,use_container_width=True)


# ══════════════════════════════════════════════════════════════════════════
# PAGE: AI ASSISTANT
# ══════════════════════════════════════════════════════════════════════════
elif cp == "AI Assistant":
    render_notice_bar()
    st.title("🤖 EaseTraffic AI Assistant")

    if not gemini_flash:
        st.error("Gemini not connected. Add GOOGLE_API_KEY to .env and restart.")
        st.stop()

    ist=get_ist()
    ctl1,ctl2,ctl3=st.columns([2,2,1])
    with ctl1: use_pro=st.toggle("Gemini 2.5 Pro (thorough)",value=False)
    with ctl2: inject_t=st.toggle("Inject current patrol missions",value=True)
    with ctl3:
        if st.button("🗑️ Clear"): st.session_state["messages"]=[]; st.rerun()

    st.caption(
        f"Model: `{'gemini-2.5-pro' if use_pro else 'gemini-2.5-flash'}` | "
        f"Context: {len(zone_df):,} zones · all tiers | {ist.strftime('%H:%M on %A')}"
    )

    col_chat,col_q=st.columns([3,1])
    with col_q:
        st.markdown("### Quick Questions")
        for q in ["Where to patrol right now?","Top 3 critical zones?",
                   "Low/medium zones trending up?","Worst vehicle types?",
                   "Weekend patrol strategy?","Which zones are surging?",
                   "Compare critical vs medium.","Full enforcement briefing."]:
            if st.button(q,key=f"q_{q}",use_container_width=True):
                st.session_state["prefill"]=q

    with col_chat:
        if "messages" not in st.session_state: st.session_state["messages"]=[]
        for msg in st.session_state["messages"]:
            with st.chat_message(msg["role"],avatar="👮" if msg["role"]=="user" else "🚦"):
                st.markdown(msg["content"])
        prefill=st.session_state.pop("prefill","")
        user_input=st.chat_input("Ask about any zone, tier, trend, or patrol strategy…") or prefill
        if user_input:
            with st.chat_message("user",avatar="👮"): st.markdown(user_input)
            st.session_state["messages"].append({"role":"user","content":user_input})
            h_ctx=ist.hour if inject_t else None
            d_ctx=ist.strftime("%A") if inject_t else None
            with st.chat_message("assistant",avatar="🚦"):
                with st.spinner("Analysing city data…"):
                    resp=ask_gemini(user_input,use_pro=use_pro,hour=h_ctx,day_name=d_ctx)
                st.markdown(resp)
            st.session_state["messages"].append({"role":"assistant","content":resp})
