import streamlit as st
import pandas as pd
import plotly.express as px
import requests
from io import BytesIO
from datetime import datetime

# Load the main CSV data from GitHub
@st.cache_data
def load_data(url: str) -> pd.DataFrame:
    try:
        df = pd.read_csv(url, parse_dates=['Date of Case'])
        df.columns = [col.strip().replace(" ", "_").lower() for col in df.columns]  # Standardize column names
        return df
    except Exception as e:
        st.error(f"Failed to load data: {e}")
        return pd.DataFrame()

# Simple function to clean the data and fill missing values if needed
def clean_data(df: pd.DataFrame) -> pd.DataFrame:
    df = df.dropna(subset=['date_of_case'])
    df['date_of_case'] = pd.to_datetime(df['date_of_case'], errors='coerce')
    df = df.dropna(subset=['date_of_case'])  # Drop any rows with null dates after conversion
    return df

# Main class for the RASFF Dashboard
class RASFFDashboard:
    def __init__(self, url: str):
        self.data = clean_data(load_data(url))

    def render_sidebar(self, df: pd.DataFrame) -> pd.DataFrame:
        st.sidebar.header("Filter Options")

        # Date range filter
        min_date = df['date_of_case'].min().date()  # Convert to datetime.date
        max_date = df['date_of_case'].max().date()  # Convert to datetime.date
        date_range = st.sidebar.slider(
            "Date Range", 
            min_value=min_date, 
            max_value=max_date, 
            value=(min_date, max_date),
            format="%Y-%m-%d"  # Use the correct date format
        )
        filtered_df = df[(df['date_of_case'] >= pd.to_datetime(date_range[0])) & (df['date_of_case'] <= pd.to_datetime(date_range[1]))]

        # Multiselect filters
        selected_categories = st.sidebar.multiselect("Product Categories", sorted(df['product_category'].dropna().unique()))
        selected_hazards = st.sidebar.multiselect("Hazard Categories", sorted(df['hazard_category'].dropna().unique()))
        selected_notifying_countries = st.sidebar.multiselect("Notifying Countries", sorted(df['notification_from'].dropna().unique()))
        selected_origin_countries = st.sidebar.multiselect("Country of Origin", sorted(df['country_origin'].dropna().unique()))

        # Apply filters
        if selected_categories:
            filtered_df = filtered_df[filtered_df['product_category'].isin(selected_categories)]
        if selected_hazards:
            filtered_df = filtered_df[filtered_df['hazard_category'].isin(selected_hazards)]
        if selected_notifying_countries:
            filtered_df = filtered_df[filtered_df['notification_from'].isin(selected_notifying_countries)]
        if selected_origin_countries:
            filtered_df = filtered_df[filtered_df['country_origin'].isin(selected_origin_countries)]

        return filtered_df

    def display_statistics(self, df: pd.DataFrame):
        st.header("Key Statistics")
        col1, col2, col3 = st.columns(3)
        col1.metric("Total Notifications", len(df))
        col2.metric("Unique Product Categories", df['product_category'].nunique())
        col3.metric("Unique Hazard Categories", df['hazard_category'].nunique())

    def display_visualizations(self, df: pd.DataFrame):
        st.header("Visualizations")

        # European Map for Notifying Countries
        fig_notifying_map = px.choropleth(
            df.groupby('notification_from').size().reset_index(name='count'),
            locations='notification_from',
            locationmode='country names',
            color='count',
            scope="europe",
            title="European Map of Notifying Countries",
            color_continuous_scale='Blues'
        )
        st.plotly_chart(fig_notifying_map)

        # World Map for Origin Countries
        fig_origin_map = px.choropleth(
            df.groupby('country_origin').size().reset_index(name='count'),
            locations='country_origin',
            locationmode='country names',
            color='count',
            title="World Map of Origin Countries",
            color_continuous_scale='Reds'
        )
        st.plotly_chart(fig_origin_map)

        # Bar Chart for Product Categories
        product_counts = df['product_category'].value_counts().head(10)
        fig_bar = px.bar(product_counts, x=product_counts.index, y=product_counts.values, title="Top Product Categories")
        st.plotly_chart(fig_bar)

        # Pie Chart for Top Hazard Categories
        hazard_counts = df['hazard_category'].value_counts().head(10)
        fig_pie = px.pie(hazard_counts, values=hazard_counts.values, names=hazard_counts.index, title="Top 10 Hazard Categories")
        st.plotly_chart(fig_pie)

    def run(self):
        st.title("RASFF Data Dashboard")

        # Sidebar filters
        filtered_df = self.render_sidebar(self.data)

        # Display statistics
        self.display_statistics(filtered_df)

        # Display visualizations
        self.display_visualizations(filtered_df)

# Run the dashboard
if __name__ == "__main__":
    st.set_page_config(page_title="RASFF Data Dashboard", layout="wide")  # Ensure this is the first Streamlit command
    dashboard = RASFFDashboard(url="https://raw.githubusercontent.com/M00N69/RASFFPORTAL/main/rasff_%202020TO30OCT2024.csv")
    dashboard.run()
