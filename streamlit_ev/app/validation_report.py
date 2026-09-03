import streamlit as st
import pandas as pd
import polars as pl
import altair as alt
import calendar
import os
from google.cloud import bigquery
from datetime import datetime, timedelta
from dotenv import load_dotenv
from helpers.gcp import get_bq_client

# Load .env file - override=True ensures .env values take precedence over OS env vars
load_dotenv(override=True)

# BigQuery table configuration from environment variables
# Defaults match Terraform resource definitions in terraform_ev/bigquery.tf
BQ_PROJECT = os.environ.get("GCP_PROJECT")
BQ_DATASET = os.environ.get("BQ_DATASET", "event_data_dataset")
BQ_TABLE = os.environ.get("BQ_TABLE", "event_data_table")

@st.cache_data(ttl=300, show_spinner=False)
def fetch_data(start_date, end_date) -> pl.DataFrame:
    client = get_bq_client()
    if not client:
        return pl.DataFrame()

    if not BQ_PROJECT:
        st.error("GCP_PROJECT environment variable is not set")
        return pl.DataFrame()

    table_ref = f"`{BQ_PROJECT}.{BQ_DATASET}.{BQ_TABLE}`"

    query = f"""
        SELECT
            event_id,
            event_name,
            field,
            error_type,
            expected,
            actual,
            timestamp,
            status
        FROM {table_ref}
        WHERE date_utc BETWEEN @start_date AND @end_date
    """
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("start_date", "DATE", start_date),
            bigquery.ScalarQueryParameter("end_date", "DATE", end_date),
        ]
    )
    
    try:
        # Fetch data as Arrow table and convert to Polars DataFrame
        arrow_table = client.query(query, job_config=job_config).to_arrow()
        df = pl.from_arrow(arrow_table)
        if isinstance(df, pl.Series):
             return df.to_frame()
        return df
    except Exception as e:
        st.error(f"Error fetching data from BigQuery: {e}")
        return pl.DataFrame()

def compute_parameter_performance(df: pl.DataFrame) -> pl.DataFrame:
    """Aggregate per-field (parameter) stats: fill/error rate, top error type, daily trend."""
    if df.is_empty():
        return pl.DataFrame()

    df = df.filter(pl.col("field").is_not_null())
    if df.is_empty():
        return pl.DataFrame()

    # Overall seen/errors per parameter
    summary = (
        df.group_by("field")
        .agg([
            pl.len().alias("seen"),
            (pl.col("status") == "error").sum().alias("errors"),
        ])
        .with_columns((pl.col("errors") / pl.col("seen") * 100).alias("error_rate"))
    )

    # Most frequent error_type per parameter (the dominant failure mode)
    top_issue = (
        df.filter(pl.col("status") == "error")
        .group_by(["field", "error_type"])
        .agg(pl.len().alias("n"))
        .sort("n", descending=True)
        .group_by("field", maintain_order=True)
        .first()
        .select(["field", pl.col("error_type").alias("top_issue")])
    )

    # Daily error rate series per parameter, for sparkline trend
    daily = (
        df
        .with_columns(pl.col("timestamp").dt.truncate("1d").alias("date"))
        .group_by(["field", "date"])
        .agg([
            pl.len().alias("day_seen"),
            (pl.col("status") == "error").sum().alias("day_errors"),
        ])
        .with_columns((pl.col("day_errors") / pl.col("day_seen") * 100).alias("day_error_rate"))
        .sort("date")
        .group_by("field", maintain_order=True)
        .agg(pl.col("day_error_rate").alias("trend"))
    )

    return (
        summary
        .join(top_issue, on="field", how="left")
        .join(daily, on="field", how="left")
        .with_columns(pl.col("top_issue").fill_null("—"))
        .sort("error_rate", descending=True)
    )


