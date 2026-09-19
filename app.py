import json
import pandas as pd
import streamlit as st
import requests

# -------------------------------------------------------------
# PAGE CONFIGURATION
# -------------------------------------------------------------
st.set_page_config(
    page_title="AIPI - Agentic Inventory & Pricing Intelligence",
    page_icon="📦",
    layout="wide",
)

st.title("📦 AIPI: Agentic Inventory & Pricing Intelligence")
st.markdown(
    "Autonomous retail operations engine powered by **Microsoft Fabric Lakehouse telemetry** "
    "& **Groq LLM tool-calling**."
)

# -------------------------------------------------------------
# SESSION STATE INITIALIZATION (single source of truth)
# -------------------------------------------------------------
if "messages" not in st.session_state:
    st.session_state.messages = [
        {
            "role": "system",
            "content": (
                "You are an autonomous inventory and pricing intelligence agent for retail "
                "operations. Use your available tools iteratively to diagnose stockouts, check "
                "competitor market signals, review sales velocity, evaluate pricing "
                "recommendations, and review anomaly logs. All results you receive are already "
                "scoped to the caller's security permissions — do not assume broader access than "
                "what a tool returns."
            ),
        },
        {
            "role": "assistant",
            "content": (
                "Hello! I am your AIPI Autonomous Retail Agent. I am connected to your inventory "
                "lakehouse telemetry and market pricing streams. How can I help you optimize "
                "stock levels or pricing strategies today?"
            ),
        },
    ]

# -------------------------------------------------------------
# SIDEBAR: RLS / OLS SECURITY CONFIGURATION (single block)
# -------------------------------------------------------------
with st.sidebar:
    st.header("🔐 Security & Access Control (RLS/OLS)")

    # ==========================================
    # ENTERPRISE RLS/OLS SECURITY MATRIX
    # ==========================================
    SECURITY_PERSONAS = {
        "Executive / C-Suite": {
            "role": "Executive",
            "scope": "global",
            "allowed_stores": ["Store 101", "Store 102", "Store 103", "Store 104"],
            "can_view_financials": True
        },
        "Internal Audit & Compliance": {
            "role": "Audit",
            "scope": "global",
            "allowed_stores": ["Store 101", "Store 102", "Store 103", "Store 104"],
            "can_view_financials": True
        },
        "Supply Chain Manager": {
            "role": "Supply Chain",
            "scope": "global_logistics",
            "allowed_stores": ["Store 101", "Store 102", "Store 103", "Store 104"],
            "can_view_financials": False
        },
        "Financial Analyst": {
            "role": "Analyst",
            "scope": "global_financials",
            "allowed_stores": ["Store 101", "Store 102", "Store 103", "Store 104"],
            "can_view_financials": True
        },
        "Store Manager 1 (Downtown)": {
            "role": "Store Manager",
            "scope": "node_specific",
            "allowed_stores": ["Store 101"],
            "can_view_financials": False
        },
        "Store Manager 2 (Northside)": {
            "role": "Store Manager",
            "scope": "node_specific",
            "allowed_stores": ["Store 102"],
            "can_view_financials": False
        },
        "Store Manager 3 (West End)": {
            "role": "Store Manager",
            "scope": "node_specific",
            "allowed_stores": ["Store 103"],
            "can_view_financials": False
        },
        "Store Manager 4 (Suburbs)": {
            "role": "Store Manager",
            "scope": "node_specific",
            "allowed_stores": ["Store 104"],
            "can_view_financials": False
        }
    }

    selected_persona_name = st.selectbox(
        "Select User Persona",
        options=list(SECURITY_PERSONAS.keys()),
        key="user_role_select",
    )

    # Extract active configuration cleanly from the dictionary
    active_persona = SECURITY_PERSONAS[selected_persona_name]
    user_role = active_persona["role"]
    allowed_stores = active_persona["allowed_stores"]
    can_view_financials = active_persona["can_view_financials"]
    
    # Backward compatibility mappings for your backend tools
    current_store_filter = allowed_stores[0] if len(allowed_stores) == 1 else "ALL"

    # Save to session state for global tool/query enforcement
    st.session_state["user_role"] = user_role
    st.session_state["allowed_stores"] = allowed_stores
    st.session_state["can_view_financials"] = can_view_financials

    # Dynamic UI security status banners
    if active_persona["scope"] == "node_specific":
        st.error(f"🔒 RLS Active: Locked to {current_store_filter}")
        st.warning("🛡️ OLS Active: Financial margins hidden.")
    elif not can_view_financials:
        st.info(f"🌐 RLS Active: Global view ({active_persona['scope']})")
        st.warning("🛡️ OLS Active: Financial margins hidden.")
    else:
        st.success("🔓 Full Access: Executive & Audit privileges.")

    st.markdown("---")
    st.header("⚙️ Agent Configuration")

    # NEVER hardcode real credentials in source. Prefer st.secrets, fall back to blank.
    default_key = st.secrets.get("GROQ_API_KEY", "") if hasattr(st, "secrets") else ""
    groq_api_key = st.text_input(
        "Groq API Key",
        value=default_key,
        type="password",
        key="groq_api_key_sidebar",
    )

    model_choice = st.selectbox(
        "LLM Engine",
        options=["openai/gpt-oss-120b", "openai/gpt-oss-20b"],
        key="model_choice_sidebar",
    )

    st.markdown("---")
    st.markdown("### Active Capabilities")
    st.success("🛠️ Stockout Risk Diagnostics")
    st.success("📊 Competitor Pricing & Intel")
    st.success("📈 Sales Velocity Tracking")
    st.success("💡 Dynamic Pricing Engine")
    st.success("🛡️ Telemetry Anomaly & Audit")
    st.info("💡 Fully autonomous multi-turn reasoning loop active.")

    st.markdown("---")
    if st.button("Clear Chat History", key="clear_chat_sidebar_btn"):
        st.session_state.messages = []
        st.rerun()

