
import streamlit as st
import pandas as pd
import json
import time
import altair as alt
from datetime import datetime

st.set_page_config(
    page_title="JIRACHI COMMANDER",
    page_icon="👁️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- CYBERPUNK STYLING ---
st.markdown("""
<style>
    /* Dark Theme Base */
    .stApp { background-color: #050505; color: #00ff41; font-family: 'Courier New', monospace; }
    
    /* Metrics */
    div[data-testid="stMetric"] {
        background-color: #111;
        border: 1px solid #333;
        padding: 15px;
        border-radius: 5px;
        box-shadow: 0 0 10px rgba(0, 255, 65, 0.1);
    }
    div[data-testid="stMetricValue"] {
        color: #fff;
        font-size: 2rem !important;
    }
    div[data-testid="stMetricLabel"] {
        color: #00ff41;
    }

    /* Headers */
    h1, h2, h3 { 
        text-shadow: 0 0 10px #00ff41; 
        color: #fff !important;
        text-transform: uppercase;
    }
    
    /* Sidebar */
    section[data-testid="stSidebar"] {
        background-color: #0a0a0a;
        border-right: 1px solid #333;
    }
    
    /* Cards */
    .decision-card {
        border-left: 5px solid;
        padding: 15px;
        margin-bottom: 10px; 
        background: #111;
        border-radius: 4px;
        border: 1px solid #222;
        transition: transform 0.1s;
    }
    .decision-card:hover {
        transform: scale(1.01);
        box-shadow: 0 0 15px rgba(0,0,0,0.5);
    }
</style>
""", unsafe_allow_html=True)

# --- SIDEBAR CONFIG ---
with st.sidebar:
    st.title("🎛️ CONTROL DECK")
    st.markdown("---")
    auto_refresh = st.checkbox("AUTO-REFRESH FEED", value=True)
    refresh_rate = st.slider("POLLING RATE (s)", 0.5, 5.0, 1.0)
    st.markdown("---")
    filter_type = st.multiselect(
        "FILTER INTEL LAYER",
        ["BLOCK", "DECEIVE", "ALLOW", "PATCH"],
        default=["BLOCK", "DECEIVE", "ALLOW", "PATCH"]
    )
    st.markdown("---")
    if st.button("CLEAR MISSION LOGS", type="primary"):
        open("mission_log.jsonl", "w").close()
        st.toast("Mission Logs Purged", icon="🗑️")

# --- MAIN HEADER ---
col_head1, col_head2 = st.columns([3, 1])
with col_head1:
    st.title("👁️ JIRACHI: GLOBAL HIVE MIND")
with col_head2:
    st.markdown(f"<div style='text-align: right; color: #555;'>SYSTEM TIME<br><span style='color: #fff; font-size: 1.2em;'>{datetime.now().strftime('%H:%M:%S')}</span></div>", unsafe_allow_html=True)

# --- LIVE METRICS CONTAINER ---
metrics_placeholder = st.empty()
charts_placeholder = st.empty()
feed_placeholder = st.empty()

def load_logs():
    data = []
    try:
        with open("mission_log.jsonl", "r") as f:
            for line in f:
                try:
                    entry = json.loads(line)
                    # Add parsed timestamp for charts - FIX: Include Date
                    t = datetime.strptime(entry['timestamp'], "%H:%M:%S").time()
                    entry['_time'] = datetime.combine(datetime.today(), t)
                    data.append(entry)
                except:
                    continue
    except FileNotFoundError:
        return []
    return data

# --- MAIN LOOP ---
if auto_refresh:
    while True:
        logs = load_logs()
        df = pd.DataFrame(logs) if logs else pd.DataFrame(columns=["timestamp", "decision", "trace", "reasoning", "_time"])

        # 1. METRICS ROW
        with metrics_placeholder.container():
            col1, col2, col3, col4 = st.columns(4)
            
            total_events = len(df)
            blocked = len(df[df['decision'] == 'BLOCK'])
            trapped = len(df[df['decision'] == 'DECEIVE'])
            
            # Status Indicator
            status_color = "red" if not logs else "green"
            status_text = "OFFLINE" if not logs else "GEMINI ACTIVE"
            
            col1.metric("TOTAL INTERCEPTIONS", total_events)
            col2.metric("THREATS BLOCKED", blocked, delta="Firewall Active", delta_color="inverse")
            col3.metric("SIREN TRAPS", trapped, delta="Deception Layer", delta_color="normal")
            col4.metric("NEURAL STATUS", status_text)

        # 2. ACTIVITY CHART
        if not df.empty:
            with charts_placeholder.container():
                # Simple time-series aggregation
                chart_data = df.copy()
                chart_data['count'] = 1
                
                # Create a base chart
                c = alt.Chart(chart_data).mark_circle(size=60).encode(
                    x=alt.X('_time', title='Timeline', axis=alt.Axis(format='%H:%M:%S', labelColor='#888', titleColor='#888')),
                    y=alt.Y('decision', title='Decision Type', axis=alt.Axis(labelColor='#888', titleColor='#888')),
                    color=alt.Color('decision', scale=alt.Scale(domain=['BLOCK', 'DECEIVE', 'ALLOW'], range=['#ff4b4b', '#ffa421', '#21c354']), legend=None),
                    tooltip=['timestamp', 'decision', 'trace']
                ).properties(
                    height=200,
                    background='transparent'
                ).configure_view(
                    strokeWidth=0
                )
                
                st.altair_chart(c, use_container_width=True)

        # 3. DECISION FEED
        with feed_placeholder.container():
            st.markdown("### 🧠 COMMANDER DECISION FEED")
            
            # Filter Data
            if not df.empty:
                filtered_df = df[df['decision'].isin(filter_type)]
                
                for i, row in filtered_df.iloc[::-1].head(10).iterrows():
                    decision = row['decision']
                    color = "#ff4b4b" if decision == "BLOCK" else "#ffa421" if decision == "DECEIVE" else "#21c354"
                    icon = "🛡️" if decision == "BLOCK" else "🧜‍♀️" if decision == "DECEIVE" else "✅"
                    
                    st.markdown(f"""
                    <div class="decision-card" style="border-left-color: {color};">
                        <div style="display: flex; justify-content: space-between; align-items: center;">
                            <strong style="color: {color}; font-size: 1.1em;">{icon} [{row['timestamp']}] {decision}</strong>
                            <small style="color: #666;">ID: {i}</small>
                        </div>
                        <div style="margin-top: 5px; color: #ccc; font-family: monospace; font-size: 0.9em; background: #000; padding: 5px; border-radius: 3px;">
                            {row.get('trace', 'N/A')}
                        </div>
                        <div style="margin-top: 5px; color: #8b949e; font-style: italic;">
                            Gemini: "{row.get('reasoning', 'No reasoning provided')}"
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
            else:
                 st.info("Awaiting Neuro-Symbolic Link...")

        time.sleep(refresh_rate)
else:
    st.info("Auto-Refresh Paused. Enable in Sidebar.")
