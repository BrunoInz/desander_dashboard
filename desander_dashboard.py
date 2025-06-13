import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
from datetime import datetime, timedelta
import os
import glob
from io import StringIO
import warnings

warnings.filterwarnings("ignore")

# Page configuration
st.set_page_config(
    page_title="Desander Data Analysis Tool", page_icon="🛢️", layout="wide", initial_sidebar_state="expanded"
)

# Initialize session state
if "df" not in st.session_state:
    st.session_state.df = None
if "data_loaded" not in st.session_state:
    st.session_state.data_loaded = False
if "data_source" not in st.session_state:
    st.session_state.data_source = "Use Sample Data"

# Custom CSS for better styling and dark mode support
st.markdown(
    """
<style>
    .main > div {
        padding-top: 2rem;
    }
    .stMetric {
        background-color: var(--background-color);
        border: 1px solid var(--border-color);
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 0.5rem 0;
    }
    .metric-container {
        display: flex;
        justify-content: space-around;
        margin: 1rem 0;
    }
    
    /* Dark mode support */
    @media (prefers-color-scheme: dark) {
        .stMetric {
            background-color: rgba(255, 255, 255, 0.05);
            border: 1px solid rgba(255, 255, 255, 0.2);
        }
    }
    
    /* Light mode support */
    @media (prefers-color-scheme: light) {
        .stMetric {
            background-color: #f0f2f6;
            border: 1px solid #e1e5e9;
        }
    }
    
    /* Ensure text visibility in both modes */
    .stMarkdown, .stText {
        color: var(--text-color);
    }
</style>
""",
    unsafe_allow_html=True,
)


def load_sample_data():
    """Generate sample data for demonstration matching actual data format"""
    np.random.seed(42)
    dates = pd.date_range(start="2025-04-06", end="2025-04-10", freq="30min", tz="UTC")

    data = []
    dump_counter = 1

    for date in dates:
        # Generate data for different serial numbers and wells matching your format
        for serial in [20273, 20274, 20275]:
            for well in [1, 2, 3, 4]:
                # Simulate dump events (not every 30 minutes)
                if np.random.random() > 0.8:  # 20% chance of dump
                    drain_weight = np.random.exponential(scale=15) + 1  # Mostly small values with some larger ones
                    if np.random.random() > 0.85:  # 15% chance of zero weight
                        drain_weight = 0

                    # Create timestamps for created_at and updated_at (slightly after time)
                    created_time = date + timedelta(minutes=np.random.randint(1, 3))
                    updated_time = created_time + timedelta(seconds=np.random.randint(0, 30))

                    data.append(
                        {
                            "time": date,
                            "serial_number": serial,
                            "well_number": well,
                            "dump_number": dump_counter,
                            "drain_weight": round(drain_weight, 2),
                            "created_at": created_time,
                            "updated_at": updated_time,
                        }
                    )
                    dump_counter += 1

    return pd.DataFrame(data)


def load_csv_files(directory_path):
    """Load CSV files from the specified directory"""
    if not os.path.exists(directory_path):
        return None

    csv_files = glob.glob(os.path.join(directory_path, "dump_*.csv"))
    if not csv_files:
        return None

    all_data = []
    for file in csv_files:
        try:
            df = pd.read_csv(file)
            all_data.append(df)
        except Exception as e:
            st.error(f"Error loading {file}: {str(e)}")

    if all_data:
        combined_df = pd.concat(all_data, ignore_index=True)
        return combined_df
    return None


