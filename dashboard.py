"""
dashboard.py  —  AI Marketing ROI Dashboard (Light Theme)
==========================================================
Run with:  streamlit run dashboard.py
"""

import streamlit as st
import plotly.graph_objects as go
import pandas as pd
from pymongo import MongoClient

from channel_profile import (
    build_channel_profiles,
    rank_channels,
    search_channels,
)
from algo import a_star
from hill_climb import hill_climb

# ─────────────────────────────────────────────────────────────────────────────
# PAGE CONFIG
# ─────────────────────────────────────────────────────────────────────────────

st.set_page_config(
    page_title            = "Marketing ROI Optimizer",
    page_icon             = "📊",
    layout                = "wide",
    initial_sidebar_state = "expanded",
)

# ─────────────────────────────────────────────────────────────────────────────
# LIGHT THEME CSS
# ─────────────────────────────────────────────────────────────────────────────

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700&family=Fraunces:wght@600;700&display=swap');

html, body, [class*="css"] {
    font-family: 'Plus Jakarta Sans', sans-serif;
    color: #1a1f2e;
}
.stApp { background: #f4f6fb; }
#MainMenu, footer, header { visibility: hidden; }

[data-testid="stSidebar"] {
    background: #ffffff !important;
    border-right: 1px solid #e2e8f0 !important;
}
[data-testid="stSidebar"] * { color: #1a1f2e !important; }
[data-testid="stSidebarContent"] { padding: 24px 16px; }

[data-testid="stMetric"] {
    background: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 12px;
    padding: 20px 24px;
    box-shadow: 0 1px 4px rgba(0,0,0,0.05);
}
[data-testid="stMetricLabel"] {
    color: #64748b !important;
    font-size: 0.75rem !important;
    font-weight: 600 !important;
    text-transform: uppercase;
    letter-spacing: 0.07em;
}
[data-testid="stMetricValue"] {
    color: #0f172a !important;
    font-family: 'Fraunces', serif !important;
    font-size: 1.75rem !important;
    font-weight: 700 !important;
}
[data-testid="stMetricDelta"] { font-size: 0.8rem !important; }

.page-header {
    background: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 16px;
    padding: 28px 36px;
    margin-bottom: 24px;
    box-shadow: 0 1px 6px rgba(0,0,0,0.05);
}
.header-title {
    font-family: 'Fraunces', serif;
    font-size: 1.8rem;
    font-weight: 700;
    color: #0f172a;
    margin: 0 0 6px 0;
}
.header-sub { color: #64748b; font-size: 0.9rem; margin: 0 0 14px 0; }
.tag {
    display: inline-block;
    background: #f1f5f9;
    border: 1px solid #e2e8f0;
    color: #475569;
    font-size: 0.72rem;
    font-weight: 600;
    padding: 4px 12px;
    border-radius: 20px;
    margin-right: 6px;
    letter-spacing: 0.04em;
}
.tag-blue  { background:#eff6ff; border-color:#bfdbfe; color:#2563eb; }
.tag-green { background:#f0fdf4; border-color:#bbf7d0; color:#16a34a; }

.section-label {
    font-size: 0.7rem;
    font-weight: 700;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    color: #94a3b8;
    margin-bottom: 4px;
}
.section-title {
    font-family: 'Fraunces', serif;
    font-size: 1.15rem;
    font-weight: 700;
    color: #0f172a;
    margin-bottom: 16px;
}

.nav-label {
    font-size: 0.68rem;
    font-weight: 700;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    color: #94a3b8;
    margin: 20px 0 8px 0;
}

.tip {
    background: #eff6ff;
    border-left: 3px solid #3b82f6;
    border-radius: 0 8px 8px 0;
    padding: 10px 14px;
    color: #1d4ed8;
    font-size: 0.83rem;
    margin-top: 16px;
}

hr { border-color: #e2e8f0 !important; margin: 28px 0 !important; }

[data-testid="stDataFrame"] {
    border-radius: 10px;
    overflow: hidden;
    border: 1px solid #e2e8f0;
}
.stTextInput input {
    border: 1px solid #e2e8f0 !important;
    border-radius: 8px !important;
    background: #f8fafc !important;
    color: #0f172a !important;
}
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# CHART DEFAULTS
# ─────────────────────────────────────────────────────────────────────────────

COLORS = ["#3b82f6", "#8b5cf6", "#10b981", "#f59e0b", "#ef4444", "#06b6d4"]

LAYOUT = dict(
    paper_bgcolor = "rgba(0,0,0,0)",
    plot_bgcolor  = "rgba(0,0,0,0)",
    font          = dict(family="Plus Jakarta Sans", color="#334155"),
    margin        = dict(t=16, b=16, l=16, r=16),
)


# ─────────────────────────────────────────────────────────────────────────────
# DATABASE + CACHED PIPELINE
# ─────────────────────────────────────────────────────────────────────────────

@st.cache_resource
def get_db():
    client = MongoClient('mongodb://localhost:27017/')
    return client['marketing_ai']


@st.cache_data(ttl=300)
def run_pipeline(budget: float):
    db = get_db()
    best_channels, best_roi, budget_used = a_star(max_budget=budget, db=db, verbose=False)
    all_profiles = build_channel_profiles(db)
    best_state, expected_roi = hill_climb(
        selected_channels = best_channels,
        all_profiles      = all_profiles,
        total_budget      = budget,
        max_alloc         = 0.25,
        verbose           = False,
    )
    return best_channels, all_profiles, best_state, expected_roi, budget_used


@st.cache_data(ttl=300)
def run_sensitivity(base_budget: float):
    db   = get_db()
    rows = []
    for multiplier in [0.6, 0.8, 1.0, 1.2, 1.4]:
        b          = base_budget * multiplier
        channels, _, _ = a_star(max_budget=b, db=db, verbose=False)
        profiles   = build_channel_profiles(db)
        best_state, _ = hill_climb(
            selected_channels = channels,
            all_profiles      = profiles,
            total_budget      = b,
            max_alloc         = 0.25,
            verbose           = False,
        )
        
        # Apply diminishing returns function using roi_at_spend
        expected_roi = 0.0
        for ch, frac in best_state.allocations.items():
            if ch in profiles:
                spend = frac * b
                roi_value = profiles[ch].roi_at_spend(spend)
                expected_roi += roi_value
        
        rows.append({
            "Budget"       : b,
            "Budget Label" : f"${b:,.0f}",
            "Expected ROI" : expected_roi,
            "Channels"     : len(channels),
            "Change"       : f"{((b - base_budget) / base_budget) * 100:+.0f}%",
        })
    return pd.DataFrame(rows)


# ─────────────────────────────────────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown("""
        <div style='font-family:Fraunces,serif;font-size:1.2rem;font-weight:700;
                    color:#0f172a;margin-bottom:2px;'>📊 ROI Optimizer</div>
        <div style='color:#64748b;font-size:0.82rem;margin-bottom:20px;'>
            AI-powered marketing budget tool
        </div>
    """, unsafe_allow_html=True)

    st.markdown("<div class='nav-label'>💰 Budget</div>", unsafe_allow_html=True)
    budget = st.slider(
        "Total Campaign Budget",
        min_value = 15_000,
        max_value = 500_000,
        value     = 75_000,
        step      = 5_000,
        format    = "$%d",
    )
    st.caption(f"Selected: **${budget:,.0f}**")

    st.divider()

    st.markdown("<div class='nav-label'>🔍 Search & Filter</div>", unsafe_allow_html=True)
    search_query = st.text_input("Search channel name", placeholder="e.g. Facebook")
    risk_filter  = st.selectbox("Filter by risk level", ["all", "safe", "moderate", "risky"])
    min_roi      = st.slider("Minimum avg ROI", 0.0, 6.0, 0.0, 0.1)

    st.divider()

    st.markdown("""
        <div class='tip'>
            💡 <b>Tip:</b> Drag the budget slider — all charts update live automatically.
        </div>
    """, unsafe_allow_html=True)

    st.markdown("""
        <div style='margin-top:24px;color:#cbd5e1;font-size:0.75rem;text-align:center;'>
            A* Search · Hill Climbing<br>200,000 campaigns · 6 channels
        </div>
    """, unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# LOAD DATA
# ─────────────────────────────────────────────────────────────────────────────

with st.spinner("Running AI pipeline..."):
    best_channels, all_profiles, best_state, expected_roi, budget_used = run_pipeline(budget)

ranked   = rank_channels(all_profiles)
filtered = search_channels(all_profiles, search_query, risk_filter, min_roi)

rank_df = pd.DataFrame([
    {
        "Rank"       : rank,
        "Channel"    : name,
        "Score"      : round(score, 5),
        "Avg ROI"    : round(all_profiles[name].avg_roi, 4),
        "ROI/Dollar" : round(all_profiles[name].roi_per_dollar, 6),
        "Conversion" : f"{all_profiles[name].avg_conversion:.1%}",
        "Avg Cost"   : f"${all_profiles[name].avg_cost:,.0f}",
        "Risk Score" : round(all_profiles[name].risk_score, 3),
        "Risk"       : all_profiles[name].risk_label,
        "Best ROI"   : round(all_profiles[name].best_case_roi, 4),
        "Worst ROI"  : round(all_profiles[name].worst_case_roi, 4),
    }
    for rank, name, score in ranked
])

alloc_df = pd.DataFrame([
    {
        "Channel"      : ch,
        "Allocation %" : round(frac * 100, 1),
        "Amount ($)"   : round(frac * budget, 0),
        "Risk"         : all_profiles[ch].risk_label if ch in all_profiles else "",
    }
    for ch, frac in sorted(best_state.allocations.items(), key=lambda x: x[1], reverse=True)
])


# ─────────────────────────────────────────────────────────────────────────────
# PAGE HEADER
# ─────────────────────────────────────────────────────────────────────────────

st.markdown(f"""
<div class="page-header">
    <div class="header-title">📊 Marketing ROI Optimizer</div>
    <div class="header-sub">
        AI-powered budget allocation across {len(all_profiles)} channels
        · Trained on 200,000 real campaigns
    </div>
    <span class="tag tag-blue">A* Search</span>
    <span class="tag tag-blue">Hill Climbing</span>
    <span class="tag tag-green">Budget: ${budget:,.0f}</span>
</div>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 1 — KPI METRICS
# ─────────────────────────────────────────────────────────────────────────────

st.markdown("<div class='section-label'>Overview</div>", unsafe_allow_html=True)
st.markdown("<div class='section-title'>Key Performance Indicators</div>", unsafe_allow_html=True)

c1, c2, c3, c4, c5 = st.columns(5)
with c1: st.metric("💰 Total Budget",      f"${budget:,.0f}")
with c2: st.metric("📈 Expected ROI",      f"{expected_roi:,.2f}")
with c3: st.metric("✅ Budget Used",       f"${budget_used:,.0f}", delta=f"{(budget_used/budget)*100:.0f}% utilised")
with c4: st.metric("🎯 Channels Selected", len(best_channels))
#with c5: st.metric("💹 Revenue",    f"${(expected_roi*budget_used)+budget_used:.2f}")

st.markdown("<br>", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 2 — ALLOCATION PIE + RANKING BAR
# ─────────────────────────────────────────────────────────────────────────────

st.markdown("<div class='section-label'>Budget Allocation</div>", unsafe_allow_html=True)
st.markdown("<div class='section-title'>How is your money split across channels?</div>", unsafe_allow_html=True)

col_pie, col_bar = st.columns([1, 1.3])

with col_pie:
    active = alloc_df[alloc_df["Allocation %"] > 0]
    fig_pie = go.Figure(go.Pie(
        labels        = active["Channel"],
        values        = active["Amount ($)"],
        hole          = 0.58,
        marker_colors = COLORS[:len(active)],
        textinfo      = "label+percent",
        textfont      = dict(size=12, color="#334155"),
        hovertemplate = "<b>%{label}</b><br>$%{value:,.0f}<br>%{percent}<extra></extra>",
    ))
    fig_pie.update_layout(
        **LAYOUT,
        height     = 290,
        showlegend = False,
        annotations= [dict(
            text      = f"<b>${budget:,.0f}</b>",
            x=0.5, y=0.5,
            font      = dict(size=15, color="#0f172a"),
            showarrow = False,
        )]
    )
    st.plotly_chart(fig_pie, use_container_width=True)
    st.dataframe(
        active.rename(columns={"Allocation %": "Alloc %", "Amount ($)": "Amount"}),
        hide_index=True, use_container_width=True,
    )

with col_bar:
    fig_bar = go.Figure()
    for i, (_, row) in enumerate(rank_df.iterrows()):
        fig_bar.add_trace(go.Bar(
            x             = [row["Score"]],
            y             = [f"#{row['Rank']}  {row['Channel']}"],
            orientation   = "h",
            marker_color  = COLORS[i % len(COLORS)],
            marker_opacity= 0.82,
            name          = row["Channel"],
            text          = [f"{row['Score']:.5f}"],
            textposition  = "outside",
            textfont      = dict(color="#64748b", size=11),
            hovertemplate = (
                f"<b>{row['Channel']}</b><br>"
                f"Score: {row['Score']:.5f}<br>"
                f"ROI/Dollar: {row['ROI/Dollar']}<br>"
                f"Conversion: {row['Conversion']}<extra></extra>"
            ),
        ))
    fig_bar.update_layout(
        **LAYOUT,
        height     = 330,
        showlegend = False,
        xaxis      = dict(showgrid=True, gridcolor="#f1f5f9", color="#94a3b8",
                          title="Composite Score", zeroline=False),
        yaxis      = dict(showgrid=False, color="#334155", autorange="reversed"),
        bargap     = 0.38,
    )
    st.plotly_chart(fig_bar, use_container_width=True)
    st.markdown("""
        <div class='tip'>
            🏆 <b>Composite Score</b> = 50% ROI efficiency + 30% conversion rate + 20% conservative ROI.
            Higher score = better overall channel.
        </div>
    """, unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 3 — RISK ANALYSIS + ROI RANGE
# ─────────────────────────────────────────────────────────────────────────────

st.divider()
st.markdown("<div class='section-label'>Risk Analysis</div>", unsafe_allow_html=True)
st.markdown("<div class='section-title'>How risky is each channel?</div>", unsafe_allow_html=True)

col_risk, col_range = st.columns(2)

with col_risk:
    risk_color_map = {
        "✅ Safe"      : "#10b981",
        "⚠️  Moderate" : "#f59e0b",
        "🔴 Risky"     : "#ef4444",
    }
    bar_colors = [risk_color_map.get(r, "#3b82f6") for r in rank_df["Risk"]]

    fig_risk = go.Figure(go.Bar(
        x             = rank_df["Channel"],
        y             = rank_df["Risk Score"],
        marker_color  = bar_colors,
        marker_opacity= 0.8,
        text          = rank_df["Risk Score"].apply(lambda v: f"{v:.3f}"),
        textposition  = "outside",
        textfont      = dict(color="#64748b", size=11),
        hovertemplate = "<b>%{x}</b><br>Risk Score: %{y:.3f}<extra></extra>",
    ))
    fig_risk.add_hline(y=0.33, line_dash="dot", line_color="#10b981", line_width=1.5,
                       annotation_text="Safe limit (0.33)",
                       annotation_font_color="#10b981", annotation_font_size=10)
    fig_risk.add_hline(y=0.66, line_dash="dot", line_color="#ef4444", line_width=1.5,
                       annotation_text="Risky limit (0.66)",
                       annotation_font_color="#ef4444", annotation_font_size=10)
    fig_risk.update_layout(
        **LAYOUT,
        height = 290,
        xaxis  = dict(showgrid=False, color="#64748b"),
        yaxis  = dict(showgrid=True, gridcolor="#f1f5f9", color="#94a3b8",
                      title="Risk Score  (0 = safe,  1 = risky)", range=[0, 1]),
    )
    st.plotly_chart(fig_risk, use_container_width=True)

    safe_n = len([r for r in rank_df["Risk"] if "Safe"     in r])
    mod_n  = len([r for r in rank_df["Risk"] if "Moderate" in r])
    risk_n = len([r for r in rank_df["Risk"] if "Risky"    in r])
    ca, cb, cc = st.columns(3)
    with ca: st.metric("✅ Safe",      safe_n)
    with cb: st.metric("⚠️ Moderate",  mod_n)
    with cc: st.metric("🔴 Risky",     risk_n)

with col_range:
    fig_range = go.Figure()
    fig_range.add_trace(go.Scatter(
        x=rank_df["Channel"], y=rank_df["Worst ROI"],
        mode="lines+markers", name="Worst Case",
        line=dict(color="#ef4444", dash="dash", width=2),
        marker=dict(size=7, color="#ef4444"),
        hovertemplate="<b>%{x}</b><br>Worst Case: %{y:.4f}<extra></extra>",
    ))
    fig_range.add_trace(go.Scatter(
        x=rank_df["Channel"], y=rank_df["Avg ROI"],
        mode="lines+markers", name="Average ROI",
        line=dict(color="#3b82f6", width=3),
        marker=dict(size=10, color="#3b82f6"),
        fill="tonexty", fillcolor="rgba(239,68,68,0.06)",
        hovertemplate="<b>%{x}</b><br>Average ROI: %{y:.4f}<extra></extra>",
    ))
    fig_range.add_trace(go.Scatter(
        x=rank_df["Channel"], y=rank_df["Best ROI"],
        mode="lines+markers", name="Best Case",
        line=dict(color="#10b981", dash="dash", width=2),
        marker=dict(size=7, color="#10b981"),
        fill="tonexty", fillcolor="rgba(16,185,129,0.06)",
        hovertemplate="<b>%{x}</b><br>Best Case: %{y:.4f}<extra></extra>",
    ))
    fig_range.update_layout(
        **LAYOUT,
        height = 290,
        legend = dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0,
                      font=dict(size=11, color="#64748b")),
        xaxis  = dict(showgrid=False, color="#64748b"),
        yaxis  = dict(showgrid=True, gridcolor="#f1f5f9", color="#94a3b8", title="ROI Value"),
    )
    st.plotly_chart(fig_range, use_container_width=True)
    st.markdown("""
        <div class='tip'>
            📉 <b>ROI Range</b> = Average ± 1 standard deviation.
            The shaded band shows your realistic expected range.
        </div>
    """, unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 4 — SENSITIVITY ANALYSIS
# ─────────────────────────────────────────────────────────────────────────────

st.divider()
st.markdown("<div class='section-label'>What-If Analysis</div>", unsafe_allow_html=True)
st.markdown("<div class='section-title'>📊 How does ROI change as budget changes?</div>", unsafe_allow_html=True)

with st.spinner("Running 5 budget scenarios..."):
    sens_df = run_sensitivity(budget)

col_chart, col_info = st.columns([1.6, 1])

with col_chart:
    base_label = f"${budget:,.0f}"

    fig_sens = go.Figure()
    fig_sens.add_trace(go.Scatter(
        x             = sens_df["Budget Label"],
        y             = sens_df["Expected ROI"],
        mode          = "lines+markers",
        line          = dict(color="#3b82f6", width=3),
        marker        = dict(
            size  = [16 if l == base_label else 9 for l in sens_df["Budget Label"]],
            color = ["#f59e0b" if l == base_label else "#3b82f6" for l in sens_df["Budget Label"]],
            line  = dict(color="#ffffff", width=2),
        ),
        fill          = "tozeroy",
        fillcolor     = "rgba(59,130,246,0.06)",
        text          = sens_df["Expected ROI"].apply(lambda v: f"${v:,.2f}"),
        textposition  = "top center",
        textfont      = dict(color="#3b82f6", size=11),
        hovertemplate = "<b>%{x}</b><br>Expected ROI: %{y:,.2f}<extra></extra>",
    ))

    # Mark current budget with a diamond
    base_rows = sens_df[sens_df["Budget Label"] == base_label]
    if not base_rows.empty:
        fig_sens.add_trace(go.Scatter(
            x            = [base_label],
            y            = [base_rows["Expected ROI"].values[0]],
            mode         = "markers+text",
            text         = ["  ◄ Your Budget"],
            textposition = "middle right",
            textfont     = dict(color="#f59e0b", size=11),
            marker       = dict(size=16, color="#f59e0b", symbol="diamond",
                                line=dict(color="#ffffff", width=2)),
            showlegend   = False,
            hovertemplate= "<b>Your Budget</b><br>ROI: $%{y:,.2f}<extra></extra>",
        ))

    fig_sens.update_layout(
        **LAYOUT,
        height     = 300,
        showlegend = False,
        xaxis      = dict(showgrid=False, color="#64748b", title="Budget Scenario"),
        yaxis      = dict(showgrid=True, gridcolor="#f1f5f9", color="#94a3b8",
                          title="Expected ROI", zeroline=False),
    )
    st.plotly_chart(fig_sens, use_container_width=True)

with col_info:
    best_s    = sens_df.loc[sens_df["Expected ROI"].idxmax()]
    base_rows = sens_df[sens_df["Budget Label"] == base_label]
    base_roi  = base_rows["Expected ROI"].values[0] if not base_rows.empty else expected_roi

    st.metric("🏆 Best Budget",          best_s["Budget Label"])
    st.metric("📈 Best Expected ROI",    f"{best_s['Expected ROI']:,.2f}")
    gain = best_s["Expected ROI"] - base_roi
    #if gain > 0:
        #st.metric("💡 Gain vs Current Budget", f"+${gain:,.2f}")

    st.markdown("<br>", unsafe_allow_html=True)

    display = sens_df[["Budget Label","Change","Expected ROI","Channels"]].copy()
    display["Expected ROI"] = display["Expected ROI"].apply(lambda v: f"${v:,.2f}")
    st.dataframe(display, hide_index=True, use_container_width=True)


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 5 — SEARCH & FILTER
# ─────────────────────────────────────────────────────────────────────────────

st.divider()
st.markdown("<div class='section-label'>Channel Explorer</div>", unsafe_allow_html=True)
st.markdown("<div class='section-title'>🔍 Search & Filter Channels</div>", unsafe_allow_html=True)

if filtered:
    st.success(f"Found **{len(filtered)}** channel(s) matching your filters.")
    filter_df = pd.DataFrame([
        {
            "Channel"    : name,
            "Avg ROI"    : round(p.avg_roi, 4),
            "ROI/Dollar" : round(p.roi_per_dollar, 6),
            "Conversion" : f"{p.avg_conversion:.1%}",
            "Avg Cost"   : f"${p.avg_cost:,.0f}",
            "Risk Score" : round(p.risk_score, 3),
            "Risk"       : p.risk_label,
            "Best ROI"   : round(p.best_case_roi, 4),
            "Worst ROI"  : round(p.worst_case_roi, 4),
            "Campaigns"  : p.total_campaigns,
        }
        for name, p in filtered.items()
    ])
    st.dataframe(filter_df, hide_index=True, use_container_width=True)
else:
    st.warning("No channels match your filters. Try adjusting the sidebar settings.")


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 6 — FULL DATA TABLE (collapsed by default)
# ─────────────────────────────────────────────────────────────────────────────

st.divider()
with st.expander("📋 Full Channel Statistics — All Data", expanded=False):
    st.dataframe(rank_df, hide_index=True, use_container_width=True)


# ─────────────────────────────────────────────────────────────────────────────
# FOOTER
# ─────────────────────────────────────────────────────────────────────────────

st.markdown("""
<div style='text-align:center;color:#cbd5e1;font-size:0.78rem;
            margin-top:40px;padding:20px 0;border-top:1px solid #e2e8f0;'>
    Marketing ROI Optimizer &nbsp;·&nbsp;
    A* Search + Hill Climbing &nbsp;·&nbsp;
    200,000 Campaigns &nbsp;·&nbsp;
    Streamlit + Plotly
</div>
""", unsafe_allow_html=True)