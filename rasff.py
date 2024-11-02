import streamlit as st
import pandas as pd
import datetime
from typing import List
from io import BytesIO
import requests
import plotly.express as px

# Load lists from external sources
def load_list_from_github(file_name: str) -> List[str]:
    base_url = "https://raw.githubusercontent.com/M00N69/RASFFPORTAL/main/"
    url = f"{base_url}{file_name}"
    response = requests.get(url)
    if response.status_code == 200:
        return response.text.splitlines()
    else:
        st.error(f"Failed to load {file_name} from GitHub.")
        return []

hazard_categories = load_list_from_github("hazard_categories.py")
hazards = load_list_from_github("hazards.py")
notifying_countries = load_list_from_github("notifying_countries.py")
origin_countries = load_list_from_github("origin_countries.py")
product_categories = load_list_from_github("product_categories.py")

class RASFFDashboard:
    def __init__(self):
        self.data = None

    def load_and_clean_data(self, url: str) -> pd.DataFrame:
        # Load the CSV data
        df = pd.read_csv(url)
        
        # Convert 'Date of Case' to datetime with a custom date format
        df['date'] = pd.to_datetime(df['Date of Case'], format='%b %d, %Y', errors='coerce')
        
        # Drop rows with NaT dates
        df = df.dropna(subset=['date'])
        
        # Standardize column names for easier access
        df.columns = [col.lower().replace(" ", "_") for col in df.columns]
        
        # Fill missing values with placeholders to avoid KeyError issues
        df['hazard_substance'].fillna("Unknown", inplace=True)
        df['hazard_category'].fillna("Unknown", inplace=True)
        df['product_category'].fillna("Unknown", inplace=True)
        df['notification_from'].fillna("Unknown", inplace=True)
        df['country_origin'].fillna("Unknown", inplace=True)
        
        return df

    def render_sidebar(self, df: pd.DataFrame) -> pd.DataFrame:
        """Displays the sidebar filters."""
        st.sidebar.header("Filter Options")

        # Set default min_date and max_date
        min_date = df['date'].min()
        max_date = df['date'].max()

        # Date range slider
        date_range = st.sidebar.slider(
            "Date Range",
            min_value=min_date.date(),
            max_value=max_date.date(),
            value=(min_date.date(), max_date.date())
        )

        # Filter by date range
        filtered_df = df[(df['date'] >= pd.to_datetime(date_range[0])) & (df['date'] <= pd.to_datetime(date_range[1]))]

        # Multiselect filters
        selected_categories = st.sidebar.multiselect("Product Categories", sorted(df['product_category'].unique()))
        selected_issues = st.sidebar.multiselect("Issue Types", sorted(df['hazard_category'].unique()))
        selected_countries = st.sidebar.multiselect("Notifying Countries", sorted(df['notification_from'].unique()))

        # Apply additional filters
        if selected_categories:
            filtered_df = filtered_df[filtered_df['product_category'].isin(selected_categories)]
        if selected_issues:
            filtered_df = filtered_df[filtered_df['hazard_category'].isin(selected_issues)]
        if selected_countries:
            filtered_df = filtered_df[filtered_df['notification_from'].isin(selected_countries)]

        return filtered_df

    def display_statistics(self, df: pd.DataFrame):
        st.header("Key Statistics")
        col1, col2, col3 = st.columns(3)
        col1.metric("Total Notifications", len(df))
        col2.metric("Unique Product Categories", df['product_category'].nunique())
        col3.metric("Unique Hazard Categories", df['hazard_category'].nunique())

    def display_visualizations(self, df: pd.DataFrame):
        st.header("Visualizations")

        # Notification distribution by country
        fig_map = px.choropleth(
            df.groupby('notification_from').size().reset_index(name='count'),
            locations='notification_from',
            locationmode='country names',
            color='count',
            title="Notifications by Notifying Country",
            color_continuous_scale='Viridis'
        )
        st.plotly_chart(fig_map)

    async def run(self):
        st.set_page_config(page_title="RASFF Dashboard", layout="wide")
        st.title("RASFF Data Dashboard")

        # Load data
        url = "https://raw.githubusercontent.com/M00N69/RASFFPORTAL/main/rasff_%202020TO30OCT2024.csv"
        df = self.load_and_clean_data(url)

        if df.empty:
            st.error("No data available. Check the data source or URL.")
            return

        # Render filters in the sidebar
        filtered_df = self.render_sidebar(df)

        # Display statistics
        self.display_statistics(filtered_df)

        # Display visualizations
        self.display_visualizations(filtered_df)

# Run the dashboard
if __name__ == "__main__":
    dashboard = RASFFDashboard()
    import asyncio
    asyncio.run(dashboard.run())
