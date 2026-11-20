"""
Enterprise Employee Analytics & Data Warehouse System
======================================================
Executive Landing Portal & Enterprise System Overview

Author: Enterprise Data Architecture Team
Design: Professional Enterprise UI
"""

import streamlit as st
import pandas as pd
from src.database.db_manager import get_db
from src.managers.analytics_manager import AnalyticsManager
from src.ui import apply_ui_theme, render_page_header, render_sidebar

# Streamlit Page Configuration
st.set_page_config(
    page_title="Enterprise Data Warehouse Portal",
    layout="wide",
    initial_sidebar_state="expanded"
)

apply_ui_theme()


def main():
    # Sidebar
    render_sidebar(
        "Command center",
        "Platform overview",
        "A single operating view across workforce, warehouse, and people intelligence.",
    )
    st.sidebar.markdown("**Operational Store (OLTP)**  \n3NF relational records")
    st.sidebar.markdown("**Data Warehouse (OLAP)**  \nStar schema analytics")
    st.sidebar.markdown("**Temporal Model**  \nSCD Type 2 history")
    st.sidebar.divider()

    db = get_db()
    backend_name = db.get_backend_name().upper()
    st.sidebar.markdown(f"""
    <div class="status-badge">
        <span class="status-dot"></span>Backend: {backend_name}
    </div>
    """, unsafe_allow_html=True)

    render_page_header(
        "Enterprise people intelligence",
        "Employee Analytics & Data Warehouse",
        "A unified operating layer for workforce decisions, historical career journeys, and executive reporting.",
    )
    st.markdown(
        '<div class="hero-strip"><div><strong>Good morning, leadership team</strong><br><span>Review workforce health, talent movement, and organizational capacity from one trusted source.</span></div><span class="audit-badge">Live warehouse view</span></div>',
        unsafe_allow_html=True,
    )

    # Initialize Analytics Manager
    analytics_mgr = AnalyticsManager(db)

    try:
        kpis = analytics_mgr.get_executive_kpis()
    except Exception as e:
        st.error(f"Error querying data warehouse: {e}")
        kpis = {
            "total_active_employees": 0,
            "avg_monthly_salary": 0.0,
            "avg_performance_rating": 0.0,
            "avg_attrition_risk": 0.0,
            "total_promotions": 0,
            "career_transitioned_employees": 0,
            "total_projects": 0
        }

    # Top KPI Metrics Row
    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        st.markdown(f"""
        <div class="kpi-container">
            <div class="kpi-num">{kpis['total_active_employees']:,}</div>
            <div class="kpi-title">Active Workforce</div>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown(f"""
        <div class="kpi-container">
            <div class="kpi-num">${kpis['avg_monthly_salary']:,.0f}</div>
            <div class="kpi-title">Avg Monthly Compensation</div>
        </div>
        """, unsafe_allow_html=True)

    with col3:
        st.markdown(f"""
        <div class="kpi-container">
            <div class="kpi-num">{kpis['avg_performance_rating']:.2f} <span style="font-size:0.9rem; color:#64748B;">/ 5.0</span></div>
            <div class="kpi-title">Avg Performance Score</div>
        </div>
        """, unsafe_allow_html=True)

    with col4:
        st.markdown(f"""
        <div class="kpi-container">
            <div class="kpi-num">{kpis['avg_attrition_risk']:.1f}%</div>
            <div class="kpi-title">Attrition Flight Risk</div>
        </div>
        """, unsafe_allow_html=True)

    with col5:
        st.markdown(f"""
        <div class="kpi-container">
            <div class="kpi-num">{kpis['career_transitioned_employees']:,}</div>
            <div class="kpi-title">SCD2 Historical Transitions</div>
        </div>
        """, unsafe_allow_html=True)

    st.write("")
    st.write("")

    # Portal Module Navigation Cards
    st.markdown('<div class="section-title">Explore the platform</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-desc">Move from daily workforce operations to board-ready intelligence without leaving the system.</div>', unsafe_allow_html=True)
    card_col1, card_col2 = st.columns(2)

    with card_col1:
        st.markdown("""
        <div class="portal-card">
            <h4>HR Operations Management (OLTP)</h4>
            <p>Transactional console for personnel records, project staffing, and career progression management:</p>
            <ul>
                <li><strong>Personnel Onboarding:</strong> Standardized data intake with corporate email and credential validation.</li>
                <li><strong>Role & Compensation Transitions:</strong> Adjust department, title, or compensation with real-time <strong>SCD Type 2</strong> versioning in the data warehouse.</li>
                <li><strong>Initiative Resource Allocation:</strong> Provision client and internal projects and allocate staffing capacity.</li>
                <li><strong>Performance Appraisals:</strong> Log annual appraisals and synchronize with fact tables.</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
        st.page_link("pages/1_HR_Operations.py", label="Access HR Operations Portal →")

    with card_col2:
        st.markdown("""
        <div class="portal-card">
            <h4>Executive Analytics & Business Intelligence (OLAP)</h4>
            <p>Dimensional analytics powered directly by the Star Schema and advanced SQL window functions:</p>
            <ul>
                <li><strong>Department Talent Rankings:</strong> Departmental performance tiers determined via SQL <code>DENSE_RANK()</code>.</li>
                <li><strong>Longitudinal YoY Trajectories:</strong> Multi-year evaluation of merit salary adjustments and ratings.</li>
                <li><strong>Flight Risk Diagnostics:</strong> Correlation models identifying compensation anomalies and turnover risk.</li>
                <li><strong>Career Mobility Audits:</strong> Full historical SCD Type 2 career transitions and salary progression.</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
        st.page_link("pages/2_Executive_Analytics.py", label="Access Executive Analytics Dashboard →")

    st.divider()

    # System Architecture Information
    st.markdown('<div class="section-title">Data architecture at a glance</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-desc">A governed flow from operational activity to decision-ready intelligence.</div>', unsafe_allow_html=True)
    arch1, arch2, arch3 = st.columns(3)
    with arch1:
        st.markdown(
            '<div class="portal-card"><div class="mini-label">01 · Capture</div><h4>Operational store</h4><p>HR records, projects, and appraisals are managed through the transactional OLTP layer.</p></div>',
            unsafe_allow_html=True,
        )
    with arch2:
        st.markdown(
            '<div class="portal-card"><div class="mini-label">02 · Preserve</div><h4>Historical warehouse</h4><p>ETL and SCD Type 2 versioning preserve every career and compensation transition.</p></div>',
            unsafe_allow_html=True,
        )
    with arch3:
        st.markdown(
            '<div class="portal-card"><div class="mini-label">03 · Decide</div><h4>Executive intelligence</h4><p>Star-schema analytics translate trusted history into workforce and capacity signals.</p></div>',
            unsafe_allow_html=True,
        )

    with st.expander("System Architecture & Data Warehousing Specifications", expanded=False):
        st.markdown("""
        #### Architecture Overview
        - **OLTP Operational Store (3NF):** High-integrity relational schema handling transaction processing across `employees`, `departments`, `projects`, and `employee_project_assignments`.
        - **OLAP Dimensional Warehouse (Star Schema):** Modeled around `Fact_PerformanceReviews` with integer surrogate keys referencing conformed dimensions (`Dim_Department`, `Dim_Project`, `Dim_Date`) and the temporal Slowly Changing Dimension (`Dim_Employee`).
        - **SCD Type 2 Execution:**
          - Department transfers, title changes, or compensation modifications trigger the expiration of the current active dimension record (`end_date = CURRENT_DATE, is_current = 0`).
          - A successor record is appended (`start_date = CURRENT_DATE, end_date = NULL, is_current = 1, version = n + 1`).
          - Past appraisals remain tied to their respective historical versions without retroactive disruption.
        """)


if __name__ == "__main__":
    main()