def render_parameter_performance(df: pl.DataFrame):
    perf = compute_parameter_performance(df)

    if perf.is_empty():
        st.info("No parameter-level data found for the selected period.")
        return

    total_checks = int(perf["seen"].sum())
    total_errors = int(perf["errors"].sum())
    overall_error_rate = (total_errors / total_checks * 100) if total_checks else 0
    worst = perf.row(0, named=True)  # already sorted by error_rate desc

    col1, col2, col3 = st.columns(3)
    col1.metric("Parameters Tracked", perf.height)
    col2.metric("Overall Error Rate", f"{overall_error_rate:.1f}%")
    col3.metric("Worst Performer", worst["field"], f"{worst['error_rate']:.1f}% errors")

    st.dataframe(
        perf.to_pandas(),
        column_config={
            "field": st.column_config.TextColumn("Parameter"),
            "seen": st.column_config.NumberColumn("Seen", help="Total validation checks for this parameter"),
            "errors": st.column_config.NumberColumn("Errors"),
            "error_rate": st.column_config.ProgressColumn(
                "Error Rate", format="%.1f%%", min_value=0, max_value=100
            ),
            "top_issue": st.column_config.TextColumn("Top Issue", help="Most frequent error_type for this parameter"),
            "trend": st.column_config.LineChartColumn(
                "Trend (daily error %)", y_min=0, y_max=100
            ),
        },
        column_order=["field", "seen", "errors", "error_rate", "top_issue", "trend"],
        hide_index=True,
        use_container_width=True,
    )


def subtract_months(d, months: int):
    """Calendar-aware month subtraction, clamping the day to the target month's length."""
    month_index = d.month - 1 - months
    year = d.year + month_index // 12
    month = month_index % 12 + 1
    day = min(d.day, calendar.monthrange(year, month)[1])
    return d.replace(year=year, month=month, day=day)


def compute_anchor_range(anchor: str, unit: str, n: int, today):
    """Return (start_date, end_date) for an Anchor (This/Last/Last …) x Unit (Day/Week/Month/Year) pair."""
    if anchor == "This":
        if unit == "Day":
            return today, today
        if unit == "Week":
            return today - timedelta(days=today.weekday()), today
        if unit == "Month":
            return today.replace(day=1), today
        if unit == "Year":
            return today.replace(month=1, day=1), today

    if anchor == "Last":
        if unit == "Day":
            yesterday = today - timedelta(days=1)
            return yesterday, yesterday
        if unit == "Week":
            start_of_this_week = today - timedelta(days=today.weekday())
            start = start_of_this_week - timedelta(days=7)
            end = start_of_this_week - timedelta(days=1)
            return start, end
        if unit == "Month":
            first_of_this_month = today.replace(day=1)
            last_month_end = first_of_this_month - timedelta(days=1)
            return last_month_end.replace(day=1), last_month_end
        if unit == "Year":
            return (
                today.replace(year=today.year - 1, month=1, day=1),
                today.replace(year=today.year - 1, month=12, day=31),
            )

    if anchor == "Last …":
        if unit == "Day":
            return today - timedelta(days=n - 1), today
        if unit == "Week":
            return today - timedelta(days=n * 7 - 1), today
        if unit == "Month":
            return subtract_months(today, n) + timedelta(days=1), today
        if unit == "Year":
            return subtract_months(today, n * 12) + timedelta(days=1), today

    # Fallback (shouldn't be hit)
    return today - timedelta(days=6), today


