import streamlit as st
import json
import os

from scenarios import SCENARIOS
from runner import run_scenario
from renderer import (
    inject_css,
    render_header,
    render_landing,
    render_isolation_comparison,
    render_scenario_intro,
    render_step_execution,
    render_timeline,
    render_anomaly_report,
    render_storage_state,
)

# ─────────────────────────────────────
# PAGE CONFIG
# ─────────────────────────────────────
st.set_page_config(
    page_title="AcidProbe",
    page_icon="🔬",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ─────────────────────────────────────
# DESIGN TOKENS
# ─────────────────────────────────────
inject_css()

# ─────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────
with st.sidebar:
    st.markdown("## 🔬 AcidProbe")
    st.markdown("<p style='color:#475569; font-size:0.8rem;'>ACID Violation Detector</p>", unsafe_allow_html=True)
    st.markdown("---")

    mode = st.radio("Input Mode", ["Preset Scenario", "Custom JSON"], index=0, label_visibility="collapsed")

    st.markdown("---")

    config = None
    is_isolation = False

    if mode == "Preset Scenario":
        scenario_key = st.selectbox("Choose Scenario", list(SCENARIOS.keys()), label_visibility="visible")
        scenario     = SCENARIOS[scenario_key]
        config       = scenario.copy()

        if scenario["isolation_level"] != "ALL":
            isolation = st.selectbox(
                "Isolation Level",
                ["READ_UNCOMMITTED", "READ_COMMITTED", "REPEATABLE_READ", "SERIALIZABLE"],
                index=["READ_UNCOMMITTED","READ_COMMITTED","REPEATABLE_READ","SERIALIZABLE"].index(scenario["isolation_level"])
            )
            config["isolation_level"] = isolation
        else:
            is_isolation = True
            st.info("Runs all 4 isolation levels automatically")

    else:
        default_json = ""
        if os.path.exists("config.json"):
            try:
                with open("config.json", "r") as f:
                    default_json = f.read()
            except Exception:
                pass
        if not default_json:
            default_json = json.dumps({
                "scenario_name": "My Custom Test",
                "isolation_level": "READ_COMMITTED",
                "initial_data": {"balance": 1000},
                "transactions": [
                    {"tid": "T1", "operations": [
                        {"op": "READ",  "key": "balance"},
                        {"op": "WRITE", "key": "balance", "value": 700},
                        {"op": "COMMIT"}
                    ]},
                    {"tid": "T2", "operations": [
                        {"op": "READ",  "key": "balance"},
                        {"op": "WRITE", "key": "balance", "value": 800},
                        {"op": "COMMIT"}
                    ]}
                ]
            }, indent=2)

        raw = st.text_area("Paste config.json", height=280, value=default_json)
        try:
            config = json.loads(raw)
            config["what_is_this"] = f"Custom scenario: **{config.get('scenario_name', 'Unnamed')}**"
            config["concepts"] = []
        except Exception:
            st.error("Invalid JSON")
            config = None

    st.markdown("---")
    run_btn = st.button("▶  Run Simulation", type="primary", use_container_width=True)

# ─────────────────────────────────────
# HEADER
# ─────────────────────────────────────
render_header()

# ─────────────────────────────────────
# MAIN OUTPUT
# ─────────────────────────────────────
if run_btn and config:

    # ── ISOLATION SWITCHER ──
    if is_isolation:
        render_isolation_comparison(config)
        st.stop()

    # ── NORMAL SCENARIO ──
    result = run_scenario(config)

    render_scenario_intro(config, result)

    # TABS
    tab1, tab2, tab3, tab4 = st.tabs([
        "⚡ Step Execution",
        "📅 Timeline View",
        "⚠️ Anomaly Report",
        "🗃️ Storage & State"
    ])

    with tab1:
        render_step_execution(result)

    with tab2:
        render_timeline(result)

    with tab3:
        render_anomaly_report(result)

    with tab4:
        render_storage_state(result)

else:
    render_landing()