import streamlit as st
import pandas as pd
import plotly.express as px
import requests
import io

# Function to load data from GitHub
@st.cache_data
def load_data_from_github():
    url = "https://raw.githubusercontent.com/M00N69/RASFFPORTAL/main/rasff_%202020TO30OCT2024.csv"
    response = requests.get(url)
    if response.status_code == 200:
        df = pd.read_csv(io.StringIO(response.text))
        return df
    else:
        st.error("Failed to load data from GitHub.")
        return pd.DataFrame()

def display_rasff_portal_lab():
    st.title("RASFF Data Analysis Dashboard")

    # Load the data from GitHub
    df = load_data_from_github()

    # Preview the data to debug column names
    if df.empty:
        st.warning("No data available. Please check the data source.")
        return
    
    st.write("Data Preview:")
    st.write(df.head())  # Display the first few rows to verify data

    # Display column names for troubleshooting
    st.write("Column Names:", df.columns.tolist())

    # Check if necessary columns exist
    required_columns = ['Notification From', 'Country Origin', 'GROUPPROD', 'GROUPHAZ', 'PRODCAT', 'HAZCAT', 'Hazard Substance']
    missing_columns = [col for col in required_columns if col not in df.columns]
    if missing_columns:
        st.error(f"Missing columns in the data: {missing_columns}")
        return

    # Sidebar filters (excluding date filters)
    st.sidebar.header("Filters")

    # Notification Country filter
    notification_country = st.sidebar.multiselect("Notification Country", options=df['Notification From'].unique())
    if notification_country:
        df = df[df['Notification From'].isin(notification_country)]

    # Country of Origin filter
    origin_country = st.sidebar.multiselect("Country of Origin", options=df['Country Origin'].unique())
    if origin_country:
        df = df[df['Country Origin'].isin(origin_country)]

    # Group Product filter
    group_prod = st.sidebar.multiselect("Group Product Category", options=df['GROUPPROD'].unique())
    if group_prod:
        df = df[df['GROUPPROD'].isin(group_prod)]

    # Group Hazard filter
    group_haz = st.sidebar.multiselect("Group Hazard Category", options=df['GROUPHAZ'].unique())
    if group_haz:
        df = df[df['GROUPHAZ'].isin(group_haz)]

    # Main dashboard metrics
    st.subheader("Key Statistics")
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Notifications", len(df))
    col2.metric("Unique Product Categories", df['PRODCAT'].nunique())
    col3.metric("Unique Hazard Categories", df['HAZCAT'].nunique())

    st.subheader("Data Visualizations")

    # Notifications by Notification Country
    st.write("### Notifications by Notification Country")
    country_notifications = df['Notification From'].value_counts().reset_index()
    country_notifications.columns = ['Notification Country', 'Count']
    fig_country_notifications = px.bar(country_notifications, x='Notification Country', y='Count', title="Notifications by Country")
    st.plotly_chart(fig_country_notifications, use_container_width=True)

    # Product Categories Distribution
    st.write("### Distribution of Product Categories")
    product_category_count = df['PRODCAT'].value_counts().reset_index()
    product_category_count.columns = ['Product Category', 'Count']
    fig_product_categories = px.pie(product_category_count, names='Product Category', values='Count', title="Product Categories")
    st.plotly_chart(fig_product_categories, use_container_width=True)

    # Hazard Categories Breakdown
    st.write("### Hazard Categories")
    hazard_category_count = df['HAZCAT'].value_counts().reset_index()
    hazard_category_count.columns = ['Hazard Category', 'Count']
    fig_hazard_categories = px.bar(hazard_category_count, x='Hazard Category', y='Count', title="Hazard Categories Breakdown")
    st.plotly_chart(fig_hazard_categories, use_container_width=True)

    # Detailed breakdown for specific categories (drill-down)
    st.write("## Detailed Analysis")

    # Select Group Hazard and Hazard Category for detailed analysis
    selected_group_haz = st.selectbox("Select Group Hazard for Detailed Analysis", options=df['GROUPHAZ'].unique())
    detailed_haz_df = df[df['GROUPHAZ'] == selected_group_haz]
    selected_haz_cat = st.selectbox("Select Hazard Category within Group", options=detailed_haz_df['HAZCAT'].unique())

    # Drill-down into specific hazard substance
    detailed_haz_cat_df = detailed_haz_df[detailed_haz_df['HAZCAT'] == selected_haz_cat]
    hazard_substance_count = detailed_haz_cat_df['Hazard Substance'].value_counts().reset_index()
    hazard_substance_count.columns = ['Hazard Substance', 'Count']
    fig_hazard_substance = px.bar(hazard_substance_count, x='Hazard Substance', y='Count', title=f"Hazard Substances in {selected_haz_cat}")
    st.plotly_chart(fig_hazard_substance, use_container_width=True)
