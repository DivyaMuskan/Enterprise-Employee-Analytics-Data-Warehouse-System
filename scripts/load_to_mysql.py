"""
Enterprise Employee Analytics - Cloud MySQL (TiDB Cloud) Loader
==============================================================
Populates the Cloud MySQL / TiDB databases with the full synthesized
enterprise dataset: 100K employees, SCD2 history, projects, reviews,
and Kimball Star Schema facts.
"""

import os
import sys
import time
import datetime
import pandas as pd
import pymysql
from pymysql.cursors import DictCursor
from dotenv import load_dotenv

# Load credentials from .env
load_dotenv()

def get_db_credentials():
    # Read from .env, streamlit secrets, or defaults
    host = os.getenv("MYSQL_HOST", "gateway01.ap-northeast-1.prod.aws.tidbcloud.com")
    port = int(os.getenv("MYSQL_PORT", 4000))
    user = os.getenv("MYSQL_USER", "PDqUFNPHHRdVeo7.root")
    password = os.getenv("MYSQL_PASSWORD", "qO0oJPLPGTT0NNsP")
    oltp_db = os.getenv("MYSQL_OLTP_DB", "enterprise_hr_oltp")
    olap_db = os.getenv("MYSQL_OLAP_DB", "enterprise_hr_dw")

    # Check streamlit secrets if available
    try:
        import streamlit as st
        if hasattr(st, "secrets") and "mysql" in st.secrets:
            sec = st.secrets["mysql"]
            host = sec.get("host", host)
            port = int(sec.get("port", port))
            user = sec.get("user", user)
            password = sec.get("password", password)
            oltp_db = sec.get("oltp_database", oltp_db)
            olap_db = sec.get("olap_database", olap_db)
    except Exception:
        pass

    return {
        "host": host,
        "port": port,
        "user": user,
        "password": password,
        "oltp_db": oltp_db,
        "olap_db": olap_db
    }

def connect_mysql(creds, database=None):
    kwargs = {
        "host": creds["host"],
        "port": creds["port"],
        "user": creds["user"],
        "password": creds["password"],
        "cursorclass": DictCursor,
        "autocommit": True,
        "connect_timeout": 15
    }
    if database:
        kwargs["database"] = database
    if creds["host"] not in ("127.0.0.1", "localhost") or creds["port"] == 4000:
        kwargs["ssl_verify_cert"] = True
        kwargs["ssl_verify_identity"] = True
    return pymysql.connect(**kwargs)

def execute_sql_file(conn, file_path, target_db):
    print(f"[SQL] Executing DDL script: {file_path} against {target_db}...")
    with open(file_path, "r", encoding="utf-8") as f:
        sql = f.read()

    with conn.cursor() as cur:
        cur.execute(f"USE `{target_db}`;")
        statements = [stmt.strip() for stmt in sql.split(";") if stmt.strip()]
        for stmt in statements:
            # Skip database creation/drop statements inside script
            upper = stmt.upper()
            if upper.startswith("CREATE DATABASE") or upper.startswith("USE "):
                continue
            try:
                cur.execute(stmt)
            except Exception as e:
                # ignore DROP IF EXISTS errors
                if "DROP TABLE" not in upper:
                    print(f"  [Warning] Statement notice: {e}")

