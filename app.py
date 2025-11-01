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
GSHEET_NAME = "MarkSenseHistory"
SERVICE_ACCOUNT_FILE = "service_account.json"
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
        
        # Ensure all required columns exist
        for c in ["Date", "Name"] + subjects + ["Total", "Average", "Rank"]:
            if c not in df.columns:
                df[c] = None
        
        # Convert numeric columns, replacing empty strings with NaN first
        for col in subjects + ["Total", "Average", "Rank"]:
            if col in df.columns:
                # Replace empty strings with NaN
                df[col] = df[col].replace('', None)
                df[col] = pd.to_numeric(df[col], errors="coerce")
        
        return df[["Date", "Name"] + subjects + ["Total", "Average", "Rank"]]
    except Exception as e:
        st.warning("Failed reading sheet: " + str(e))
        return pd.DataFrame(columns=["Date", "Name"] + subjects + ["Total", "Average", "Rank"])

def append_rows_to_sheet(sheet, df_rows):
    """Append rows to the sheet."""
    try:
        for row in df_rows:
            sheet.append_row(row)
        return True
    except Exception as e:
        st.warning("Failed writing to Google Sheet: " + str(e))
        return False

def update_or_append_rows(sheet, new_data_df, date_to_update):
    """Update existing rows for a date or append new ones."""
    try:
        # Get all existing data
        all_data = sheet.get_all_values()
        if len(all_data) <= 1:  # Only header or empty
            # Just append
            rows_to_append = new_data_df.values.tolist()
            for row in rows_to_append:
                sheet.append_row(row)
            return True
        
        # Find rows to update
        header = all_data[0]
        data_rows = all_data[1:]
        
        # Build a dict of existing data by date and name
        existing_indices = {}
        for idx, row in enumerate(data_rows, start=2):  # start=2 because row 1 is header
            if len(row) > 1:  # Ensure row has at least Date and Name
                row_date = row[0]
                row_name = row[1]
                if row_date == date_to_update:
                    existing_indices[(row_date, row_name)] = idx
        
        # Process new data
        rows_to_append = []
        for _, new_row in new_data_df.iterrows():
            new_date = new_row['Date']
            new_name = new_row['Name']
            key = (new_date, new_name)
            
            if key in existing_indices:
                # Update existing row
                row_idx = existing_indices[key]
                row_values = new_row.tolist()
                for col_idx, value in enumerate(row_values, start=1):
                    sheet.update_cell(row_idx, col_idx, value)
            else:
                # Append new row
                rows_to_append.append(new_row.tolist())
        
        # Append any completely new rows
        if rows_to_append:
            for row in rows_to_append:
                sheet.append_row(row)
        
        return True
    except Exception as e:
        st.warning("Failed updating Google Sheet: " + str(e))
        return False

# Connect once
sheet = connect_sheets()

# ------------------------------
# Session state initialization
# ------------------------------
if "page" not in st.session_state:
    st.session_state.page = "Home"
if "student_data" not in st.session_state:
    st.session_state.student_data = []
if "max_marks" not in st.session_state:
    st.session_state.max_marks = 100
if "num_students" not in st.session_state:
    st.session_state.num_students = 3

# ------------------------------
# Sidebar navigation + state
# ------------------------------
page = st.sidebar.radio("📍 Navigate", ["Home", "Visualizer", "Progress", "About"],
                        index=["Home", "Visualizer", "Progress", "About"].index(st.session_state.page))
st.session_state.page = page