def process_data(df):
    """Process and clean the data"""
    # Handle the actual column name 'time' instead of 'timestamp'
    time_column = "time" if "time" in df.columns else "timestamp"

    if time_column in df.columns:
        # Convert to datetime with flexible format handling for mixed timestamp formats
        try:
            df[time_column] = pd.to_datetime(df[time_column], format="mixed", utc=True)
        except:
            # Fallback to infer format if mixed doesn't work
            df[time_column] = pd.to_datetime(df[time_column], infer_datetime_format=True, utc=True)
        # Create a standard 'timestamp' column for consistency in the rest of the code
        df["timestamp"] = df[time_column]
    else:
        # If no time column, create one based on index (for demo)
        df["timestamp"] = pd.date_range(start="2025-04-06", periods=len(df), freq="30min", tz="UTC")

    # Handle created_at and updated_at if they exist with flexible parsing
    if "created_at" in df.columns:
        try:
            df["created_at"] = pd.to_datetime(df["created_at"], format="mixed", utc=True)
        except:
            df["created_at"] = pd.to_datetime(df["created_at"], infer_datetime_format=True, utc=True)
    if "updated_at" in df.columns:
        try:
            df["updated_at"] = pd.to_datetime(df["updated_at"], format="mixed", utc=True)
        except:
            df["updated_at"] = pd.to_datetime(df["updated_at"], infer_datetime_format=True, utc=True)

    # Ensure required columns exist
    required_columns = ["serial_number", "well_number", "dump_number", "drain_weight"]
    for col in required_columns:
        if col not in df.columns:
            st.error(f"Required column '{col}' not found in data. Found columns: {list(df.columns)}")
            return None

    # Convert data types
    df["drain_weight"] = pd.to_numeric(df["drain_weight"], errors="coerce")
    df["well_number"] = pd.to_numeric(df["well_number"], errors="coerce")
    df["dump_number"] = pd.to_numeric(df["dump_number"], errors="coerce")
    df["serial_number"] = pd.to_numeric(df["serial_number"], errors="coerce")

    # Remove rows with NaN values in critical columns
    df = df.dropna(subset=["drain_weight", "well_number", "dump_number", "serial_number"])

    # Sort by timestamp and dump number
    df = df.sort_values(["timestamp", "dump_number"])

    return df


def detect_asymptotic_behavior(df, threshold=0.5, min_points=5):
    """Detect when drain weights become asymptotic to zero"""
    df_sorted = df.sort_values("timestamp")
    asymptotic_periods = []

    current_low_start = None
    for i, (idx, row) in enumerate(df_sorted.iterrows()):
        if row["drain_weight"] <= threshold:
            if current_low_start is None:
                current_low_start = i
        else:
            if current_low_start is not None and (i - current_low_start) >= min_points:
                start_idx = df_sorted.iloc[current_low_start].name
                end_idx = df_sorted.iloc[i - 1].name
                asymptotic_periods.append(
                    {
                        "start_time": df_sorted.loc[start_idx, "timestamp"],
                        "end_time": df_sorted.loc[end_idx, "timestamp"],
                        "duration_hours": (
                            df_sorted.loc[end_idx, "timestamp"] - df_sorted.loc[start_idx, "timestamp"]
                        ).total_seconds()
                        / 3600,
                    }
                )
            current_low_start = None

    # Handle case where asymptotic period extends to the end
    if current_low_start is not None and (len(df_sorted) - current_low_start) >= min_points:
        start_idx = df_sorted.iloc[current_low_start].name
        end_idx = df_sorted.iloc[-1].name
        asymptotic_periods.append(
            {
                "start_time": df_sorted.loc[start_idx, "timestamp"],
                "end_time": df_sorted.loc[end_idx, "timestamp"],
                "duration_hours": (
                    df_sorted.loc[end_idx, "timestamp"] - df_sorted.loc[start_idx, "timestamp"]
                ).total_seconds()
                / 3600,
            }
        )

    return asymptotic_periods


