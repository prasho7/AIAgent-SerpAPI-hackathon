"""Minimal custom styling for the ScoutAI interface."""

from __future__ import annotations

import streamlit as st


def apply_custom_styles() -> None:
    """Apply modern, dark, high-contrast editorial styling with subtle glassmorphism."""
    st.markdown(
        """
        <style>
        /* Base typography, background & layout */
        .stApp {
            background-color: #0b0e14 !important;
            background-image: 
                radial-gradient(circle at 12% 0%, rgba(255, 75, 75, 0.05), transparent 36%),
                radial-gradient(circle at 88% 5%, rgba(61, 220, 151, 0.035), transparent 32%) !important;
            background-attachment: fixed !important;
            color: #f3f5f7 !important;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
        }

        /* Transparent Header Bar so content is never covered */
        header[data-testid="stHeader"] {
            background: transparent !important;
        }

        /* Safe Top Padding to ensure content starts cleanly below header */
        [data-testid="stAppViewContainer"] .main .block-container,
        .block-container {
            padding-top: 3.75rem !important;
            padding-bottom: 3.5rem !important;
            max-width: 1350px !important;
        }

        /* Sidebar styling with glassmorphism */
        section[data-testid="stSidebar"] {
            background-color: rgba(15, 19, 28, 0.95) !important;
            backdrop-filter: blur(16px) !important;
            border-right: 1px solid rgba(37, 43, 58, 0.9) !important;
        }

        /* ScoutAI Header */
        .scout-header-row {
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: 0.35rem;
        }
        .scout-brand {
            display: inline-flex;
            align-items: center;
            gap: 0.55rem;
        }
        .scout-mark {
            display: inline-block;
            width: 13px;
            height: 13px;
            background-color: #ff4b4b;
            border-radius: 3px;
        }
        .scout-name {
            font-size: 1.15rem;
            font-weight: 700;
            letter-spacing: 0.06em;
            color: #f3f5f7;
            text-transform: uppercase;
        }
        .scout-subheading {
            font-size: 1.65rem;
            font-weight: 700;
            color: #f3f5f7;
            margin: 0.2rem 0 0.15rem 0;
            line-height: 1.25;
        }
        .scout-tagline {
            font-size: 0.9rem;
            color: #8b93a7;
            margin-bottom: 1.35rem;
        }

        /* Starter Examples Section */
        .scout-starter-section {
            margin-top: 1.75rem;
            margin-bottom: 0.85rem;
        }
        .scout-starter-title {
            font-size: 1.05rem;
            font-weight: 600;
            color: #f3f5f7;
            margin-bottom: 0.2rem;
        }
        .scout-starter-desc {
            font-size: 0.85rem;
            color: #8b93a7;
            margin-bottom: 0.75rem;
        }

        /* Metadata summary line */
        .scout-meta-line {
            display: flex;
            align-items: center;
            flex-wrap: wrap;
            gap: 0.45rem;
            font-size: 0.82rem;
            color: #8b93a7;
            margin-bottom: 1.15rem;
            padding: 0.5rem 0.75rem;
            background: rgba(22, 27, 39, 0.5);
            backdrop-filter: blur(8px);
            border: 1px solid rgba(37, 43, 58, 0.7);
            border-radius: 8px;
        }
        .scout-meta-highlight {
            color: #3ddc97;
            font-weight: 600;
        }

        /* Glassy Source Card */
        .scout-source-item {
            background: rgba(22, 27, 39, 0.75);
            backdrop-filter: blur(12px);
            border: 1px solid rgba(37, 43, 58, 0.85);
            border-radius: 10px;
            padding: 0.85rem;
            margin-bottom: 0.65rem;
            transition: border-color 0.15s ease, transform 0.15s ease;
        }
        .scout-source-item:hover {
            border-color: rgba(62, 72, 94, 0.9);
        }
        .scout-source-top {
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: 0.35rem;
        }
        .scout-source-badge {
            font-size: 0.7rem;
            font-weight: 700;
            background: #252b3a;
            color: #f3f5f7;
            padding: 0.12rem 0.4rem;
            border-radius: 4px;
        }
        .scout-source-domain {
            font-size: 0.75rem;
            color: #8b93a7;
        }
        .scout-source-title {
            font-size: 0.85rem;
            font-weight: 600;
            color: #f3f5f7;
            line-height: 1.35;
            margin-bottom: 0.3rem;
        }
        .scout-source-snippet {
            font-size: 0.78rem;
            color: #8b93a7;
            line-height: 1.4;
            margin-bottom: 0.45rem;
            display: -webkit-box;
            -webkit-line-clamp: 2;
            -webkit-box-orient: vertical;
            overflow: hidden;
        }
        .scout-source-footer {
            display: flex;
            align-items: center;
            justify-content: space-between;
            font-size: 0.72rem;
            color: #64748b;
        }
        .scout-source-link {
            color: #ff4b4b !important;
            font-weight: 600;
            text-decoration: none;
        }
        .scout-source-link:hover {
            text-decoration: underline;
        }

        /* Glassy Sidebar metric cards */
        .scout-metric-card {
            background: rgba(22, 27, 39, 0.75);
            backdrop-filter: blur(10px);
            border: 1px solid rgba(37, 43, 58, 0.8);
            border-radius: 8px;
            padding: 0.6rem 0.75rem;
            margin-bottom: 0.5rem;
        }
        .scout-metric-label {
            font-size: 0.72rem;
            color: #8b93a7;
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }
        .scout-metric-val {
            font-size: 1.05rem;
            font-weight: 700;
            color: #f3f5f7;
            margin-top: 0.1rem;
        }

        /* Primary button red accent */
        div[data-testid="stButton"] button[kind="primary"] {
            background-color: #ff4b4b !important;
            border-color: #ff4b4b !important;
            color: #ffffff !important;
            font-weight: 600 !important;
            border-radius: 8px !important;
        }
        div[data-testid="stButton"] button[kind="primary"]:hover {
            background-color: #e03838 !important;
            border-color: #e03838 !important;
        }

        /* Secondary buttons & popover buttons */
        div[data-testid="stButton"] button[kind="secondary"],
        div[data-testid="stPopover"] button {
            border-radius: 8px !important;
            border: 1px solid rgba(37, 43, 58, 0.85) !important;
            background-color: rgba(22, 27, 39, 0.75) !important;
            backdrop-filter: blur(8px) !important;
            color: #f3f5f7 !important;
        }
        div[data-testid="stButton"] button[kind="secondary"]:hover,
        div[data-testid="stPopover"] button:hover {
            border-color: rgba(62, 72, 94, 0.9) !important;
            color: #ffffff !important;
        }

        /* Input styling with glassmorphic depth */
        div[data-testid="stTextInput"] input {
            background-color: rgba(22, 27, 39, 0.8) !important;
            backdrop-filter: blur(8px) !important;
            border: 1px solid rgba(37, 43, 58, 0.85) !important;
            color: #f3f5f7 !important;
            border-radius: 8px !important;
            font-size: 0.92rem !important;
        }
        div[data-testid="stTextInput"] input:focus {
            border-color: #ff4b4b !important;
            box-shadow: 0 0 0 1px #ff4b4b !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