# ------------------------------
# Home page
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

    if sheet:
        history_df = read_history_from_sheet(sheet)
    else:
        history_df = pd.DataFrame(columns=["Date", "Name"] + subjects + ["Total", "Average", "Rank"])

    if not history_df.empty:
        for sub in subjects:
            if sub not in history_df.columns:
                history_df[sub] = 0
        
        # Convert all numeric columns properly - but preserve existing values
        for col in subjects + ["Total", "Average", "Rank"]:
            if col in history_df.columns:
                history_df[col] = pd.to_numeric(history_df[col], errors="coerce")
        
        # Only fill NaN, don't replace all zeros
        history_df = history_df.fillna(0)

        st.markdown("---")
        st.subheader("📅 Select Date to View")
        available_dates = sorted(history_df['Date'].unique(), reverse=True)
        selected_date = st.selectbox("Choose a date:", available_dates, index=0)
        
        latest_data = history_df[history_df['Date'] == selected_date]

        if not latest_data.empty:
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

            st.markdown("---")
            avg_today = latest_data['Average'].mean()
            max_today = latest_data['Total'].max()
            min_today = latest_data['Total'].min()
            
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("📈 Class Average", f"{avg_today:.1f}")
            col2.metric("⭐ Highest Total", f"{int(max_today)}")
            col3.metric("📉 Lowest Total", f"{int(min_today)}")
            col4.metric("👥 Total Students", len(latest_data))

            st.markdown("---")
            st.subheader("📊 Subject-wise Performance")
            
            chart_col1, chart_col2 = st.columns([3, 1])
            
            with chart_col2:
                st.write("**Options:**")
                show_class_avg = st.checkbox("Show Class Average", value=True)
                chart_style = st.radio("Chart Style:", ["Bar", "Line"], index=0, key="home_chart_style")
            
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
                comparison_type = st.radio("Compare by:", ["Total Marks", "Subject-wise"], key="home_comparison")
            
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
                    melted = filtered_students.melt(id_vars=['Name'], 
                                                   value_vars=subjects,
                                                   var_name='Subject', 
                                                   value_name='Marks')
                    fig_compare = px.bar(melted, x='Subject', y='Marks', color='Name',
                                        barmode='group',
                                        title="Subject-wise Comparison",
                                        template=PLOTLY_THEME)
                    st.plotly_chart(fig_compare, use_container_width=True)
                
                st.dataframe(filtered_students[['Name'] + subjects + ['Total', 'Average']]
                           .style.background_gradient(cmap="Blues", subset=subjects),
                           use_container_width=True)

            st.markdown("---")
            st.subheader("📈 Performance Distribution")
            
            dist_col1, dist_col2 = st.columns(2)
            
            with dist_col1:
                fig_hist = px.histogram(latest_data, x='Total', nbins=10,
                                       title="Total Marks Distribution",
                                       template=PLOTLY_THEME,
                                       labels={'Total': 'Total Marks', 'count': 'Number of Students'})
                fig_hist.update_traces(marker_color='lightblue')
                st.plotly_chart(fig_hist, use_container_width=True)
            
            with dist_col2:
                fig_avg_hist = px.histogram(latest_data, x='Average', nbins=10,
                                           title="Average Marks Distribution",
                                           template=PLOTLY_THEME,
                                           labels={'Average': 'Average Marks', 'count': 'Number of Students'})
                fig_avg_hist.update_traces(marker_color='lightgreen')
                st.plotly_chart(fig_avg_hist, use_container_width=True)

            st.markdown("---")
            st.subheader("✨ Student Spotlight")
            
            spotlight_col1, spotlight_col2 = st.columns([1, 3])
            
            with spotlight_col1:
                spotlight_option = st.radio("Show:", 
                                           ["Random Student", "Select Student", "Top Performer", "Needs Improvement"],
                                           key="spotlight_option")
            
            with spotlight_col2:
                if spotlight_option == "Random Student":
                    spotlight_student = latest_data.sample(1).iloc[0]
                elif spotlight_option == "Select Student":
                    selected_name = st.selectbox("Choose student:", latest_data['Name'].unique(), key="spotlight_select")
                    spotlight_student = latest_data[latest_data['Name'] == selected_name].iloc[0]
                elif spotlight_option == "Top Performer":
                    spotlight_student = latest_data.loc[latest_data['Total'].idxmax()]
                else:
                    spotlight_student = latest_data.loc[latest_data['Total'].idxmin()]
                
                st.markdown(f"### 👤 {spotlight_student['Name']}")
                metric_cols = st.columns(3)
                metric_cols[0].metric("Total Marks", int(spotlight_student['Total']))
                metric_cols[1].metric("Average", f"{spotlight_student['Average']:.1f}")
                
                rank = (latest_data['Total'] > spotlight_student['Total']).sum() + 1
                metric_cols[2].metric("Rank", f"#{rank}")
                
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

    st.sidebar.header("⚙️ Settings")
    
    max_marks = st.sidebar.number_input(
        "Maximum Marks per Subject", 10, 500, 
        value=st.session_state.max_marks, key="max_marks_input"
    )
    st.session_state.max_marks = max_marks

    n = st.sidebar.number_input(
        "Number of Students", 1, 100, 
        value=st.session_state.num_students, key="num_students_input"
    )
    st.session_state.num_students = n

    if st.button("🧹 Clear All Inputs"):
        for i in range(st.session_state.num_students):
            st.session_state.pop(f"name_{i}", None)
            for sub in subjects:
                st.session_state.pop(f"{sub}_{i}", None)
        st.session_state.student_data = [{} for _ in range(st.session_state.num_students)]
        st.success("All student inputs cleared.")

    # Initialize student data
    if len(st.session_state.student_data) < n:
        st.session_state.student_data += [{} for _ in range(n - len(st.session_state.student_data))]
    elif len(st.session_state.student_data) > n:
        st.session_state.student_data = st.session_state.student_data[:n]

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
            
            # Convert ALL numeric columns properly - preserve existing values
            for col in subjects + ["Total", "Average", "Rank"]:
                if col in history_df.columns:
                    history_df[col] = pd.to_numeric(history_df[col], errors="coerce")
            
            # Fill NaN only
            history_df = history_df.fillna(0)

            latest_date = history_df["Date"].max()
            latest_data = history_df[history_df["Date"] == latest_date]

            if not latest_data.empty:
                # Reset student data
                st.session_state.student_data = []
                
                # Clear existing session state entries
                for key in list(st.session_state.keys()):
                    if key.startswith("name_") or any(key.startswith(f"{sub}_") for sub in subjects):
                        st.session_state.pop(key, None)

                # Load new data
                for i, (_, student) in enumerate(latest_data.iterrows()):
                    if i >= n:  # Don't exceed current number of students
                        break
                    
                    student_dict = {"Name": student["Name"]}
                    for sub in subjects:
                        student_dict[sub] = int(student[sub]) if pd.notna(student[sub]) else 0
                    
                    st.session_state.student_data.append(student_dict)
                    
                    # Set session state for inputs
                    st.session_state[f"name_{i}"] = student["Name"]
                    for sub in subjects:
                        st.session_state[f"{sub}_{i}"] = int(student[sub]) if pd.notna(student[sub]) else 0

                # Fill remaining slots if needed
                while len(st.session_state.student_data) < n:
                    st.session_state.student_data.append({})

                st.success(f"✅ Loaded last saved data from {latest_date}")
                st.rerun()
            else:
                st.warning("No rows found for latest date.")
        else:
            st.warning("No saved data available.")

    student_data = []
    for i in range(n):
        with st.expander(f"Student {i+1}", expanded=True):
            # Initialize name
            name_key = f"name_{i}"
            if name_key not in st.session_state:
                st.session_state[name_key] = st.session_state.student_data[i].get("Name", f"Student {i+1}") if i < len(st.session_state.student_data) else f"Student {i+1}"
            
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

    # Update session state with current data
    st.session_state.student_data = student_data

    # Create DataFrame
    df = pd.DataFrame(student_data)
    if not df.empty:
        df[subjects] = df[subjects].apply(pd.to_numeric, errors="coerce").fillna(0)
    df["Total"] = df[subjects].sum(axis=1)
    df["Average"] = df[subjects].mean(axis=1)
    df["Rank"] = df["Total"].rank(ascending=False, method="min").astype(int)

    st.header("Step 2: Results Table")
    st.dataframe(df.style.background_gradient(cmap="Blues", subset=subjects+["Total", "Average"]))

    if not df.empty:
        topper = df.loc[df["Total"].idxmax()]
        st.subheader("🏆 Topper")
        st.success(f"{topper['Name']} with {int(topper['Total'])} marks (Avg: {topper['Average']:.1f})")

    st.header("Step 3: Visualize Data")
    chart_type = st.radio("Select chart type", ["Bar", "Line", "Radar"], key="viz_chart_type")
    
    if not df.empty:
        if chart_type == "Bar":
            fig = px.bar(df, x="Name", y=subjects, barmode="group", template=PLOTLY_THEME, title="Marks Comparison")
        elif chart_type == "Line":
            fig = px.line(df, x="Name", y=subjects, markers=True, template=PLOTLY_THEME, title="Trend Across Subjects")
        else:
            melted = df.melt(id_vars=["Name"], value_vars=subjects, var_name="Subject", value_name="Marks")
            fig = px.line_polar(melted, r="Marks", theta="Subject", color="Name", line_close=True, 
                              template=PLOTLY_THEME, title="Radar Chart")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Enter student data to see visualizations")

    st.header("Step 4: Insights")
    if not df.empty:
        weak_subjects = {sub: df[sub].mean() for sub in subjects if df[sub].mean() < max_marks * 0.5}
        if weak_subjects:
            for sub, avg in weak_subjects.items():
                st.warning(f"{sub} is weak on average: {avg:.1f}")
        else:
            st.success("No weak subjects detected (averages >= 50%)")
    else:
        st.info("Enter data to see insights.")

    st.header("Step 5: Save Data")
    if st.button("💾 Save Today's Results", type="primary"):
        today = datetime.date.today().isoformat()
        df_copy = df.copy()
        df_copy.insert(0, "Date", today)

        if sheet:
            success = update_or_append_rows(sheet, df_copy[["Date", "Name"] + subjects + ["Total", "Average", "Rank"]], today)
            if success:
                st.success("✅ Saved/Updated to Google Sheet (with Total, Average, Rank)")
            else:
                st.error("Failed to save to Google Sheets")
        else:
            st.error("Google Sheets not connected. Cannot save data.")

    if not df.empty:
        st.download_button("📥 Download Results as CSV", df.to_csv(index=False), "student_results.csv", "text/csv")