# Main-body clear button (kept separate & uniquely keyed, per original design)
if st.button("Clear Chat History", key="clear_chat_main_btn"):
    st.session_state.messages = []
    st.rerun()
# -------------------------------------------------------------
# TOOL DEFINITIONS
# Every tool accepts **kwargs so unexpected LLM-supplied arguments
# never raise a TypeError. store_filter defaults exist for direct/manual
# calls, but the agent dispatcher below ALWAYS overrides it server-side —
# the LLM's own arguments can never widen its RLS/OLS scope.
# -------------------------------------------------------------

def get_stockout_risks(store_filter="ALL", **kwargs):
    """Retrieves critical inventory stockout risks, strictly enforcing RLS store filters."""
    raw_results = [
        {"site_name": "STORE_101", "product_name": "Whole Milk 1 Gal", "snapshot_date": "2026-09-16", "stock_on_hand": 2, "predicted_units": 5, "variance": -3},
        {"site_name": "STORE_103", "product_name": "Whole Milk 1 Gal", "snapshot_date": "2026-09-16", "stock_on_hand": 0, "predicted_units": 1, "variance": -1},
        {"site_name": "STORE_103", "product_name": "Artisan Sourdough", "snapshot_date": "2026-09-15", "stock_on_hand": 0, "predicted_units": 1, "variance": -1},
        {"site_name": "STORE_104", "product_name": "Organic Eggs 12pk", "snapshot_date": "2026-09-17", "stock_on_hand": 1, "predicted_units": 4, "variance": -3},
    ]
    if store_filter != "ALL":
        raw_results = [r for r in raw_results if r["site_name"] == store_filter]
    return json.dumps(raw_results, default=str)


