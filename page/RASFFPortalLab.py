import streamlit as st
import pandas as pd
import plotly.express as px

# Set up the Streamlit page at the start
st.set_page_config(page_title="RASFF Data Analysis", layout="wide")

st.title("RASFF Data Analysis Dashboard")

# Upload CSV File
uploaded_file = st.file_uploader("Upload your CSV file", type="csv")

if uploaded_file:
    # Load the CSV data
    df = pd.read_csv(uploaded_file)
    # Standardize column names for easier access
    df.columns = [col.strip().replace(" ", "_").lower() for col in df.columns]
    
    # Check if necessary columns exist to avoid KeyErrors
    required_columns = {'notification_from', 'country_origin', 'groupprod', 'grouphaz', 'prodcat', 'hazcat', 'hazard_substance'}
    if not required_columns.issubset(df.columns):
        st.error(f"The uploaded file is missing required columns: {required_columns - set(df.columns)}")
    else:
        # Sidebar filters (excluding date filters)
        st.sidebar.header("Filters")

        # Notification Country filter
        notification_country = st.sidebar.multiselect(
            "Notification Country", options=df['notification_from'].unique()
        )
        if notification_country:
            df = df[df['notification_from'].isin(notification_country)]

        # Country of Origin filter
        origin_country = st.sidebar.multiselect(
            "Country of Origin", options=df['country_origin'].unique()
        )
        if origin_country:
            df = df[df['country_origin'].isin(origin_country)]

        # Group Product filter
        group_prod = st.sidebar.multiselect(
            "Group Product Category", options=df['groupprod'].unique()
        )
        if group_prod:
            df = df[df['groupprod'].isin(group_prod)]

        # Group Hazard filter
        group_haz = st.sidebar.multiselect(
            "Group Hazard Category", options=df['grouphaz'].unique()
        )
        if group_haz:
            df = df[df['grouphaz'].isin(group_haz)]

        # Main dashboard metrics
        st.subheader("Key Statistics")
        col1, col2, col3 = st.columns(3)
        col1.metric("Total Notifications", len(df))
        col2.metric("Unique Product Categories", df['prodcat'].nunique())
        col3.metric("Unique Hazard Categories", df['hazcat'].nunique())

        st.subheader("Data Visualizations")

        # Notifications by Notification Country
        st.write("### Notifications by Notification Country")
        country_notifications = df['notification_from'].value_counts().reset_index()
        country_notifications.columns = ['Notification Country', 'Count']
        fig_country_notifications = px.bar(
            country_notifications, x='Notification Country', y='Count', title="Notifications by Country"
        )
        st.plotly_chart(fig_country_notifications, use_container_width=True)

        # Product Categories Distribution
        st.write("### Distribution of Product Categories")
        product_category_count = df['prodcat'].value_counts().reset_index()
        product_category_count.columns = ['Product Category', 'Count']
        fig_product_categories = px.pie(
            product_category_count, names='Product Category', values='Count', title="Product Categories"
        )
        st.plotly_chart(fig_product_categories, use_container_width=True)

        # Hazard Categories Breakdown
        st.write("### Hazard Categories")
        hazard_category_count = df['hazcat'].value_counts().reset_index()
        hazard_category_count.columns = ['Hazard Category', 'Count']
        fig_hazard_categories = px.bar(
            hazard_category_count, x='Hazard Category', y='Count', title="Hazard Categories Breakdown"
        )
        st.plotly_chart(fig_hazard_categories, use_container_width=True)

        # Detailed breakdown for specific categories (drill-down)
        st.write("## Detailed Analysis")

        # Select Group Hazard and Hazard Category for detailed analysis
        selected_group_haz = st.selectbox(
            "Select Group Hazard for Detailed Analysis", options=df['grouphaz'].unique()
        )
        detailed_haz_df = df[df['grouphaz'] == selected_group_haz]
        selected_haz_cat = st.selectbox(
            "Select Hazard Category within Group", options=detailed_haz_df['hazcat'].unique()
        )

        # Drill-down into specific hazard substance
        detailed_haz_cat_df = detailed_haz_df[detailed_haz_df['hazcat'] == selected_haz_cat]
        hazard_substance_count = detailed_haz_cat_df['hazard_substance'].value_counts().reset_index()
        hazard_substance_count.columns = ['Hazard Substance', 'Count']
        fig_hazard_substance = px.bar(
            hazard_substance_count, x='Hazard Substance', y='Count', title=f"Hazard Substances in {selected_haz_cat}"
        )
        st.plotly_chart(fig_hazard_substance, use_container_width=True)

else:
    st.info("Please upload a CSV file to proceed.")