def populate_dim_date(conn, olap_db, start_year=2018, end_year=2030):
    print(f"[Dim_Date] Populating calendar dimension ({start_year} - {end_year})...")
    start_date = datetime.date(start_year, 1, 1)
    end_date = datetime.date(end_year, 12, 31)
    delta = datetime.timedelta(days=1)

    records = []
    curr = start_date
    while curr <= end_date:
        records.append((
            int(curr.strftime("%Y%m%d")),
            curr.strftime("%Y-%m-%d"),
            curr.year,
            (curr.month - 1) // 3 + 1,
            curr.month,
            curr.strftime("%B"),
            curr.day,
            curr.strftime("%A"),
            1 if curr.weekday() in (5, 6) else 0,
            f"FY{curr.year}"
        ))
        curr += delta

    with conn.cursor() as cur:
        cur.execute(f"USE `{olap_db}`;")
        sql = """
            INSERT IGNORE INTO Dim_Date (
                date_dim_id, full_date, year, quarter, month, month_name,
                day_of_month, day_name, is_weekend, fiscal_year
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        cur.executemany(sql, records)
    print(f"[Dim_Date] Loaded {len(records):,} calendar records.")

def clean_records(records):
    """Replaces any float NaN values with python None for clean MySQL NULL insertion."""
    clean = []
    for row in records:
        clean.append([
            None if (isinstance(v, float) and pd.isna(v)) else v
            for v in row
        ])
    return clean

def load_data(creds):
    data_dir = os.path.join("data", "synthesized")
    if not os.path.exists(os.path.join(data_dir, "employees_scd2_full.csv")):
        print(f"[ERROR] Synthesized CSVs not found in {data_dir}. Run 'python scripts/data_synthesizer.py' first.")
        return

    print("=" * 70)
    print(" Enterprise Employee Analytics - TiDB Cloud Data Ingestion")
    print(f" Target Host: {creds['host']}:{creds['port']}")
    print("=" * 70)

    # 1. Connect and Ensure Databases
    print("\n[Step 1/5] Ensuring Cloud Databases exist...")
    conn = connect_mysql(creds)
    with conn.cursor() as cur:
        cur.execute(f"CREATE DATABASE IF NOT EXISTS `{creds['oltp_db']}`;")
        cur.execute(f"CREATE DATABASE IF NOT EXISTS `{creds['olap_db']}`;")
    print("  -> Databases enterprise_hr_oltp & enterprise_hr_dw ready.")

    # 2. Run DDL Schemas
    print("\n[Step 2/5] Creating 3NF OLTP and Kimball Star Schemas...")
    execute_sql_file(conn, os.path.join("sql", "ddl", "01_oltp_schema.sql"), creds['oltp_db'])
    execute_sql_file(conn, os.path.join("sql", "ddl", "02_olap_star_schema.sql"), creds['olap_db'])

    # 3. Populate Dim_Date
    populate_dim_date(conn, creds['olap_db'])

    # 4. Ingest Reference Dimensions
    print("\n[Step 3/5] Loading Departments and Projects...")
    df_dept = pd.read_csv(os.path.join(data_dir, "departments.csv"))
    with conn.cursor() as cur:
        cur.execute(f"USE `{creds['oltp_db']}`;")
        cur.executemany(
            "INSERT INTO departments (department_id, department_name, cost_center, budget) VALUES (%s, %s, %s, %s)",
            df_dept[["department_id", "department_name", "cost_center", "budget"]].values.tolist()
        )
        cur.execute(f"USE `{creds['olap_db']}`;")
        cur.executemany(
            "INSERT INTO Dim_Department (department_id, department_name, cost_center, budget) VALUES (%s, %s, %s, %s)",
            df_dept[["department_id", "department_name", "cost_center", "budget"]].values.tolist()
        )
    print(f"  -> Ingested {len(df_dept)} departments.")

    df_proj = pd.read_csv(os.path.join(data_dir, "projects.csv"))
    if "budget_tier" not in df_proj.columns:
        df_proj["budget_tier"] = df_proj["budget"].apply(
            lambda b: "Small (<$500k)" if b < 500000 else ("Medium ($500k-$1.5M)" if b <= 1500000 else "Large (> $1.5M)")
        )

    with conn.cursor() as cur:
        cur.execute(f"USE `{creds['oltp_db']}`;")
        cur.executemany(
            """INSERT INTO projects (project_id, project_code, project_name, department_id, start_date, end_date, budget, status)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
            df_proj[["project_id", "project_code", "project_name", "department_id", "start_date", "end_date", "budget", "status"]].values.tolist()
        )
        cur.execute(f"USE `{creds['olap_db']}`;")
        cur.executemany(
            """INSERT INTO Dim_Project (project_id, project_code, project_name, budget_tier, status)
               VALUES (%s, %s, %s, %s, %s)""",
            df_proj[["project_id", "project_code", "project_name", "budget_tier", "status"]].values.tolist()
        )
    print(f"  -> Ingested {len(df_proj)} projects.")

    # 5. Ingest Employees (OLTP & SCD2)
    print("\n[Step 4/5] Loading Employees (OLTP active & SCD Type 2 dimension)...")
    df_emp_oltp = pd.read_csv(os.path.join(data_dir, "employees_oltp_current.csv"))
    oltp_cols = [
        "employee_id", "first_name", "last_name", "email", "phone", "gender", "age",
        "marital_status", "hire_date", "department_id", "job_role", "education_field",
        "monthly_income", "overtime", "years_at_company", "attrition", "status"
    ]
    oltp_records = clean_records(df_emp_oltp[oltp_cols].values.tolist())

    with conn.cursor() as cur:
        cur.execute(f"USE `{creds['oltp_db']}`;")
        insert_emp_sql = f"""
            INSERT IGNORE INTO employees ({', '.join(oltp_cols)})
            VALUES ({', '.join(['%s'] * len(oltp_cols))})
        """
        chunk_size = 5000
        for i in range(0, len(oltp_records), chunk_size):
            cur.executemany(insert_emp_sql, oltp_records[i:i + chunk_size])
            print(f"  -> Inserted {min(i + chunk_size, len(oltp_records)):,} / {len(oltp_records):,} active employees...", end="\r")
        print()

    # Load Dim_Employee SCD2
    df_scd2 = pd.read_csv(os.path.join(data_dir, "employees_scd2_full.csv"))
    scd2_cols = [
        "employee_dim_id", "employee_id", "first_name", "last_name", "gender", "age",
        "hire_date", "department_id", "department_name", "job_role", "education_field",
        "monthly_income", "start_date", "end_date", "is_current", "version"
    ]
    scd2_records = clean_records(df_scd2[scd2_cols].values.tolist())

    with conn.cursor() as cur:
        cur.execute(f"USE `{creds['olap_db']}`;")
        insert_scd2_sql = f"""
            INSERT IGNORE INTO Dim_Employee ({', '.join(scd2_cols)})
            VALUES ({', '.join(['%s'] * len(scd2_cols))})
        """
        for i in range(0, len(scd2_records), chunk_size):
            cur.executemany(insert_scd2_sql, scd2_records[i:i + chunk_size])
            print(f"  -> Inserted {min(i + chunk_size, len(scd2_records)):,} / {len(scd2_records):,} SCD2 records into Dim_Employee...", end="\r")
        print()

    # 6. Ingest Assignments and Reviews
    print("\n[Step 5/5] Loading Project Assignments and Performance Reviews...")
    df_assign = pd.read_csv(os.path.join(data_dir, "project_assignments.csv"))
    assign_records = clean_records(df_assign[["employee_id", "project_id", "assignment_role", "allocation_percentage", "assigned_date"]].values.tolist())
    with conn.cursor() as cur:
        cur.execute(f"USE `{creds['oltp_db']}`;")
        cur.executemany(
            """INSERT IGNORE INTO employee_project_assignments 
               (employee_id, project_id, assignment_role, allocation_percentage, assigned_date)
               VALUES (%s, %s, %s, %s, %s)""",
            assign_records
        )
    print(f"  -> Ingested {len(assign_records):,} project assignments.")

    df_rev = pd.read_csv(os.path.join(data_dir, "performance_reviews.csv"))
    rev_cols = [
        "review_id", "employee_id", "department_id", "review_date", "review_year",
        "performance_rating", "monthly_income_at_review", "percent_salary_hike",
        "work_life_balance", "job_satisfaction", "environment_satisfaction",
        "promotion_given", "attrition_risk_score", "tenure_at_review"
    ]
    rev_records = clean_records(df_rev[rev_cols].values.tolist())
    with conn.cursor() as cur:
        cur.execute(f"USE `{creds['oltp_db']}`;")
        insert_rev_sql = f"""
            INSERT IGNORE INTO performance_reviews ({', '.join(rev_cols)})
            VALUES ({', '.join(['%s'] * len(rev_cols))})
        """
        for i in range(0, len(rev_records), chunk_size):
            cur.executemany(insert_rev_sql, rev_records[i:i + chunk_size])
            print(f"  -> Inserted {min(i + chunk_size, len(rev_records)):,} / {len(rev_records):,} performance reviews...", end="\r")
        print()

    # Ingest Fact_PerformanceReviews (Resolved joins)
    print("\n[Final] Resolving dimensional surrogate keys into Fact_PerformanceReviews...")
    with conn.cursor() as cur:
        cur.execute(f"USE `{creds['olap_db']}`;")
        cur.execute(f"""
            INSERT INTO `{creds['olap_db']}`.Fact_PerformanceReviews (
                employee_dim_id, department_dim_id, project_dim_id, date_dim_id,
                review_id, employee_id, performance_rating, monthly_income_at_review,
                percent_salary_hike, work_life_balance, job_satisfaction,
                environment_satisfaction, attrition_risk_score, tenure_at_review, promotion_given
            )
            SELECT 
                de.employee_dim_id,
                dd.department_dim_id,
                0 AS project_dim_id,
                CAST(DATE_FORMAT(r.review_date, '%Y%m%d') AS UNSIGNED) AS date_dim_id,
                r.review_id,
                r.employee_id,
                r.performance_rating,
                r.monthly_income_at_review,
                r.percent_salary_hike,
                r.work_life_balance,
                r.job_satisfaction,
                r.environment_satisfaction,
                r.attrition_risk_score,
                r.tenure_at_review,
                r.promotion_given
            FROM `{creds['oltp_db']}`.performance_reviews r
            JOIN `{creds['olap_db']}`.Dim_Employee de 
                ON r.employee_id = de.employee_id
               AND r.review_date >= de.start_date
               AND (de.end_date IS NULL OR r.review_date < de.end_date)
            JOIN `{creds['olap_db']}`.Dim_Department dd 
                ON r.department_id = dd.department_id;
        """)
        cur.execute(f"SELECT COUNT(*) as cnt FROM `{creds['olap_db']}`.Fact_PerformanceReviews;")
        fact_count = cur.fetchone()["cnt"]

        # Also populate Bridge_EmployeeProject
        cur.execute(f"""
            INSERT IGNORE INTO `{creds['olap_db']}`.Bridge_EmployeeProject (
                employee_dim_id, project_dim_id, assignment_start_date, is_active
            )
            SELECT 
                de.employee_dim_id,
                dp.project_dim_id,
                ep.assigned_date AS assignment_start_date,
                1 AS is_active
            FROM `{creds['oltp_db']}`.employee_project_assignments ep
            JOIN `{creds['olap_db']}`.Dim_Employee de 
                ON ep.employee_id = de.employee_id AND de.is_current = 1
            JOIN `{creds['olap_db']}`.Dim_Project dp 
                ON ep.project_id = dp.project_id;
        """)

    conn.close()
    print("=" * 70)
    print(f" SUCCESS: Loaded {fact_count:,} facts into Fact_PerformanceReviews on TiDB Cloud!")
    print(" You can now refresh your Streamlit Community Cloud page!")
    print("=" * 70)

if __name__ == "__main__":
    creds = get_db_credentials()
    load_data(creds)