def render_validation_report():
    st.title("Validation Report")

    # Date Range Selector
    with st.sidebar:
        st.header("Filters")
        today = datetime.now().date()

        custom_range = st.checkbox("Custom range")

        if custom_range:
            default_start = today - timedelta(days=7)
            default_end = today
            date_range = st.date_input(
                "Select Date Range",
                value=[default_start, default_end],
                max_value=today,
            )
        else:
            col_anchor, col_unit = st.columns(2)
            with col_anchor:
                anchor = st.selectbox("Range", ["This", "Last", "Last …"], index=2)
            with col_unit:
                unit = st.selectbox("Unit", ["Day", "Week", "Month", "Year"], index=0)

            n = 7
            if anchor == "Last …":
                n = st.number_input(
                    f"Number of {unit.lower()}s",
                    min_value=1,
                    value=7 if unit == "Day" else 1,
                    step=1,
                )

            start_date, end_date = compute_anchor_range(anchor, unit, int(n), today)
            date_range = (start_date, end_date)
            st.caption(f"{start_date.strftime('%b %d, %Y')} – {end_date.strftime('%b %d, %Y')}")

    if isinstance(date_range, (list, tuple)) and len(date_range) == 2:
        start_date, end_date = date_range
    else:
        st.info("Please select a complete date range (start and end date).")
        return

    # Fetch Data
    with st.spinner("Fetching data..."):
        df = fetch_data(start_date, end_date)

    if not df.is_empty():
        # Get unique event names for filter
        unique_events = sorted(df.select("event_name").unique().to_series().to_list())

        # Event Name Filter in sidebar
        with st.sidebar:
            selected_events = st.multiselect(
                "Filter by Event Name",
                options=unique_events,
                default=unique_events,
                help="Select one or more event names to filter the data"
            )

        # Apply event name filter
        if selected_events:
            df = df.filter(pl.col("event_name").is_in(selected_events))
        else:
            st.warning("Please select at least one event name to display data.")
            return

        overview_tab, params_tab = st.tabs(["Overview", "Parameter Performance"])

        with params_tab:
            render_parameter_performance(df)

        # Filter for errors
        error_df = df.filter(pl.col("status") == "error")

        with overview_tab:
            if not error_df.is_empty():
                st.subheader("Event Failures Overview")

                # Aggregate failure data for bar chart
                chart_data = (
                    error_df
                    .with_columns(pl.col("timestamp").dt.truncate("1d").alias("date"))
                    .group_by(["date", "event_name"])
                    .agg(pl.len().alias("count"))
                    .sort("date")
                )

                # Calculate error rate per day (% of distinct event_ids with error status)
                error_rate_data = (
                    df
                    .with_columns(pl.col("timestamp").dt.truncate("1d").alias("date"))
                    .group_by("date")
                    .agg([
                        pl.col("event_id").n_unique().alias("total_events"),
                        pl.col("event_id").filter(pl.col("status") == "error").n_unique().alias("error_events")
                    ])
                    .with_columns(
                        (pl.col("error_events") / pl.col("total_events") * 100).alias("error_rate")
                    )
                    .sort("date")
                )

                # Convert to pandas for Altair
                chart_pd = chart_data.to_pandas()
                error_rate_pd = error_rate_data.to_pandas()

                # Convert date to string for ordinal scale (no gaps)
                chart_pd['date_str'] = chart_pd['date'].dt.strftime('%b %d')
                error_rate_pd['date_str'] = error_rate_pd['date'].dt.strftime('%b %d')

                # Get sorted unique dates for proper ordering
                date_order = chart_pd.sort_values('date')['date_str'].unique().tolist()

                # Stacked Bar Chart for failure counts
                bars = alt.Chart(chart_pd).mark_bar().encode(
                    x=alt.X(
                        'date_str:O',
                        axis=alt.Axis(title='Date', labelAngle=-45),
                        sort=date_order
                    ),
                    y=alt.Y('count:Q', axis=alt.Axis(title='Count of Failures')),
                    color=alt.Color('event_name:N', legend=alt.Legend(title="Event Name")),
                    tooltip=[
                        alt.Tooltip('date_str:O', title='Date'),
                        alt.Tooltip('event_name:N', title='Event Name'),
                        alt.Tooltip('count:Q', title='Failures')
                    ]
                )

                # Line chart for error rate
                # Fixed, theme-independent color (not white/black) so the line stays
                # visible whether the Streamlit theme is light or dark.
                line = alt.Chart(error_rate_pd).mark_line(
                    color='#D62728',
                    strokeWidth=2,
                    point=alt.OverlayMarkDef(color='#D62728', size=50)
                ).encode(
                    x=alt.X('date_str:O', sort=date_order),
                    y=alt.Y(
                        'error_rate:Q',
                        axis=alt.Axis(title='Error Rate (%)', orient='right'),
                        scale=alt.Scale(domain=[0, 100])
                    ),
                    tooltip=[
                        alt.Tooltip('date_str:O', title='Date'),
                        alt.Tooltip('error_rate:Q', title='Error Rate (%)', format='.1f'),
                        alt.Tooltip('error_events:Q', title='Failed Events'),
                        alt.Tooltip('total_events:Q', title='Total Events')
                    ]
                )

                # Combine charts with independent Y-axes
                chart = alt.layer(bars, line).resolve_scale(
                    y='independent'
                ).properties(
                    height=500
                ).interactive()

                st.altair_chart(chart, use_container_width=True)

                # Raw Data Table
                st.subheader("Raw Failure Logs")
                st.dataframe(
                    error_df.to_pandas(),
                    column_config={
                        "timestamp": st.column_config.DatetimeColumn("Timestamp", format="D MMM YYYY, h:mm a"),
                    },
                    use_container_width=True
                )
            else:
                st.info("No failure data found for the selected period.")
    else:
        st.info("No data found for the selected period.")