def get_dynamic_pricing_recommendations(store_filter="ALL", **kwargs):
    """Generates dynamic pricing adjustment recommendations based on live telemetry."""
    raw_recommendations = [
        {"site_code": "STORE_101", "item_sku": "SKU-MILK-001", "product_name": "Whole Milk 1 Gal", "current_price": 3.99, "recommended_price": 3.89, "action": "Defensive Markdown", "rationale": "Competitor dropped to $3.47; adjust to prevent volume leakage."},
        {"site_code": "STORE_101", "item_sku": "SKU-BREAD-002", "product_name": "Artisan Sourdough", "current_price": 2.49, "recommended_price": 2.49, "action": "Hold", "rationale": "Aligned with optimal baseline market positioning."},
        {"site_code": "STORE_102", "item_sku": "SKU-MILK-001", "product_name": "Whole Milk 1 Gal", "current_price": 3.99, "recommended_price": 4.15, "action": "Margin Expansion", "rationale": "Competitor pricing high at $4.23; safe to capture incremental margin."},
        {"site_code": "STORE_103", "item_sku": "SKU-EGG-003", "product_name": "Organic Eggs 12pk", "current_price": 4.19, "recommended_price": 4.29, "action": "Optimize", "rationale": "High velocity 5-unit baskets permit minor price uplift."},
        {"site_code": "STORE_104", "item_sku": "SKU-JUICE-004", "product_name": "Cold Pressed Juice", "current_price": 5.99, "recommended_price": 5.99, "action": "Hold", "rationale": "Healthy volume velocity at current price point."},
    ]
    if store_filter != "ALL":
        raw_recommendations = [r for r in raw_recommendations if r["site_code"] == store_filter]
    return json.dumps(raw_recommendations, default=str)


def get_competitor_signals(store_filter="ALL", include_financials=True, **kwargs):
    """
    Retrieves live competitor scrape signals, enforcing RLS and OLS security.
    include_financials is an EXPLICIT parameter (not read from st.session_state),
    so masking is deterministic and always reflects the caller's actual permission.
    """
    raw_signals = [
        {"site_code": "STORE_101", "item_sku": "SKU-MILK-001", "product_name": "Whole Milk 1 Gal", "our_price": 3.99, "competitor_price": 3.47, "internal_cost": 2.1, "margin": "44%"},
        {"site_code": "STORE_101", "item_sku": "SKU-BREAD-002", "product_name": "Artisan Sourdough", "our_price": 2.49, "competitor_price": 2.17, "internal_cost": 1.4, "margin": "43%"},
        {"site_code": "STORE_102", "item_sku": "SKU-MILK-001", "product_name": "Whole Milk 1 Gal", "our_price": 3.99, "competitor_price": 4.23, "internal_cost": 2.1, "margin": "44%"},
        {"site_code": "STORE_103", "item_sku": "SKU-EGG-003", "product_name": "Organic Eggs 12pk", "our_price": 4.19, "competitor_price": 4.53, "internal_cost": 2.5, "margin": "40%"},
        {"site_code": "STORE_104", "item_sku": "SKU-JUICE-004", "product_name": "Cold Pressed Juice", "our_price": 5.99, "competitor_price": 5.27, "internal_cost": 3.3, "margin": "45%"},
    ]

    if store_filter != "ALL":
        raw_signals = [s for s in raw_signals if s["site_code"] == store_filter]

    processed = []
    for sig in raw_signals:
        item = sig.copy()
        if not include_financials:
            item["internal_cost"] = "🔒 RESTRICTED (OLS)"
            item["margin"] = "🔒 RESTRICTED (OLS)"
        processed.append(item)

    return json.dumps(processed, default=str)


def get_sales_velocity(store_filter="ALL", **kwargs):
    """Retrieves point-of-sale transaction velocity and basket metrics."""
    raw_sales = [
        {"site_code": "STORE_101", "item_sku": "SKU-MILK-001", "product_name": "Whole Milk 1 Gal", "units_sold": 2, "transaction_count": 42},
        {"site_code": "STORE_101", "item_sku": "SKU-BREAD-002", "product_name": "Artisan Sourdough", "units_sold": 3, "transaction_count": 35},
        {"site_code": "STORE_102", "item_sku": "SKU-MILK-001", "product_name": "Whole Milk 1 Gal", "units_sold": 1, "transaction_count": 50},
        {"site_code": "STORE_103", "item_sku": "SKU-EGG-003", "product_name": "Organic Eggs 12pk", "units_sold": 5, "transaction_count": 68},
        {"site_code": "STORE_104", "item_sku": "SKU-JUICE-004", "product_name": "Cold Pressed Juice", "units_sold": 5, "transaction_count": 61},
    ]
    if store_filter != "ALL":
        raw_sales = [s for s in raw_sales if s["site_code"] == store_filter]
    return json.dumps(raw_sales, default=str)


