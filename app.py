import streamlit as st
import matplotlib
import pandas as pd
import plotly.express as px
import datetime
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# ------------------------------
# Config
# ------------------------------
st.set_page_config(page_title="MarkSense", layout="wide")
PLOTLY_THEME = "plotly_white"
GSHEET_NAME = "MarkSenseHistory"           # your sheet name
SERVICE_ACCOUNT_FILE = "service_account.json"  # place this next to the app
subjects = ["Maths", "Science", "English", "History", "Computer"]

# ----------------------------------
# Connect to Google Sheets securely
# ----------------------------------
def connect_sheets():
    """Return gspread sheet object or None if connection fails."""
    try:
        scope = [
            "https://spreadsheets.google.com/feeds",
            "https://www.googleapis.com/auth/drive"
        ]
        # Load credentials securely from Streamlit Secrets
        service_account_info = st.secrets["google_service_account"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(service_account_info, scope)
        client = gspread.authorize(creds)
        sheet = client.open(GSHEET_NAME).sheet1
        return sheet
    except Exception as e:
        st.warning("Google Sheets connection failed. Reason: " + str(e))
        return None

def read_history_from_sheet(sheet):
    """Return a DataFrame read from the sheet, or an empty DataFrame."""
    try:
        data = sheet.get_all_records()
        if not data:
            cols = ["Date", "Name"] + subjects + ["Total", "Average", "Rank"]
            return pd.DataFrame(columns=cols)
        df = pd.DataFrame(data)
        for c in ["Date", "Name"] + subjects + ["Total", "Average", "Rank"]:
            if c not in df.columns:
                df[c] = None
        return df[["Date", "Name"] + subjects + ["Total", "Average", "Rank"]]
    except Exception as e:
        st.warning("Failed reading sheet: " + str(e))
        return pd.DataFrame(columns=["Date", "Name"] + subjects + ["Total", "Average", "Rank"])

def append_rows_to_sheet(sheet, df_rows):
    """Append rows (iterable of lists) to the sheet."""
    try:
        for row in df_rows:
            sheet.append_row(row)
        return True
    except Exception as e:
        st.warning("Failed writing to Google Sheet: " + str(e))
        return False

# Connect once
sheet = connect_sheets()

# ------------------------------
# Sidebar navigation + state
# ------------------------------
if "page" not in st.session_state:
    st.session_state.page = "Home"
page = st.sidebar.radio("📍 Navigate", ["Home", "Visualizer", "Progress", "About"],
                        index=["Home", "Visualizer", "Progress", "About"].index(st.session_state.page))
st.session_state.page = page

# ------------------------------
# Home page - ENHANCED INTERACTIVE VERSION
# ------------------------------
if page == "Home":
    st.title("📘 MarkSense")
    st.subheader("Smart Student Marks Visualizer")
    st.write("Track performance daily with interactive charts and topper analysis.")

    with st.expander("ℹ️ About this App"):
        st.write("""
        **MarkSense** helps students and teachers track performance daily.
        - Enter marks subject-wise
        - Get totals, averages and ranks
        - Visualize performance with charts
        - Save daily results to Google Sheets
        """)

    # load history from Google Sheets
    if sheet:
        history_df = read_history_from_sheet(sheet)
    else:
        history_df = pd.DataFrame(columns=["Date", "Name"] + subjects)

    if not history_df.empty:
        # Ensure numeric subject columns exist and compute Total/Average safely
        for sub in subjects:
            if sub not in history_df.columns:
                history_df[sub] = 0
        history_df[subjects] = history_df[subjects].apply(pd.to_numeric, errors="coerce").fillna(0)
        history_df["Total"] = history_df[subjects].sum(axis=1)
        history_df["Average"] = history_df[subjects].mean(axis=1)

        # --- INTERACTIVE FEATURE 1: Date Selector ---
        st.markdown("---")
        st.subheader("📅 Select Date to View")
        available_dates = sorted(history_df['Date'].unique(), reverse=True)
        selected_date = st.selectbox("Choose a date:", available_dates, index=0)
        
        latest_data = history_df[history_df['Date'] == selected_date]

        if not latest_data.empty:
            # --- INTERACTIVE FEATURE 2: Top 3 Leaderboard ---
            st.markdown("---")
            col1, col2 = st.columns([2, 1])
            
            with col1:
                st.subheader("🏆 Top 3 Leaderboard")
                top3 = latest_data.nlargest(3, 'Total')[['Name', 'Total', 'Average']].reset_index(drop=True)
                top3.index = ['🥇 1st', '🥈 2nd', '🥉 3rd'][:len(top3)]
                st.dataframe(top3, use_container_width=True)
            
            with col2:
                topper = latest_data.loc[latest_data['Total'].idxmax()]
                st.metric(label="🏆 Top Scorer", value=topper['Name'], delta=f"{int(topper['Total'])} marks")
                st.metric(label="📊 Average", value=f"{topper['Average']:.1f}", delta="Best performer")

            # --- Class Statistics ---
            st.markdown("---")
            avg_today = latest_data['Average'].mean()
            max_today = latest_data['Total'].max()
            min_today = latest_data['Total'].min()
            
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("📈 Class Average", f"{avg_today:.1f}")
            col2.metric("⭐ Highest Total", f"{int(max_today)}")
            col3.metric("📉 Lowest Total", f"{int(min_today)}")
            col4.metric("👥 Total Students", len(latest_data))

            # --- INTERACTIVE FEATURE 3: Subject Performance Chart ---
            st.markdown("---")
            st.subheader("📊 Subject-wise Performance")
            
            chart_col1, chart_col2 = st.columns([3, 1])
            
            with chart_col2:
                st.write("**Options:**")
                show_class_avg = st.checkbox("Show Class Average", value=True)
                chart_style = st.radio("Chart Style:", ["Bar", "Line"], index=0)
            
            with chart_col1:
                subject_means = latest_data[subjects].mean()
                
                if chart_style == "Bar":
                    fig = px.bar(subject_means, x=subject_means.index, y=subject_means.values,
                                labels={'y': 'Average Marks', 'x': 'Subject'}, 
                                template=PLOTLY_THEME, 
                                title=f"Subject Averages - {selected_date}")
                    fig.update_traces(marker_color='#1f77b4')
                else:
                    fig = px.line(subject_means, x=subject_means.index, y=subject_means.values,
                                 labels={'y': 'Average Marks', 'x': 'Subject'}, 
                                 template=PLOTLY_THEME,
                                 title=f"Subject Averages - {selected_date}",
                                 markers=True)
                
                if show_class_avg:
                    fig.add_hline(y=avg_today, line_dash="dash", 
                                 annotation_text=f"Class Avg: {avg_today:.1f}",
                                 line_color="red")
                
                st.plotly_chart(fig, use_container_width=True)

            # --- INTERACTIVE FEATURE 4: Student Search & Compare ---
            st.markdown("---")
            st.subheader("🔍 Search & Compare Students")
            
            search_col1, search_col2 = st.columns([2, 1])
            
            with search_col1:
                student_names = latest_data['Name'].unique().tolist()
                selected_students = st.multiselect(
                    "Select students to compare (max 5):",
                    student_names,
                    default=student_names[:2] if len(student_names) >= 2 else student_names,
                    max_selections=5
                )
            
            with search_col2:
                comparison_type = st.radio("Compare by:", ["Total Marks", "Subject-wise"])
            
            if selected_students:
                filtered_students = latest_data[latest_data['Name'].isin(selected_students)]
                
                if comparison_type == "Total Marks":
                    fig_compare = px.bar(filtered_students, x='Name', y='Total',
                                        title="Total Marks Comparison",
                                        template=PLOTLY_THEME,
                                        color='Total',
                                        color_continuous_scale='Blues')
                    st.plotly_chart(fig_compare, use_container_width=True)
                else:
                    # Subject-wise comparison
                    melted = filtered_students.melt(id_vars=['Name'], 
                                                   value_vars=subjects,
                                                   var_name='Subject', 
                                                   value_name='Marks')
                    fig_compare = px.bar(melted, x='Subject', y='Marks', color='Name',
                                        barmode='group',
                                        title="Subject-wise Comparison",
                                        template=PLOTLY_THEME)
                    st.plotly_chart(fig_compare, use_container_width=True)
                
                # Show detailed table
                st.dataframe(filtered_students[['Name'] + subjects + ['Total', 'Average']]
                           .style.background_gradient(cmap="Blues", subset=subjects),
                           use_container_width=True)

            # --- INTERACTIVE FEATURE 5: Performance Distribution ---
            st.markdown("---")
            st.subheader("📈 Performance Distribution")
            
            dist_col1, dist_col2 = st.columns(2)
            
            with dist_col1:
                # Total marks distribution
                fig_hist = px.histogram(latest_data, x='Total', nbins=10,
                                       title="Total Marks Distribution",
                                       template=PLOTLY_THEME,
                                       labels={'Total': 'Total Marks', 'count': 'Number of Students'})
                fig_hist.update_traces(marker_color='lightblue')
                st.plotly_chart(fig_hist, use_container_width=True)
            
            with dist_col2:
                # Average marks distribution
                fig_avg_hist = px.histogram(latest_data, x='Average', nbins=10,
                                           title="Average Marks Distribution",
                                           template=PLOTLY_THEME,
                                           labels={'Average': 'Average Marks', 'count': 'Number of Students'})
                fig_avg_hist.update_traces(marker_color='lightgreen')
                st.plotly_chart(fig_avg_hist, use_container_width=True)

            # --- INTERACTIVE FEATURE 6: Student Spotlight with Filter ---
            st.markdown("---")
            st.subheader("✨ Student Spotlight")
            
            spotlight_col1, spotlight_col2 = st.columns([1, 3])
            
            with spotlight_col1:
                spotlight_option = st.radio("Show:", 
                                           ["Random Student", "Select Student", "Top Performer", "Needs Improvement"])
            
            with spotlight_col2:
                if spotlight_option == "Random Student":
                    spotlight_student = latest_data.sample(1).iloc[0]
                elif spotlight_option == "Select Student":
                    selected_name = st.selectbox("Choose student:", latest_data['Name'].unique())
                    spotlight_student = latest_data[latest_data['Name'] == selected_name].iloc[0]
                elif spotlight_option == "Top Performer":
                    spotlight_student = latest_data.loc[latest_data['Total'].idxmax()]
                else:  # Needs Improvement
                    spotlight_student = latest_data.loc[latest_data['Total'].idxmin()]
                
                # Display student card
                st.markdown(f"### 👤 {spotlight_student['Name']}")
                metric_cols = st.columns(3)
                metric_cols[0].metric("Total Marks", int(spotlight_student['Total']))
                metric_cols[1].metric("Average", f"{spotlight_student['Average']:.1f}")
                
                # Calculate rank
                rank = (latest_data['Total'] > spotlight_student['Total']).sum() + 1
                metric_cols[2].metric("Rank", f"#{rank}")
                
                # Subject breakdown
                student_subjects = spotlight_student[subjects]
                fig_student = px.bar(x=subjects, y=student_subjects.values,
                                    title=f"{spotlight_student['Name']}'s Subject Performance",
                                    template=PLOTLY_THEME,
                                    labels={'x': 'Subject', 'y': 'Marks'})
                st.plotly_chart(fig_student, use_container_width=True)

        else:
            st.warning("No entries for selected date.")
    else:
        st.warning("No saved progress yet. Go to Visualizer and save today's results.")

    # --- Quick Action Button ---
    st.markdown("---")
    if st.button("🚀 Go to Visualizer", type="primary", use_container_width=True):
        st.session_state.page = "Visualizer"
        st.rerun()

# ------------------------------
# Visualizer page
# ------------------------------
elif page == "Visualizer":
    st.title("📊 Student Marks Visualizer")
    st.write("Analyze marks, edit or load saved data, then save to Google Sheets.")

    # persistent sidebar settings
    st.sidebar.header("⚙️ Settings")
    if "max_marks" not in st.session_state:
        st.session_state.max_marks = 100
    max_marks = st.sidebar.number_input(
        "Maximum Marks per Subject", 10, 500, 
        value=st.session_state.max_marks, key="max_marks_input"
    )
    st.session_state.max_marks = max_marks

    if "num_students" not in st.session_state:
        st.session_state.num_students = 3
    n = st.sidebar.number_input(
        "Number of Students", 1, 100, 
        value=st.session_state.num_students, key="num_students_input"
    )
    st.session_state.num_students = n

    # Clear inputs
    if st.button("🧹 Clear All Inputs"):
        for i in range(st.session_state.num_students):
            st.session_state.pop(f"name_{i}", None)
            for sub in subjects:
                st.session_state.pop(f"{sub}_{i}", None)
        st.session_state.student_data = [{} for _ in range(st.session_state.num_students)]
        st.success("All student inputs cleared.")

    # Ensure student_data matches number of students
    if "student_data" not in st.session_state:
        st.session_state.student_data = [{} for _ in range(n)]
    else:
        if len(st.session_state.student_data) < n:
            st.session_state.student_data += [{} for _ in range(n - len(st.session_state.student_data))]
        elif len(st.session_state.student_data) > n:
            st.session_state.student_data = st.session_state.student_data[:n]

    # ✅ Load Last Saved Data button (fixed placement)
    st.header("Step 1: Load Last Saved Data (Optional)")
    if st.button("🕒 Load Last Saved Data"):
        if sheet:
            history_df = read_history_from_sheet(sheet)
        else:
            history_df = pd.DataFrame(columns=["Date", "Name"] + subjects + ["Total", "Average", "Rank"])
            
        if not history_df.empty:
            for sub in subjects:
                if sub not in history_df.columns:
                    history_df[sub] = 0
            history_df[subjects] = history_df[subjects].apply(pd.to_numeric, errors="coerce").fillna(0)

            # Compute Total/Average/Rank if not present
            if "Total" not in history_df.columns:
                history_df["Total"] = history_df[subjects].sum(axis=1)
            if "Average" not in history_df.columns:
                history_df["Average"] = history_df[subjects].mean(axis=1)
            if "Rank" not in history_df.columns:
                history_df["Rank"] = history_df["Total"].rank(ascending=False, method="min").astype(int)

            # Get latest date's data
            latest_date = history_df["Date"].max()
            latest_data = history_df[history_df["Date"] == latest_date]

            if not latest_data.empty:
                st.session_state.student_data = latest_data[["Name"] + subjects].to_dict("records")

                # Clear any old keys
                for key in list(st.session_state.keys()):
                    if key.startswith("name_") or any(key.startswith(f"{sub}_") for sub in subjects):
                        st.session_state.pop(key, None)

                # Refill session state
                for i, student in enumerate(st.session_state.student_data):
                    st.session_state[f"name_{i}"] = student["Name"]
                    for sub in subjects:
                        st.session_state[f"{sub}_{i}"] = student[sub]

                st.success(f"✅ Loaded last saved data from {latest_date}")
            else:
                st.warning("No rows found for latest date.")
        else:
            st.warning("No saved data available.")

    # Manual inputs (persistent)
    student_data = []
    for i in range(n):
        with st.expander(f"Student {i+1}"):
            name_key = f"name_{i}"
            if name_key not in st.session_state:
                st.session_state[name_key] = st.session_state.student_data[i].get("Name", "") if i < len(st.session_state.student_data) else ""
            name = st.text_input("Name", value=st.session_state[name_key], key=f"name_input_{i}")
            st.session_state[name_key] = name

            marks = {}
            for sub in subjects:
                mark_key = f"{sub}_{i}"
                if mark_key not in st.session_state:
                    default_val = st.session_state.student_data[i].get(sub, int(max_marks/2)) if i < len(st.session_state.student_data) else int(max_marks/2)
                    st.session_state[mark_key] = default_val
                marks[sub] = st.number_input(f"{sub} marks", 0, max_marks, value=st.session_state[mark_key], key=f"{sub}_input_{i}")
                st.session_state[mark_key] = marks[sub]

            student_data.append({"Name": name if name else f"Student {i+1}", **marks})

    # compute results table
    df = pd.DataFrame(student_data)
    if not df.empty:
        df[subjects] = df[subjects].apply(pd.to_numeric, errors="coerce").fillna(0)
    df["Total"] = df[subjects].sum(axis=1)
    df["Average"] = df[subjects].mean(axis=1)
    df["Rank"] = df["Total"].rank(ascending=False, method="min").astype(int)

    st.header("Step 2: Results Table")
    st.dataframe(df.style.background_gradient(cmap="Blues"))

    # topper
    if not df.empty:
        topper = df.loc[df["Total"].idxmax()]
        st.subheader("🏆 Topper")
        st.success(f"{topper['Name']} with {int(topper['Total'])} marks (Avg: {topper['Average']:.1f})")

    # charts
    st.header("Step 3: Visualize Data")
    chart_type = st.radio("Select chart type", ["Bar", "Line", "Radar"])
    if chart_type == "Bar":
        fig = px.bar(df, x="Name", y=subjects, barmode="group", template=PLOTLY_THEME, title="Marks Comparison")
    elif chart_type == "Line":
        fig = px.line(df, x="Name", y=subjects, markers=True, template=PLOTLY_THEME, title="Trend Across Subjects")
    else:
        melted = df.melt(id_vars=["Name"], value_vars=subjects, var_name="Subject", value_name="Marks")
        fig = px.line_polar(melted, r="Marks", theta="Subject", color="Name", line_close=True, template=PLOTLY_THEME, title="Radar Chart")
    st.plotly_chart(fig, use_container_width=True)

    # weak subjects
    st.header("Step 4: Insights")
    weak_subjects = {sub: df[sub].mean() for sub in subjects if df[sub].mean() < max_marks * 0.5} if not df.empty else {}
    if weak_subjects:
        for sub, avg in weak_subjects.items():
            st.warning(f"{sub} is weak on average: {avg:.1f}")
    else:
        st.success("No weak subjects detected (averages >= 50%)" if not df.empty else "Enter data to see insights.")

    # Save to Google Sheets
    if st.button("💾 Save Today's Results"):
        today = datetime.date.today().isoformat()
        df_copy = df.copy()
        df_copy.insert(0, "Date", today)
        rows_to_append = df_copy[["Date", "Name"] + subjects].values.tolist()

        if sheet:
            wrote = append_rows_to_sheet(sheet, rows_to_append)
            if wrote:
                st.success("Saved to Google Sheet ✅")
            else:
                st.error("Failed to save to Google Sheets")
        else:
            st.error("Google Sheets not connected. Cannot save data.")

        # Clear session_state after saving
        for i in range(n):
            st.session_state.pop(f"name_{i}", None)
            for sub in subjects:
                st.session_state.pop(f"{sub}_{i}", None)

    # download current results as CSV
    st.download_button("📥 Download Results as CSV", df.to_csv(index=False), "student_results.csv", "text/csv")

# ------------------------------
# Progress page
# ------------------------------
elif page == "Progress":
    st.title("📅 Progress Tracker")
    # read history from Google Sheets
    if sheet:
        history_df = read_history_from_sheet(sheet)
    else:
        history_df = pd.DataFrame(columns=["Date", "Name"] + subjects)

    if history_df.empty:
        st.warning("No progress saved yet. Go to Visualizer and save today's results.")
    else:
        # ensure presence of subject columns and numeric
        for sub in subjects:
            if sub not in history_df.columns:
                history_df[sub] = 0
        history_df[subjects] = history_df[subjects].apply(pd.to_numeric, errors="coerce").fillna(0)

        # compute totals/averages if missing
        if "Total" not in history_df.columns:
            history_df["Total"] = history_df[subjects].sum(axis=1)
        if "Average" not in history_df.columns:
            history_df["Average"] = history_df[subjects].mean(axis=1)

        st.write("### Saved Progress History")
        st.dataframe(history_df)

        history_df["Average"] = pd.to_numeric(history_df["Average"], errors="coerce")
        avg_progress = history_df.groupby("Date", as_index=False)["Average"].mean()

        fig_avg = px.line(avg_progress, x="Date", y="Average", markers=True, title="Average Performance Over Time", template=PLOTLY_THEME)
        st.plotly_chart(fig_avg, use_container_width=True)

        history_df["Total"] = pd.to_numeric(history_df["Total"], errors="coerce")
        topper_progress = history_df.groupby("Date", as_index=False)["Total"].max()

        fig_topper = px.line(topper_progress, x="Date", y="Total", markers=True, title="Topper's Total Over Time", template=PLOTLY_THEME)
        st.plotly_chart(fig_topper, use_container_width=True)

        st.subheader("📌 Track Individual Student")
        student_choice = st.selectbox("Select Student", history_df["Name"].unique())
        student_hist = history_df[history_df["Name"] == student_choice]
        if not student_hist.empty:
            fig_student = px.line(student_hist, x="Date", y="Total", markers=True, title=f"{student_choice}'s Total Marks Over Time", template=PLOTLY_THEME)
            st.plotly_chart(fig_student, use_container_width=True)
        else:
            st.info("No data for this student yet.")

# ------------------------------
# About page
# ------------------------------
else:
    st.title("ℹ️ About MarkSense")
    st.write("""
    MarkSense - student marks visualizer.
    - Persistent inputs while you edit
    - Save to Google Sheets
    - Load last saved data
    - Clear inputs and download CSV
    - Explore trends and insights
    """)
