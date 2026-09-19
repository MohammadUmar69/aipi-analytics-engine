# aipi-analytics-engine
Enterprise-grade AIPI Engine and analytics command center featuring granular RLS/OLS security personas, autonomous Groq LLM agent guardrails, and live-streaming POS telemetry. Built with Streamlit and Plotly for high-performance interactive data visualization, secure multi-tenant role isolation, and bulletproof audit compliance.

# Enterprise AIPI Analytics Engine

An enterprise-grade analytics command center featuring granular RLS/OLS security personas, autonomous Groq LLM agent guardrails, and live-streaming POS telemetry. Built with Streamlit and Plotly for high-performance interactive data visualization.

## Features
- **Security (RLS/OLS):** Multi-tenant role isolation and session-state permissioning.
- **AI Guardrails:** Autonomous Groq LLM-powered analytics and anomaly detection.
- **Real-Time Telemetry:** Live POS telemetry tracking with robust store ID filtering.

## Tech Stack
- **Frontend & Dashboard:** Streamlit, Plotly
- **AI Engine:** Groq LLM API
- **Data Processing:** Pandas, Azure EventHub integrations

## Deployment
Deployed on Streamlit Community Cloud with secure runtime secret management via `.streamlit/secrets.toml`.