# ------------------------------
# Progress page - FIXED
# ------------------------------
elif page == "Progress":
    st.title("📅 Progress Tracker")
    
    if sheet:
        history_df = read_history_from_sheet(sheet)
    else:
        history_df = pd.DataFrame(columns=["Date", "Name"] + subjects + ["Total", "Average", "Rank"])

    if history_df.empty:
        st.warning("No progress saved yet. Go to Visualizer and save today's results.")
    else:
        for sub in subjects:
            if sub not in history_df.columns:
                history_df[sub] = 0
        
        # Convert ALL numeric columns properly - preserve values
        for col in subjects + ["Total", "Average", "Rank"]:
            if col in history_df.columns:
                history_df[col] = pd.to_numeric(history_df[col], errors="coerce")
        
        # Fill NaN only
        history_df = history_df.fillna(0)

        st.write("### Saved Progress History")
        st.dataframe(history_df, use_container_width=True)

        # Ensure we have valid data for plotting
        if not history_df.empty and 'Date' in history_df.columns and 'Average' in history_df.columns:
            # Group by date for trend analysis
            avg_progress = history_df.groupby("Date", as_index=False)["Average"].mean()
            if not avg_progress.empty:
                fig_avg = px.line(avg_progress, x="Date", y="Average", markers=True, 
                                 title="Average Performance Over Time", template=PLOTLY_THEME)
                st.plotly_chart(fig_avg, use_container_width=True)

            if 'Total' in history_df.columns:
                topper_progress = history_df.groupby("Date", as_index=False)["Total"].max()
                if not topper_progress.empty:
                    fig_topper = px.line(topper_progress, x="Date", y="Total", markers=True, 
                                        title="Topper's Total Over Time", template=PLOTLY_THEME)
                    st.plotly_chart(fig_topper, use_container_width=True)

        st.subheader("📌 Track Individual Student")
        if 'Name' in history_df.columns:
            student_choice = st.selectbox("Select Student", history_df["Name"].unique())
            student_hist = history_df[history_df["Name"] == student_choice]
            if not student_hist.empty and 'Date' in student_hist.columns and 'Total' in student_hist.columns:
                fig_student = px.line(student_hist, x="Date", y="Total", markers=True, 
                                     title=f"{student_choice}'s Total Marks Over Time", template=PLOTLY_THEME)
                st.plotly_chart(fig_student, use_container_width=True)
            else:
                st.info("No complete data for this student yet.")
        else:
            st.info("No student data available")

# ------------------------------
# About page
# ------------------------------
else:
    st.title("ℹ️ About MarkSense")
    st.write("""
    MarkSense - student marks visualizer.
    - Persistent inputs while you edit
    - Save to Google Sheets with update support
    - Load last saved data
    - Clear inputs and download CSV
    - Explore trends and insights
    """)
