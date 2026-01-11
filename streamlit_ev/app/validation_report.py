import streamlit as st
import pandas as pd
import polars as pl
import altair as alt
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

def fetch_data(start_date, end_date):
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
        return pl.from_arrow(arrow_table)
    except Exception as e:
        st.error(f"Error fetching data from BigQuery: {e}")
        return pl.DataFrame()

def render_validation_report():
    st.title("Validation Report")

    # Date Range Selector
    with st.sidebar:
        st.header("Filters")
        default_start = datetime.now().date() - timedelta(days=7)
        default_end = datetime.now().date()
        date_range = st.date_input(
            "Select Date Range",
            value=[default_start, default_end],
            max_value=datetime.now().date()
        )

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

        # Filter for errors
        error_df = df.filter(pl.col("status") == "error")

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
            line = alt.Chart(error_rate_pd).mark_line(
                color='white',
                strokeWidth=2,
                point=alt.OverlayMarkDef(color='white', size=50)
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
