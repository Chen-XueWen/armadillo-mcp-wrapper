import streamlit as st
import pandas as pd
import sqlite3
import time
import sys
import os
import altair as alt

# Add project root to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.db import get_connection, update_status

st.set_page_config(page_title="Governor-MCP | Enterprise", layout="wide", page_icon="🛡️")

# --- Custom CSS (Enterprise Theme) ---
st.markdown("""
<style>
    /* Global Styles */
    .stApp {
        background-color: #f8f9fa;
        font-family: 'Inter', sans-serif;
    }
    
    /* Sidebar */
    [data-testid="stSidebar"] {
        background-color: #ffffff;
        border-right: 1px solid #e5e7eb;
    }
    
    /* Metrics */
    [data-testid="stMetric"] {
        background-color: white;
        padding: 15px;
        border-radius: 8px;
        border: 1px solid #e5e7eb;
        box-shadow: 0 1px 2px 0 rgba(0, 0, 0, 0.05);
    }
    
    /* Tabs */
    .stTabs [data-baseweb="tab-list"] {
        gap: 20px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        white-space: pre-wrap;
        background-color: white;
        border-radius: 4px;
        color: #4b5563;
        font-weight: 600;
    }
    .stTabs [aria-selected="true"] {
        background-color: #ebf5ff;
        color: #2563eb;
    }
    
    /* Status Badges in Tables (Custom) */
    .status-badge {
        padding: 4px 8px;
        border-radius: 12px;
        font-size: 12px;
        font-weight: 600;
    }
    
    /* Cards */
    .card {
        background: white;
        padding: 20px;
        border-radius: 10px;
        border: 1px solid #e5e7eb;
        margin-bottom: 20px;
    }
</style>
""", unsafe_allow_html=True)

# --- Config & Data ---
def load_data():
    conn = get_connection()
    df = pd.read_sql_query("SELECT * FROM requests ORDER BY timestamp DESC LIMIT 500", conn)
    conn.close()
    return df

def approve_request(req_id):
    update_status(req_id, "APPROVED")
    st.toast(f"✅ Approved Request: {req_id[:8]}")

def deny_request(req_id):
    update_status(req_id, "DENIED")
    st.toast(f"❌ Denied Request: {req_id[:8]}")

# --- Sidebar Controls ---
with st.sidebar:
    st.title("🛡️ Governor")
    st.caption("v1.2.0 • Enterprise Edition")
    st.divider()
    
    st.subheader("Controls")
    auto_refresh = st.toggle("Auto-Refresh (Live)", value=True)
    refresh_rate = st.slider("Rate (s)", 1, 10, 2, disabled=not auto_refresh)
    
    if st.button("🔄 Manual Refresh", use_container_width=True):
        st.rerun()
        
    st.divider()
    st.subheader("Filters")
    status_filter = st.multiselect(
        "Status",
        ["PENDING", "APPROVED", "DENIED", "BLOCKED", "COMPLETED"],
        default=["PENDING", "APPROVED", "DENIED", "BLOCKED", "COMPLETED"]
    )

# --- Main Logic ---
df = load_data()

# Apply Sidebar Filters
if not df.empty and status_filter:
    df = df[df['status'].isin(status_filter)]

# Header Stats
if not df.empty:
    total = len(df)
    pending = len(df[df['status'] == 'PENDING'])
    blocked = len(df[df['status'] == 'BLOCKED'])
    
    # Calculate Threat Score
    threat_score = (blocked * 5 + pending * 2) / max(total, 1) * 10
    threat_delta = "off"
    if threat_score > 5: threat_delta = "inverse"
    
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Traffic Volume", total, help="Total requests processed in trailing window")
    c2.metric("Pending Actions", pending, delta=pending if pending > 0 else None, delta_color="inverse")
    c3.metric("Blocked Threats", blocked, delta_color="off")
    c4.metric("Risk Score", f"{threat_score:.1f}/10", delta_color=threat_delta)

# --- Tabs Layout ---
tab_dashboard, tab_actions, tab_audit = st.tabs(["📊 Dashboard", "⚡ Action Center", "📜 Audit Log"])

# 1. Dashboard Tab (Analytics)
with tab_dashboard:
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader("Traffic Velocity")
        if not df.empty:
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            line_chart = alt.Chart(df).mark_area(
                opacity=0.6,
                interpolate='step'
            ).encode(
                x=alt.X('timestamp', axis=alt.Axis(format='%H:%M:%S', title='Time')),
                y=alt.Y('count()', title='Requests'),
                color=alt.Color('status', scale=alt.Scale(
                    domain=['COMPLETED', 'BLOCKED', 'PENDING', 'APPROVED', 'DENIED'],
                    range=['#10b981', '#ef4444', '#f59e0b', '#3b82f6', '#991b1b']
                ))
            ).properties(height=300)
            st.altair_chart(line_chart, use_container_width=True)
            
    with col2:
        st.subheader("Tool Distribution")
        if not df.empty:
            donut = alt.Chart(df).mark_arc(innerRadius=50).encode(
                theta=alt.Theta("count()"),
                color=alt.Color("tool_name"),
                tooltip=["tool_name", "count()"]
            ).properties(height=300)
            st.altair_chart(donut, use_container_width=True)

# 2. Action Center Tab (HITL)
with tab_actions:
    if not df.empty:
        pending_df = df[df['status'] == 'PENDING']
        if pending_df.empty:
            st.info("✅ No pending actions. All systems nominal.")
        else:
            st.warning(f"⚠️ {len(pending_df)} Request(s) requiring approval")
            
            for index, row in pending_df.iterrows():
                with st.container():
                    # Card-like layout
                    c1, c2, c3 = st.columns([0.1, 0.7, 0.2])
                    with c1:
                        st.markdown("### 🛑")
                    with c2:
                        st.markdown(f"**{row['tool_name']}**")
                        st.caption(f"Risk: {row['risk_level'].upper()} • Reason: {row['policy_reason']}")
                        with st.expander("Payload Details"):
                            st.code(row['args'], language="json")
                    with c3:
                        if st.button("Approve", key=f"a_{row['id']}", type="primary", use_container_width=True):
                            approve_request(row['id'])
                            st.rerun()
                        if st.button("Deny", key=f"d_{row['id']}", use_container_width=True):
                            deny_request(row['id'])
                            st.rerun()
                    st.divider()

# 3. Audit Log Tab (Data Grid)
with tab_audit:
    if not df.empty:
        # Configuration for the advanced data editor
        st.dataframe(
            df,
            column_config={
                "status": st.column_config.TextColumn(
                    "Status",
                    help="Request Status"
                ),
                "timestamp": st.column_config.DatetimeColumn(
                    "Timestamp",
                    format="D MMM, HH:mm:ss"
                ),
                "args": st.column_config.TextColumn("Arguments", width="medium"),
                "tool_name": st.column_config.TextColumn("Tool", width="small"),
                "risk_level": st.column_config.TextColumn("Risk", width="small")
            },
            hide_index=True,
            use_container_width=True,
            height=600
        )

# Auto-refresh logic
if auto_refresh:
    time.sleep(refresh_rate)
    st.rerun()