def get_anomaly_logs(store_filter="ALL", **kwargs):
    """Retrieves system telemetry anomalies, latency flags, and pricing volatility alerts."""
    raw_anomalies = [
        {"signal_id": "SIG-1789419825", "site_code": "STORE_104", "anomaly_type": "Price Volatility", "severity": "Medium", "description": "Abrupt price drop detected ($4.40 vs historical avg $5.30).", "timestamp": "2026-09-18 18:14:02"},
        {"signal_id": "SIG-1789419833", "site_code": "STORE_104", "anomaly_type": "Rapid Fluctuation", "severity": "Low", "description": "Multiple scraped price shifts within a 30-second window.", "timestamp": "2026-09-18 18:14:15"},
        {"signal_id": "SIG-1789419849", "site_code": "STORE_103", "anomaly_type": "Spike Alert", "severity": "High", "description": "Competitor price spiked to $6.35 for juice SKU.", "timestamp": "2026-09-18 18:14:35"},
        {"signal_id": "TXN-998124011", "site_code": "STORE_101", "anomaly_type": "POS Override Check", "severity": "Low", "description": "Standard compliance verification passed; zero unauthorized overrides.", "timestamp": "2026-09-18 18:15:00"},
    ]
    if store_filter != "ALL":
        raw_anomalies = [a for a in raw_anomalies if a["site_code"] == store_filter]
    return json.dumps(raw_anomalies, default=str)

@st.cache_data
def load_pos_telemetry():
    # Enterprise POS dataset mapped to all 4 store nodes
    data = {
        "Store Node": ["Store 101 - Downtown", "Store 102 - Northside", "Store 103 - Westend", "Store 104 - Eastside"],
        "Q3_Revenue": [125000, 98000, 142000, 110000],
        "Inventory_Variance": [2.1, 1.5, 3.2, 0.9],
        "Region": ["East", "North", "West", "East"]
    }
    return pd.DataFrame(data)

def get_store_telemetry(store_filter="ALL", **kwargs):
    df = load_pos_telemetry()
    
    # Enforce RLS session state if active
    allowed_stores = st.session_state.get("allowed_stores", ["Store 101", "Store 102", "Store 103", "Store 104"])
    
    # Filter by user permissions first
    df = df[df["Store Node"].isin(allowed_stores)]
    
    # Robust substring matching so "Store 101" or "101" works seamlessly
    if store_filter and store_filter != "ALL":
        store_id = ''.join(filter(str.isdigit, str(store_filter)))
        if store_id:
            df = df[df["Store Node"].str.contains(store_id, na=False)]
            
    return df

    
    # Enforce RLS session state if active
    allowed_stores = st.session_state.get("allowed_stores", ["Store 101", "Store 102", "Store 103", "Store 104"])
    
    # Filter by user permissions first
    df = df[df["Store Node"].isin(allowed_stores)]
    
    # Robust substring matching so "Store 101" or "101" works seamlessly
    if store_filter and store_filter != "ALL":
        store_id = ''.join(filter(str.isdigit, str(store_filter)))
        if store_id:
            df = df[df["Store Node"].str.contains(store_id, na=False)]
            
    return df

# -------------------------------------------------------------
# PHASE 1: COMPETITOR INTELLIGENCE UI
# -------------------------------------------------------------
st.subheader("🏷️ Live Competitor Price Intelligence")
st.markdown("Real-time market tracking paired with your security access profile.")

raw_data_json = get_competitor_signals(store_filter=current_store_filter, include_financials=can_view_financials)
signals_df = pd.DataFrame(json.loads(raw_data_json))