def detect_valve_changes(df, rise_factor=1.5, stagnation_threshold=2.0, min_stagnation_points=3):
    """Detect potential valve (choke manifold) changes based on percentage rise after decreasing/stagnant period.

    Parameters
    ----------
    df : pd.DataFrame
        DataFrame containing a 'timestamp' and 'drain_weight' columns.
    rise_factor : float
        Factor of increase relative to previous dump weight that constitutes a sudden rise (e.g., 1.5 == 150%).
    stagnation_threshold : float
        Threshold below which weights are considered stagnant.
    min_stagnation_points : int
        Minimum number of previous points to evaluate for decreasing/stagnant pattern.
    """
    df_sorted = df.sort_values("timestamp").reset_index(drop=True)
    valve_changes = []

    # Iterate using a manual index so we can skip ahead when we find a change
    idx = min_stagnation_points - 1  # first index that can have enough history
    while idx < len(df_sorted) - 1:
        baseline_idx = idx

        # Ensure enough previous points exist for pattern check
        window_start = baseline_idx - (min_stagnation_points - 1)
        if window_start < 0:
            idx += 1
            continue

        prev_weights = df_sorted.loc[window_start:baseline_idx, "drain_weight"].values

        all_low = all(w <= stagnation_threshold for w in prev_weights)
        decreasing_trend = all(prev_weights[j] <= prev_weights[j - 1] for j in range(1, len(prev_weights)))
        non_increasing = all(prev_weights[j] <= prev_weights[j - 1] * 1.1 for j in range(1, len(prev_weights)))

        if not (all_low or decreasing_trend or non_increasing):
            idx += 1
            continue

        baseline_weight = df_sorted.loc[baseline_idx, "drain_weight"]
        if baseline_weight == 0:
            idx += 1
            continue

        # Search next three measures for sudden rise
        change_idx = None
        for look_ahead in (1, 2, 3):
            nxt_idx = baseline_idx + look_ahead
            if nxt_idx >= len(df_sorted):
                break
            nxt_weight = df_sorted.loc[nxt_idx, "drain_weight"]
            if nxt_weight >= baseline_weight * rise_factor:
                change_idx = nxt_idx
                break

        if change_idx is None:
            idx += 1
            continue

        # Determine the lowest measurement among the three bars preceding the rise
        search_start = max(change_idx - 3, 0)
        candidate_slice = df_sorted.loc[search_start:change_idx - 1]
        lowest_idx = candidate_slice["drain_weight"].idxmin()

        lowest_weight = df_sorted.loc[lowest_idx, "drain_weight"]
        lowest_time = df_sorted.loc[lowest_idx, "timestamp"]

        valve_changes.append({
            "warning_time": lowest_time,
            "change_time": df_sorted.loc[change_idx, "timestamp"],
            "warning_weight": lowest_weight,
            "change_weight": df_sorted.loc[change_idx, "drain_weight"],
            "ratio": df_sorted.loc[change_idx, "drain_weight"] / lowest_weight if lowest_weight != 0 else np.inf,
            "rise_factor": rise_factor,
            "hours_between": (df_sorted.loc[change_idx, "timestamp"] - lowest_time).total_seconds() / 3600.0,
            "dump_number_warning": df_sorted.loc[lowest_idx, "dump_number"],
            "dump_number_change": df_sorted.loc[change_idx, "dump_number"],
        })

        # Skip ahead past the change to avoid duplicates
        idx = change_idx + 1
    
    return valve_changes


