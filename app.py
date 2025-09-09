import streamlit as st
import pandas as pd
import plotly.express as px
import os
import datetime

# ------------------------------
# 🎯 App Config & Theme
# ------------------------------
st.set_page_config(page_title="MarkSense", layout="wide")

PLOTLY_THEME = "plotly_white"  # light theme for charts
DATA_FILE = "progress_history.csv"

# ------------------------------
# 🎯 Sidebar Navigation
# ------------------------------
page = st.sidebar.radio("📍 Navigate", ["Home", "Visualizer", "Progress", "About"])

# ------------------------------
# 🎯 Home Page
# ------------------------------
if page == "Home":
    st.title("📘 MarkSense")
    st.subheader("Smart Student Marks Visualizer")
    st.write("Track performance daily with interactive charts and topper analysis.")

    with st.expander("ℹ️ About this App"):
        st.write("""
        **MarkSense** helps students and teachers track performance daily in a fun and interactive way.

        🔹 Enter marks subject-wise  
        🔹 Get instant ranks, averages, and toppers  
        🔹 Visualize performance with interactive charts  
        🔹 Play with scores using the What-if slider  
        🔹 Save daily results and track progress over time  
        🔹 Export results for later use  

        Designed for daily use to keep learning progress transparent and motivating.
        """)

# ------------------------------
# 🎯 Visualizer Page
# ------------------------------
elif page == "Visualizer":
    st.title("📊 Student Marks Visualizer")
    st.write("Analyze marks with charts, topper analysis, and What-if predictions.")

    # Settings
    st.sidebar.header("⚙️ Settings")
    subjects = ["Maths", "Science", "English", "History", "Computer"]
    max_marks = st.sidebar.number_input("Maximum Marks per Subject", min_value=10, max_value=500, value=100)
    n = st.sidebar.number_input("Number of Students", min_value=1, max_value=50, value=3)

    # Data Input
    st.header("Step 1: Enter Students Data")
    student_data = []
    cols = st.columns(2)
    for i in range(n):
        with cols[i % 2]:
            st.subheader(f"Student {i+1}")
            name = st.text_input(f"Enter name of student {i+1}", key=f"name{i}")
            marks = {}
            for sub in subjects:
                mark = st.number_input(
                    f"{sub} marks (out of {max_marks}) for {name if name else f'Student {i+1}'}",
                    min_value=0, max_value=max_marks, value=int(max_marks/2), key=f"{sub}_{i}"
                )
                marks[sub] = mark
            student_data.append({"Name": name if name else f"Student {i+1}", **marks})

    # Convert to DataFrame
    df = pd.DataFrame(student_data)
    df["Total"] = df[subjects].sum(axis=1)
    df["Average"] = df[subjects].mean(axis=1)
    df["Rank"] = df["Total"].rank(ascending=False, method="min").astype(int)

    # Display Table
    st.header("Step 2: Results Table")
    st.dataframe(df.style.background_gradient(cmap="Blues"))

    # Topper Highlight
    topper = df.loc[df["Total"].idxmax()]
    with st.container():
        st.subheader("🏆 Topper")
        st.success(f"{topper['Name']} with {topper['Total']} marks (Avg: {topper['Average']:.1f})")

    # Visualizations
    st.header("Step 3: Visualize Data")
    chart_type = st.radio("Select chart type", ["Bar", "Line", "Radar"])

    if chart_type == "Bar":
        fig = px.bar(df, x="Name", y=subjects, title="Marks Comparison", barmode="group", template=PLOTLY_THEME)
    elif chart_type == "Line":
        fig = px.line(df, x="Name", y=subjects, markers=True, title="Trend Across Subjects", template=PLOTLY_THEME)
    else:
        melted = df.melt(id_vars=["Name"], value_vars=subjects, var_name="Subject", value_name="Marks")
        fig = px.line_polar(melted, r="Marks", theta="Subject", color="Name", line_close=True, title="Radar Chart", template=PLOTLY_THEME)

    st.plotly_chart(fig, use_container_width=True)

    # What-if Analysis
    st.header("Step 4: What-if Analysis")
    student_choice = st.selectbox("Select student to adjust marks", df["Name"])
    student_row = df[df["Name"] == student_choice].iloc[0]

    what_if_marks = {}
    for sub in subjects:
        what_if_marks[sub] = st.slider(f"Adjust {sub} marks (out of {max_marks})", 0, max_marks, int(student_row[sub]))

    new_total = sum(what_if_marks.values())
    new_avg = new_total / len(subjects)
    st.info(f"If {student_choice}'s marks are adjusted: Total = {new_total}, Average = {new_avg:.1f}")

    # Save Daily Progress
    if st.button("💾 Save Today's Results"):
        today = datetime.date.today().isoformat()
        df_copy = df.copy()
        df_copy.insert(0, "Date", today)

        if os.path.exists(DATA_FILE):
            df_copy.to_csv(DATA_FILE, mode='a', header=False, index=False)
        else:
            df_copy.to_csv(DATA_FILE, index=False)
        st.success("Today's results saved to progress history ✅")

    # Download Option
    st.download_button("📥 Download Results as CSV", df.to_csv(index=False), "student_results.csv", "text/csv")

# ------------------------------
# 🎯 Progress Page
# ------------------------------
elif page == "Progress":
    st.title("📅 Progress Tracker")
    if os.path.exists(DATA_FILE):
        history_df = pd.read_csv(DATA_FILE)
        st.write("### Saved Progress History")
        st.dataframe(history_df)

        # Plot Progress Over Time
        avg_progress = history_df.groupby("Date")["Average"].mean().reset_index()
        fig = px.line(avg_progress, x="Date", y="Average", markers=True, title="Average Performance Over Time", template=PLOTLY_THEME)
        st.plotly_chart(fig, use_container_width=True)

        topper_progress = history_df.groupby("Date")["Total"].max().reset_index()
        fig2 = px.line(topper_progress, x="Date", y="Total", markers=True, title="Topper's Total Over Time", template=PLOTLY_THEME)
        st.plotly_chart(fig2, use_container_width=True)
    else:
        st.warning("No progress saved yet. Go to Visualizer and save today's results.")

# ------------------------------
# 🎯 About Page
# ------------------------------
else:
    st.title("ℹ️ About MarkSense")
    st.write("""
    **MarkSense** is built to make student performance tracking simple and engaging.

    ### Features
    - Enter marks for multiple students and subjects
    - Get automatic totals, averages, and ranks
    - See topper highlights instantly
    - Visualize data with interactive charts (Bar, Line, Radar)
    - Experiment with scores using the What-if analysis
    - Save results daily and view progress trends
    - Export results as CSV for offline use

    ### Ideal Users
    - Teachers tracking class performance
    - Students comparing progress with peers
    - Parents monitoring study outcomes

    **Created with ❤️ using Streamlit & Plotly**
    """)