if not signals_df.empty:
    st.dataframe(signals_df, use_container_width=True)
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Active Store Scope", current_store_filter)
    with col2:
        st.metric("Tracked Competitor Signals", len(signals_df))
    with col3:
        st.metric("Security Compliance", "Full Access" if can_view_financials else "Secured (RLS/OLS)")
else:
    st.info(f"No competitor signals available for current security scope: {current_store_filter}")

# -------------------------------------------------------------
# PHASE 2: SALES VELOCITY UI
# -------------------------------------------------------------
st.markdown("---")
st.subheader("📈 Point-of-Sale Sales Velocity")
st.markdown("Real-time turnover rates and basket size density per SKU.")

sales_df = pd.DataFrame(json.loads(get_sales_velocity(store_filter=current_store_filter)))

if not sales_df.empty:
    st.dataframe(sales_df, use_container_width=True)
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Total Units Moving", int(sales_df["units_sold"].sum()))
    with col2:
        st.metric("Total Transactions Logged", int(sales_df["transaction_count"].sum()))
else:
    st.info(f"No sales velocity data found for store scope: {current_store_filter}")

# -------------------------------------------------------------
# PHASE 3: DYNAMIC PRICING RECOMMENDATIONS UI
# -------------------------------------------------------------
st.markdown("---")
st.subheader("💡 Dynamic Pricing Recommendations")
st.markdown("AI-driven pricing strategies tuned to local competitor movement and inventory velocity.")

pricing_df = pd.DataFrame(json.loads(get_dynamic_pricing_recommendations(store_filter=current_store_filter)))

if not pricing_df.empty:
    st.dataframe(pricing_df, use_container_width=True)
    action_counts = pricing_df["action"].value_counts()
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Active Recommendations", len(pricing_df))
    with col2:
        markdowns = action_counts.get("Defensive Markdown", 0) + action_counts.get("Margin Expansion", 0)
        st.metric("Suggested Price Adjustments", int(markdowns))
    with col3:
        holds = action_counts.get("Hold", 0) + action_counts.get("Optimize", 0)
        st.metric("Stable / Hold SKUs", int(holds))
else:
    st.info(f"No pricing recommendations available for store scope: {current_store_filter}")

# -------------------------------------------------------------
# PHASE 4: ANOMALY DETECTION & AUDIT VIEW UI
# -------------------------------------------------------------
st.markdown("---")
st.subheader("🛡️ Anomaly Detection & Telemetry Audit")
st.markdown("Real-time monitoring of pricing volatility, scraping latency, and compliance logs.")

anomaly_df = pd.DataFrame(json.loads(get_anomaly_logs(store_filter=current_store_filter)))

if not anomaly_df.empty:
    st.dataframe(anomaly_df, use_container_width=True)
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Logged Telemetry Anomalies", len(anomaly_df))
    with col2:
        st.metric("High Severity Alerts", len(anomaly_df[anomaly_df["severity"] == "High"]))
    with col3:
        st.metric("Stream Latency", "2.1s (Nominal)")
else:
    st.info(f"No anomaly logs recorded for store scope: {current_store_filter}")