def create_visualization(df, color_by="well_number", show_trend=True, trend_analysis=None, interval_hours: int = 1):
    """Create the main visualization with dark mode support and trend analysis"""
    fig = make_subplots(specs=[[{"secondary_y": False}]])

    # Color mapping
    if color_by == "well_number":
        color_column = "well_number"
        color_discrete_map = px.colors.qualitative.Set1
    else:
        color_column = "serial_number"
        color_discrete_map = px.colors.qualitative.Set2

    # Create bar chart
    for i, (name, group) in enumerate(df.groupby(color_column)):
        # Build hover template dynamically based on available columns
        hover_parts = ["<b>Time:</b> %{x}", "<b>Drain Weight:</b> %{y:.2f} kg"]
        custom_cols = []

        if "dump_number" in group.columns:
            hover_parts.append(f"<b>Dump Count:</b> %{{customdata[{len(custom_cols)}]}}")
            custom_cols.append("dump_number")
        if "serial_number" in group.columns:
            hover_parts.append(f"<b>Serial Number:</b> %{{customdata[{len(custom_cols)}]}}")
            custom_cols.append("serial_number")
        if "well_number" in group.columns:
            hover_parts.append(f"<b>Well Number:</b> %{{customdata[{len(custom_cols)}]}}")
            custom_cols.append("well_number")

        hovertemplate = "<br>".join(hover_parts) + "<extra></extra>"
        customdata_vals = group[custom_cols].values if custom_cols else None

        fig.add_trace(
            go.Bar(
                x=group["timestamp"],
                y=group["drain_weight"],
                name=f"{color_by.replace('_', ' ').title()}: {name}",
                hovertemplate=hovertemplate,
                customdata=customdata_vals,
                marker_color=px.colors.qualitative.Set1[i % len(px.colors.qualitative.Set1)],
                width=interval_hours * 3600000 * 0.8,  # bar spans 80% of the grouping interval
            )
        )

    # Add trend line if requested
    if show_trend and len(df) > 1:
        # Calculate multiple trend indicators
        df_sorted = df.sort_values("timestamp")

        # Moving average (short term)
        short_window = max(3, len(df) // 30)
        df_sorted["short_trend"] = df_sorted["drain_weight"].rolling(window=short_window, center=True).mean()

        # Moving average (long term)
        long_window = max(5, len(df) // 15)
        df_sorted["long_trend"] = df_sorted["drain_weight"].rolling(window=long_window, center=True).mean()

        # Exponential moving average for recent trend
        df_sorted["exp_trend"] = df_sorted["drain_weight"].ewm(span=max(3, len(df) // 25)).mean()

        # Short-term trend (more responsive)
        fig.add_trace(
            go.Scatter(
                x=df_sorted["timestamp"],
                y=df_sorted["short_trend"],
                mode="lines",
                name="Short-term Trend",
                line=dict(color="orange", width=2, dash="dot"),
                hovertemplate="<b>Short Trend:</b> %{y:.2f} kg<extra></extra>",
            )
        )

        # Long-term trend (smoother)
        fig.add_trace(
            go.Scatter(
                x=df_sorted["timestamp"],
                y=df_sorted["long_trend"],
                mode="lines",
                name="Long-term Trend",
                line=dict(color="red", width=3, dash="dash"),
                hovertemplate="<b>Long Trend:</b> %{y:.2f} kg<extra></extra>",
            )
        )

        # Exponential trend (recent emphasis)
        fig.add_trace(
            go.Scatter(
                x=df_sorted["timestamp"],
                y=df_sorted["exp_trend"],
                mode="lines",
                name="Exponential Trend",
                line=dict(color="purple", width=2),
                hovertemplate="<b>Exp Trend:</b> %{y:.2f} kg<extra></extra>",
            )
        )

    # Add trend analysis annotations if provided
    if trend_analysis:
        # Mark valve changes (potential choke changes)
        for vc in trend_analysis.get("valve_changes", []):
            fig.add_scatter(
                x=[vc["warning_time"],],
                y=[vc["warning_weight"],],
                mode="markers+text",
                marker=dict(symbol="triangle-up", size=15, color="red", line=dict(width=2, color="darkred")),
                text=["🔧"],
                textposition="top center",
                name="Potencial cambio de valvula",
                hovertemplate=(
                    "<b>Potencial cambio de valvula</b><br>"
                    "<b>Hora de aviso:</b> %{x}<br>"
                    "<b>Peso de aviso:</b> %{y:.2f} kg<br>"
                    f"<b>Peso al cambio:</b> {vc['change_weight']:.2f} kg<br>"
                    f"<b>Ratio subida:</b> {vc['ratio']:.2f}x<br>"
                    f"<b>Dump # aviso:</b> {vc['dump_number_warning']}<br>"
                    f"<b>Dump # cambio:</b> {vc['dump_number_change']}<br>"
                    f"<b>Horas hasta cambio:</b> {vc['hours_between']:.2f} h<br>"
                    "<extra></extra>"
                ),
            )

    # Update layout with theme support
    fig.update_layout(
        title="Desander Drain Weight Analysis - Trend Analysis",
        xaxis_title="Date/Time",
        yaxis_title="Drain Weight (kg)",
        hovermode="x unified",
        showlegend=True,
        height=700,  # Increased height for better trend visibility
        xaxis=dict(tickformat="%Y-%m-%d %H:%M", tickangle=45),
        yaxis=dict(tickformat=".2f"),
        # Dynamic theming based on Streamlit's theme
        template="plotly_white",
        plot_bgcolor="rgba(0,0,0,0)",  # Transparent background
        paper_bgcolor="rgba(0,0,0,0)",  # Transparent paper
        font=dict(color="rgb(50,50,50)"),  # Neutral color that works in both modes
    )

    # Update grid colors to be more subtle
    fig.update_xaxes(
        showgrid=True, gridwidth=1, gridcolor="rgba(128,128,128,0.2)", zerolinecolor="rgba(128,128,128,0.3)"
    )
    fig.update_yaxes(
        showgrid=True, gridwidth=1, gridcolor="rgba(128,128,128,0.2)", zerolinecolor="rgba(128,128,128,0.3)"
    )

    return fig


def create_summary_stats(df):
    """Create summary statistics"""
    stats = {
        "Total Dumps": len(df),
        "Total Drain Weight": f"{df['drain_weight'].sum():.2f} kg",
        "Average Drain Weight": f"{df['drain_weight'].mean():.2f} kg",
        "Max Drain Weight": f"{df['drain_weight'].max():.2f} kg",
        "Active Wells": df["well_number"].nunique(),
        "Active Serial Numbers": df["serial_number"].nunique(),
    }
    return stats


# Add new helper to aggregate data by time interval
def aggregate_by_interval(df, interval_hours: int = 1, offset_hour: int = 0, color_by: str = "well_number"):
    """Aggregate drain weights by a fixed hourly interval with an optional daily offset.

    Parameters
    ----------
    df : pd.DataFrame
        Input dataframe containing at least a 'timestamp' column and the chosen color_by column.
    interval_hours : int
        Width of each time bin in hours (1-24).
    offset_hour : int
        Hour of day that marks the start of the first interval (0-23). For example, with
        offset_hour=8 and interval_hours=8 the bins will be 08-16, 16-00, 00-08.
    color_by : str
        Column used for colour-coding the bars – either 'well_number' or 'serial_number'.

    Returns
    -------
    pd.DataFrame
        Aggregated dataframe with one row per (interval, color_by) pair. The resulting
        dataframe contains at least the columns:
        ['timestamp', 'drain_weight', 'dump_number', 'serial_number', 'well_number'] so
        that the existing visualisation logic keeps working.
    """

    if df.empty:
        return df.copy()

    # Ensure we work on a copy to avoid SettingWithCopy warnings
    df_ = df.copy()

    # Compute the start time of the bin each datapoint belongs to
    ts_shifted = df_["timestamp"] - pd.Timedelta(hours=offset_hour)
    df_["_interval_start"] = ts_shifted.dt.floor(f"{interval_hours}H") + pd.Timedelta(hours=offset_hour)

    # Group and aggregate
    group_cols = ["_interval_start", color_by]
    agg = (
        df_.groupby(group_cols)
        .agg(
            drain_weight=("drain_weight", "sum"),  # total weight in the bin
            dump_number=("dump_number", "count"),   # number of dumps aggregated
        )
        .reset_index()
    )

    # Rename for downstream compatibility
    agg["timestamp"] = agg["_interval_start"]
    agg.drop(columns=["_interval_start"], inplace=True)

    # Ensure the presence of both serial_number and well_number columns so the hover
    # templates do not fail even when grouping by one of them.
    if "serial_number" not in agg.columns:
        agg["serial_number"] = np.nan
    if "well_number" not in agg.columns:
        agg["well_number"] = np.nan

    # Re-order for clarity
    ordered_cols = ["timestamp", "serial_number", "well_number", "dump_number", "drain_weight"]
    # Ensure the grouping column is included exactly once
    if color_by not in ordered_cols:
        ordered_cols.insert(3, color_by)

    agg = agg[ordered_cols]

    return agg


def main():
    st.title("🛢️ Desander Data Analysis Tool")
    st.markdown("---")

    # Sidebar for controls
    st.sidebar.header("📊 Analysis Controls")

    # Data source selection
    data_source = st.sidebar.radio(
        "Select Data Source:", ["Use Sample Data", "Upload CSV Files", "Load from Directory"]
    )

    # Check if data source changed
    if data_source != st.session_state.data_source:
        st.session_state.data_source = data_source
        st.session_state.df = None
        st.session_state.data_loaded = False

    df = None

    if data_source == "Use Sample Data":
        if not st.session_state.data_loaded or st.session_state.df is None:
            st.session_state.df = load_sample_data()
            st.session_state.data_loaded = True
        df = st.session_state.df
        st.sidebar.success("✅ Sample data loaded successfully!")

    elif data_source == "Upload CSV Files":
        uploaded_files = st.sidebar.file_uploader("Upload CSV files", type=["csv"], accept_multiple_files=True)

        if uploaded_files:
            # Create a unique key for uploaded files to detect changes
            file_names = [f.name for f in uploaded_files]
            file_key = str(sorted(file_names))

            # Check if files changed
            if "uploaded_files_key" not in st.session_state or st.session_state.uploaded_files_key != file_key:

                all_data = []
                for file in uploaded_files:
                    try:
                        file_df = pd.read_csv(file)
                        all_data.append(file_df)
                    except Exception as e:
                        st.sidebar.error(f"Error reading {file.name}: {str(e)}")

                if all_data:
                    st.session_state.df = pd.concat(all_data, ignore_index=True)
                    st.session_state.data_loaded = True
                    st.session_state.uploaded_files_key = file_key
                    st.sidebar.success(f"✅ Loaded {len(uploaded_files)} files successfully!")

            df = st.session_state.df
            if df is not None:
                st.sidebar.success(f"✅ Loaded {len(uploaded_files)} files successfully!")

    elif data_source == "Load from Directory":
        directory_path = st.sidebar.text_input(
            "Enter directory path:", value="./Dumps", help="Path to directory containing dump_*.csv files"
        )

        if st.sidebar.button("Load Files"):
            loaded_df = load_csv_files(directory_path)
            if loaded_df is not None:
                st.session_state.df = loaded_df
                st.session_state.data_loaded = True
                st.sidebar.success("✅ Files loaded successfully!")
            else:
                st.sidebar.error("❌ No files found or error loading files")

        # Use loaded data from session state
        if st.session_state.data_loaded and st.session_state.df is not None:
            df = st.session_state.df
            st.sidebar.success("✅ Files loaded successfully!")

    if df is not None:
        # Process the data
        df = process_data(df)

        if df is not None:
            st.sidebar.markdown("---")

            # Filter for non-zero drain weights
            original_count = len(df)
            df = df[df["drain_weight"] > 0]
            filtered_count = len(df)

            st.sidebar.info(
                f"Showing {filtered_count} records with drain_weight > 0\n(Filtered out {original_count - filtered_count} zero-weight records)"
            )

            # Filters
            st.sidebar.subheader("🔍 Filters")

            # Serial number filter
            serial_numbers = sorted(df["serial_number"].unique())
            selected_serials = st.sidebar.multiselect(
                "Select Serial Numbers:",
                options=serial_numbers,
                default=[],  # Start with none selected for better performance
            )

            # Well number filter
            well_numbers = sorted(df["well_number"].unique())
            selected_wells = st.sidebar.multiselect(
                "Select Well Numbers:",
                options=well_numbers,
                default=[],  # Start with none selected for better performance
            )

            # Date range filter
            if "timestamp" in df.columns:
                min_date = df["timestamp"].min().date()
                max_date = df["timestamp"].max().date()

                date_range = st.sidebar.date_input(
                    "Select Date Range:", value=(min_date, max_date), min_value=min_date, max_value=max_date
                )

                if isinstance(date_range, tuple) and len(date_range) == 2:
                    start_date, end_date = date_range
                else:
                    start_date = end_date = date_range

            # Visualization options
            st.sidebar.subheader("🎨 Visualization Options")
            color_by = st.sidebar.selectbox(
                "Color bars by:",
                options=["well_number", "serial_number"],
                format_func=lambda x: x.replace("_", " ").title(),
            )

            show_trend = st.sidebar.checkbox("Show Trend Lines", value=True)

            # Grouping options
            st.sidebar.subheader("⏱️ Grouping Options")
            group_interval_hours = st.sidebar.slider(
                "Grouping interval (hours):",
                min_value=1,
                max_value=24,
                value=1,
                step=1,
                help="Number of hours to combine into a single bar on the chart",
            )

            start_hour = st.sidebar.slider(
                "Start hour of first interval (0-23):",
                min_value=0,
                max_value=23,
                value=0,
                step=1,
                help="Hour of day at which the first interval begins. For example, select 8 for bins 08-16, 16-00, 00-08 when using an 8-hour interval.",
            )

            # Trend Analysis Parameters
            st.sidebar.subheader("🔍 Trend Analysis Settings")

            rise_percentage = st.sidebar.slider(
                "Incremento repentino (%):",
                min_value=150,
                max_value=400,
                value=150,
                step=10,
                help="Porcentaje de aumento entre un dump y el siguiente que indica un potencial cambio de valvula",
            )

            # Convert percentage to multiplicative factor (e.g., 150 -> 1.5)
            rise_factor = rise_percentage / 100.0

            stagnation_threshold = st.sidebar.slider(
                "Stagnation threshold (kg):",
                min_value=0.5,
                max_value=5.0,
                value=2.0,
                step=0.1,
                help="Values below this are considered stagnant (low activity period)",
            )

            # Apply filters
            filtered_df = df.copy()

            # Only apply serial number filter if selections are made
            if selected_serials:
                filtered_df = filtered_df[filtered_df["serial_number"].isin(selected_serials)]

            # Only apply well number filter if selections are made
            if selected_wells:
                filtered_df = filtered_df[filtered_df["well_number"].isin(selected_wells)]

            if "timestamp" in filtered_df.columns and len(date_range) == 2:
                filtered_df = filtered_df[
                    (filtered_df["timestamp"].dt.date >= start_date) & (filtered_df["timestamp"].dt.date <= end_date)
                ]

            if len(filtered_df) > 0 or (not selected_serials and not selected_wells):
                # Show message when no filters are applied
                if not selected_serials and not selected_wells:
                    st.info("💡 Select serial numbers and/or well numbers from the sidebar to view data and charts.")

                    # Show basic statistics even without filters
                    stats = create_summary_stats(df)
                    st.subheader("📊 Dataset Overview")

                    # Display metrics in a grid
                    metric_cols = st.columns(3)
                    metrics_items = list(stats.items())

                    for i, (key, value) in enumerate(metrics_items):
                        with metric_cols[i % 3]:
                            st.metric(key, value)

                    # Show available options
                    col1, col2 = st.columns(2)
                    with col1:
                        st.write("**Available Serial Numbers:**")
                        st.write(", ".join(map(str, sorted(df["serial_number"].unique()))))
                    with col2:
                        st.write("**Available Well Numbers:**")
                        st.write(", ".join(map(str, sorted(df["well_number"].unique()))))

                    return  # Exit early to avoid showing empty charts

                # Main content area when filters are applied
                col1, col2 = st.columns([3, 1])

                with col1:
                    # Summary statistics
                    stats = create_summary_stats(filtered_df)

                    # Display metrics in a grid
                    metric_cols = st.columns(3)
                    metrics_items = list(stats.items())

                    for i, (key, value) in enumerate(metrics_items):
                        with metric_cols[i % 3]:
                            st.metric(key, value)

                with col2:
                    # Export functionality
                    st.subheader("📥 Export Data")

                    csv_data = filtered_df.to_csv(index=False)
                    st.download_button(
                        label="Download Filtered Data as CSV",
                        data=csv_data,
                        file_name=f"desander_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                        mime="text/csv",
                    )

                # Visualization preparation: aggregate by selected interval first
                graph_df = aggregate_by_interval(
                    filtered_df,
                    interval_hours=group_interval_hours,
                    offset_hour=start_hour,
                    color_by=color_by,
                )

                # Perform trend analysis
                trend_analysis = {}
                if len(graph_df) > 1:
                    valve_changes_all = []
                    # Detect per grouping column to avoid cross-well interference
                    group_col = color_by  # 'well_number' or 'serial_number'
                    for g_val, g_df in graph_df.groupby(group_col):
                        changes = detect_valve_changes(
                            g_df,
                            rise_factor=rise_factor,
                            stagnation_threshold=stagnation_threshold,
                            min_stagnation_points=3,
                        )
                        # attach group identifier to each change
                        for ch in changes:
                            ch[group_col] = g_val
                        valve_changes_all.extend(changes)

                    trend_analysis = {
                        "valve_changes": valve_changes_all
                    }

                # Trend Analysis Summary
                if trend_analysis:
                    st.subheader("🔬 Trend Analysis Summary")
                    
                    # Add explanation of the detection logic
                    st.info("""
                    **Choke Manifold Change Detection Logic:**
                    The system now detects potential choke manifold changes only when there's a pattern of 
                    decreasing or stagnant weights followed by a sudden rise. This includes:
                    - 📉 **Stagnant pattern**: Several consecutive low-weight dumps
                    - 📉 **Decreasing trend**: Each dump weight is less than or equal to the previous
                    - 📉 **Non-increasing trend**: No significant increases in recent dumps
                    """)

                    # Compact metrics side-by-side just above the graph
                    metric_small_cols = st.columns([2, 2, 4])

                    with metric_small_cols[0]:
                        st.metric("Potenciales cambios de valvula", len(trend_analysis["valve_changes"]))

                    total_unproductive_hours = sum(vc['hours_between'] for vc in trend_analysis['valve_changes'])
                    with metric_small_cols[1]:
                        st.metric("Cantidad de horas no útiles", f"{total_unproductive_hours:.1f} h")

                # Visualization
                st.subheader("📈 Drain Weight Analysis with Trend Detection")

                if len(graph_df) > 0:
                    fig = create_visualization(graph_df, color_by, show_trend, trend_analysis, interval_hours=group_interval_hours)
                    st.plotly_chart(fig, use_container_width=True)

                # Detailed list of valve changes after the graph
                if trend_analysis and trend_analysis["valve_changes"]:
                    st.subheader("🔧 Potenciales cambios de valvula")
                    for i, change in enumerate(trend_analysis["valve_changes"]):
                        st.write(
                            f"• {change['warning_time'].strftime('%m/%d %H:%M')}: "
                            f"{change['warning_weight']:.1f}kg (↑{change['change_weight'] - change['warning_weight']:.1f}kg) "
                            f"Dump #{change['dump_number_warning']} to {change['dump_number_change']}"
                        )

                # Data table
                st.subheader("📋 Detailed Measurements")

                # Format the dataframe for display
                display_df = filtered_df.copy()

                # Choose which timestamp column to display
                if "time" in display_df.columns:
                    display_df["time"] = display_df["time"].dt.strftime("%Y-%m-%d %H:%M:%S UTC")
                    timestamp_col = "time"
                elif "timestamp" in display_df.columns:
                    display_df["timestamp"] = display_df["timestamp"].dt.strftime("%Y-%m-%d %H:%M:%S UTC")
                    timestamp_col = "timestamp"

                # Format other timestamp columns if they exist
                if "created_at" in display_df.columns:
                    display_df["created_at"] = display_df["created_at"].dt.strftime("%Y-%m-%d %H:%M:%S UTC")
                if "updated_at" in display_df.columns:
                    display_df["updated_at"] = display_df["updated_at"].dt.strftime("%Y-%m-%d %H:%M:%S UTC")

                # Reorder columns for better display, including the new columns
                base_columns = [timestamp_col, "serial_number", "well_number", "dump_number", "drain_weight"]
                additional_columns = []
                if "created_at" in display_df.columns:
                    additional_columns.append("created_at")
                if "updated_at" in display_df.columns:
                    additional_columns.append("updated_at")

                column_order = base_columns + additional_columns
                display_df = display_df[column_order]

                # Rename columns for better display
                column_names = {
                    "time": "Time",
                    "timestamp": "Timestamp",
                    "serial_number": "Serial Number",
                    "well_number": "Well Number",
                    "dump_number": "Dump Number",
                    "drain_weight": "Drain Weight (kg)",
                    "created_at": "Created At",
                    "updated_at": "Updated At",
                }
                display_df = display_df.rename(columns=column_names)

                st.dataframe(display_df, use_container_width=True, height=400)

                # Additional analysis
                if st.checkbox("Show Advanced Analytics"):
                    st.subheader("🔬 Advanced Analytics")

                    # Trend Analysis Details
                    if trend_analysis and trend_analysis["valve_changes"]:
                        st.subheader("📊 Detailed Trend Analysis")

                        # Valve changes detailed table
                        st.write("**Potenciales cambios de valvula:**")
                        changes_df = pd.DataFrame(trend_analysis["valve_changes"])
                        changes_df["warning_time"] = changes_df["warning_time"].dt.strftime("%Y-%m-%d %H:%M")
                        changes_df["change_time"] = changes_df["change_time"].dt.strftime("%Y-%m-%d %H:%M")
                        
                        # Rename columns for better display
                        changes_df = changes_df.rename(columns={
                            "warning_time": "Warning Time",
                            "change_time": "Change Time",
                            "warning_weight": "Warning Weight (kg)",
                            "change_weight": "Change Weight (kg)",
                            "ratio": "Rise Ratio",
                            "rise_factor": "Rise Factor",
                            "hours_between": "Hours Between",
                            "dump_number_warning": "Warning Dump Number",
                            "dump_number_change": "Change Dump Number"
                        })
                        
                        changes_df = changes_df.round(2)
                        st.dataframe(changes_df, use_container_width=True)

                    col1, col2 = st.columns(2)

                    with col1:
                        # Distribution by well
                        well_stats = (
                            filtered_df.groupby("well_number")["drain_weight"].agg(["count", "sum", "mean"]).round(2)
                        )
                        well_stats.columns = ["Total Dumps", "Total Weight (kg)", "Average Weight (kg)"]
                        st.write("**Analysis by Well Number:**")
                        st.dataframe(well_stats)

                    with col2:
                        # Distribution by serial number
                        serial_stats = (
                            filtered_df.groupby("serial_number")["drain_weight"].agg(["count", "sum", "mean"]).round(2)
                        )
                        serial_stats.columns = ["Total Dumps", "Total Weight (kg)", "Average Weight (kg)"]
                        st.write("**Analysis by Serial Number:**")
                        st.dataframe(serial_stats)

            else:
                st.warning("⚠️ No data matches the selected filters. Please adjust your filter criteria.")

    else:
        st.info("👆 Please select a data source from the sidebar to begin analysis.")

        # Show expected data format
        st.subheader("📋 Expected Data Format")
        st.write("Your CSV files should contain the following columns:")

        sample_format = pd.DataFrame(
            {
                "time": ["2025-04-06 23:59:51.917000+00:00", "2025-04-07 00:30:15.234000+00:00"],
                "serial_number": [20273, 20274],
                "well_number": [4, 2],
                "dump_number": [68, 69],
                "drain_weight": [1.0, 12.5],
                "created_at": ["2025-04-07 00:01:14.524005+00:00", "2025-04-07 00:31:20.456000+00:00"],
                "updated_at": ["2025-04-07 00:01:14.524005+00:00", "2025-04-07 00:31:20.456000+00:00"],
            }
        )

        st.dataframe(sample_format)

        st.write(
            """
        **Column Descriptions:**
        - `time`: Date and time of the measurement (with timezone)
        - `serial_number`: Numeric identifier for the desander unit
        - `well_number`: Well number being processed
        - `dump_number`: Sequential dump number
        - `drain_weight`: Weight of material drained (kg)
        - `created_at`: Record creation timestamp (optional)
        - `updated_at`: Record update timestamp (optional)

        **Note:** The tool will automatically handle timezone information and convert timestamps appropriately.
        """
        )


if __name__ == "__main__":
    main()