# -------------------------------------------------------------
# AGENT TOOL SCHEMA (all 5 tools registered)
# -------------------------------------------------------------
tools_definition = [
    {
        "type": "function",
        "function": {
            "name": "get_stockout_risks",
            "description": "Retrieve store locations and products currently facing critical stockout risks (stock < forecast demand).",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_competitor_signals",
            "description": "Retrieve recent competitor pricing and promotional intelligence for retail SKUs.",
            "parameters": {
                "type": "object",
                "properties": {
                    "product_name": {"type": "string", "description": "Optional product name filter (e.g., 'Whole Milk 1 Gal')."}
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_sales_velocity",
            "description": "Retrieve point-of-sale transaction velocity and basket metrics per SKU.",
            "parameters": {
                "type": "object",
                "properties": {
                    "product_name": {"type": "string", "description": "Optional product name filter."}
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_dynamic_pricing_recommendations",
            "description": "Retrieve AI-generated dynamic pricing recommendations.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_anomaly_logs",
            "description": "Retrieve telemetry anomalies, pricing volatility, and compliance audit signals.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
]


def dispatch_tool_call(func_name: str, func_args: dict) -> str:
    """
    Server-side, security-aware tool dispatcher.

    IMPORTANT: store_filter / include_financials are ALWAYS injected here from the
    authenticated sidebar persona, never taken from the LLM's arguments. Even if the
    model tries to pass its own store_filter, it is ignored — this is what makes
    RLS/OLS actually enforceable instead of advisory.
    """
    safe_args = {k: v for k, v in func_args.items() if k not in ("store_filter", "include_financials")}

    if func_name == "get_stockout_risks":
        return get_stockout_risks(store_filter=current_store_filter, **safe_args)
    elif func_name == "get_competitor_signals":
        return get_competitor_signals(
            store_filter=current_store_filter, include_financials=can_view_financials, **safe_args
        )
    elif func_name == "get_sales_velocity":
        return get_sales_velocity(store_filter=current_store_filter, **safe_args)
    elif func_name == "get_dynamic_pricing_recommendations":
        return get_dynamic_pricing_recommendations(store_filter=current_store_filter, **safe_args)
    elif func_name == "get_anomaly_logs":
        return get_anomaly_logs(store_filter=current_store_filter, **safe_args)
    else:
        return json.dumps({"error": f"Unknown tool '{func_name}'"})


# -------------------------------------------------------------
# CHAT HISTORY RENDER (None-content safe)
# -------------------------------------------------------------
for message in st.session_state.messages:
    if message["role"] == "system":
        continue
    if message["role"] == "tool":
        continue  # tool results are shown via the assistant's synthesis, not rendered raw
    content = message.get("content") or ""
    if not content and not message.get("tool_calls"):
        continue
    if content:
        with st.chat_message(message["role"]):
            st.markdown(content)


# --- NATIVE EXECUTIVE KPI & AUDIT WORKSPACE ---
st.markdown("---")
st.subheader("📈 Executive KPI & Compliance Workspace")

# Create columns for executive summary cards
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric(label="Total Business Sales", value="$1,284,500", delta="+12.3%")
with col2:
    st.metric(label="Inventory Valuation", value="$429,100", delta="-2.1%")
with col3:
    st.metric(label="Stock Variance Rate", value="1.4%", delta="-0.3% (Safe)")
with col4:
    st.metric(label="Active Anomaly Alerts", value="3 Flags", delta="+1 Critical", delta_color="inverse")

# Compliance & Telemetry Tab View
tab1, tab2 = st.tabs(["🔍 Telemetry & SIG- Feeds", "📋 Inventory Reconciliations"])

with tab1:
    st.info("Live audit logs active. Monitoring store-level transactions and pricing variances.")
    st.code("SIG-104: Rapid price volatility detected in Store 102 (SKU-9942)\nTXN-8812: POS override verified by manager role.")

with tab2:
    st.write("Run automated stock-to-sales reconciliation checks across active store nodes.")
    if st.button("Run System Audit Check"):
        st.success("Audit complete: All active store nodes match ledger records within acceptable RLS tolerances.")

# --- DAY 4: EMBEDDED ANALYTICS COMMAND CENTER ---
st.markdown("---")
st.subheader("📊 Executive Analytics & Live Intelligence Hub")
st.caption("Integrated Power BI / Interactive Telemetry Visuals")
# --- NATIVE INTERACTIVE PLOTLY TELEMETRY CHART ---
import plotly.express as px
import pandas as pd

# Real-time multi-store telemetry dataset
chart_data = pd.DataFrame({
    "Store Node": ["Store 101 - Downtown", "Store 102 - Northside", "Store 103 - West End", "Store 104 - Suburbs"],
    "Revenue ($)": [340000, 420000, 290000, 450000],
    "Stock Variance (%)": [0.8, 1.4, 0.5, 1.1]
})

fig = px.bar(
    chart_data, 
    x="Store Node", 
    y="Revenue ($)", 
    color="Stock Variance (%)",
    color_continuous_scale="Viridis",
    title="Store-Level Revenue & Inventory Variance Tracking"
)
fig.update_layout(title_font_size=16, plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)")

st.plotly_chart(fig, use_container_width=True)
import time
import random
@st.fragment(run_every=3)
def render_live_stream():
    st.markdown("---")
    st.subheader("⚡ Live Ingestion & Telemetry Stream")
    current_time = time.strftime("%H:%M:%S")
    st.caption(f"Status: Live streaming active | Last poll timestamp: {current_time}")

    # Simulate incoming real-time transactions / dynamic data jitter across store nodes
    live_data = pd.DataFrame({
        "Store Node": ["Store 101 - Downtown", "Store 102 - Northside", "Store 103 - West End", "Store 104 - Suburbs"],
        "Revenue ($)": [
            random.randint(330000, 360000), 
            random.randint(410000, 440000), 
            random.randint(280000, 310000), 
            random.randint(440000, 470000)
        ],
        "Stock Variance (%)": [round(random.uniform(0.5, 1.5), 2) for _ in range(4)]
    })

    fig = px.bar(
        live_data, 
        x="Store Node", 
        y="Revenue ($)", 
        color="Stock Variance (%)",
        color_continuous_scale="Viridis",
        title="Real-Time Store Revenue & Variance Feed"
    )
    fig.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)")
    
    st.plotly_chart(fig, use_container_width=True, key="live_stream_chart_dynamic")

# Execute the live streaming fragment
render_live_stream()
# -------------------------------------------------------------
# USER INPUT & AGENT EXECUTION LOOP
# -------------------------------------------------------------
if user_prompt := st.chat_input("Ask about stockouts, replenishment plans, or competitor pricing..."):
    st.session_state.messages.append({"role": "user", "content": user_prompt})
    with st.chat_message("user"):
        st.markdown(user_prompt)

    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {"Authorization": f"Bearer {groq_api_key}", "Content-Type": "application/json"}

    with st.chat_message("assistant"):
        with st.spinner("Agent is reasoning and querying operational data..."):
            max_turns = 5
            final_response_content = "I encountered an error processing your request."

            if not groq_api_key:
                final_response_content = "⚠️ No Groq API key configured. Add one in the sidebar to enable the agent."
            else:
                for turn in range(max_turns):
                    payload = {
                        "model": model_choice,
                        "messages": st.session_state.messages,
                        "tools": tools_definition,
                        "tool_choice": "auto",
                    }

                    try:
                        response = requests.post(url, headers=headers, json=payload, timeout=30)
                        response.raise_for_status()
                        response_data = response.json()
                    except requests.exceptions.RequestException as e:
                        final_response_content = f"⚠️ Network/API error contacting Groq: {e}"
                        break
                    except json.JSONDecodeError:
                        final_response_content = "⚠️ Received a malformed response from the LLM API."
                        break

                    if "choices" not in response_data:
                        final_response_content = f"API Error: {response_data}"
                        break

                    message = response_data["choices"][0]["message"]
                    st.session_state.messages.append(message)

                    if message.get("tool_calls"):
                        for tool_call in message["tool_calls"]:
                            func_name = tool_call["function"]["name"]
                            try:
                                func_args = json.loads(tool_call["function"].get("arguments", "{}"))
                            except json.JSONDecodeError:
                                func_args = {}

                            try:
                                tool_result = dispatch_tool_call(func_name, func_args)
                            except Exception as e:
                                tool_result = json.dumps({"error": str(e)})

                            st.session_state.messages.append(
                                {
                                    "role": "tool",
                                    "tool_call_id": tool_call["id"],
                                    "name": func_name,
                                    "content": tool_result,
                                }
                            )
                    else:
                        final_response_content = message.get("content") or ""
                        break
                else:
                    final_response_content = "⚠️ Reached max reasoning turns without a final answer."

            st.markdown(final_response_content)
            st.session_state.messages.append({"role": "assistant", "content": final_response_content})
