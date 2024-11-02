import streamlit as st
import pandas as pd
import datetime
import plotly.express as px
import requests
from typing import List, Dict
from dataclasses import dataclass

# Define GitHub URLs for loading lists
GITHUB_BASE_URL = "https://raw.githubusercontent.com/M00N69/RASFFPORTAL/main/"

# Load lists dynamically from GitHub
def load_list_from_github(filename: str, file_type: str = "list") -> List:
    url = f"{GITHUB_BASE_URL}{filename}"
    response = requests.get(url)
    if response.status_code == 200:
        if file_type == "list":
            return response.text.splitlines()
        elif file_type == "dict":
            local_dict = {}
            exec(response.text, {}, local_dict)
            return local_dict.get(filename.split('.')[0], {})  # Extract the dictionary by key
    else:
        st.error(f"Failed to load {filename} from GitHub.")
        return []

# Load data from GitHub
notifying_countries = load_list_from_github("notifying_countries.py", file_type="list")
origin_countries = load_list_from_github("origin_countries.py", file_type="list")
hazard_categories = load_list_from_github("hazard_categories.py", file_type="dict")

# Configuration for constants
@dataclass
class Config:
    CSV_URL: str = f"{GITHUB_BASE_URL}rasff_%202020TO30OCT2024.csv"

# Helper class for cleaning and standardizing data
class DataStandardizer:
    def __init__(self, notifying_countries: List[str], origin_countries: List[str]):
        self.notifying_countries = notifying_countries
        self.origin_countries = origin_countries

    def standardize_country(self, country: str) -> str:
        return country if country in self.notifying_countries else "Other"
    
    def standardize_date(self, date):
        if pd.isna(date):
            return pd.NaT
        try:
            return pd.to_datetime(date, errors='coerce')
        except:
            return pd.NaT
    
    def clean_data(self, df: pd.DataFrame) -> pd.DataFrame:
        # Ensure required columns exist
        for col, default in {
            'Hazard Category': 'Unknown',
            'Product Category': 'Unknown',
            'issue_type': 'Unknown',
            'Notification From': 'Unknown',
            'Country Origin': 'Unknown',
            'risk_decision': 'Unknown',
            'date': pd.NaT
        }.items():
            if col not in df.columns:
                df[col] = default

        # Parse and standardize date column
        df['date'] = pd.to_datetime(df['Date of Case'], errors='coerce')
        return df

class DataAnalyzer:
    @staticmethod
    def calculate_temporal_trends(df: pd.DataFrame) -> pd.DataFrame:
        """Analyze notifications trends over time."""
        temporal_data = df.groupby([pd.Grouper(key='date', freq='M'), 'Hazard Category']).size().reset_index(name='count')
        return temporal_data

    @staticmethod
    def prepare_map_data(df: pd.DataFrame) -> pd.DataFrame:
        """Prepare data for geographic visualization."""
        return df.groupby('Notification From').size().reset_index(name='count')

class EnhancedRASFFDashboard:
    def __init__(self):
        self.standardizer = DataStandardizer(notifying_countries, origin_countries)
        self.analyzer = DataAnalyzer()

    def render_sidebar(self, df: pd.DataFrame):
        """Displays the sidebar filters and instructions."""
        st.sidebar.header("Filter Options")
        
        # Ensure valid date range for slider
        if not df['date'].isna().all():
            min_date, max_date = df['date'].min(), df['date'].max()
            date_range = st.sidebar.slider(
                "Date Range", 
                min_value=min_date.date() if min_date else datetime.date(2020, 1, 1),
                max_value=max_date.date() if max_date else datetime.date.today(),
                value=(min_date.date() if min_date else datetime.date(2020, 1, 1), 
                       max_date.date() if max_date else datetime.date.today())
            )
        else:
            st.sidebar.error("No valid date information available in data.")
            return df
        
        # Category filters
        selected_categories = st.sidebar.multiselect("Product Categories", sorted(df['Product Category'].unique()))
        selected_issues = st.sidebar.multiselect("Issue Types", sorted(df['Hazard Category'].unique()))
        selected_countries = st.sidebar.multiselect("Notifying Countries", sorted(df['Notification From'].unique()))
        
        # Apply filters
        filtered_df = df[(df['date'] >= pd.to_datetime(date_range[0])) & (df['date'] <= pd.to_datetime(date_range[1]))]
        if selected_categories:
            filtered_df = filtered_df[filtered_df['Product Category'].isin(selected_categories)]
        if selected_issues:
            filtered_df = filtered_df[filtered_df['Hazard Category'].isin(selected_issues)]
        if selected_countries:
            filtered_df = filtered_df[filtered_df['Notification From'].isin(selected_countries)]
        
        # Instructions expander
        with st.sidebar.expander("Instructions"):
            st.write("""
                - Use the filters above to refine data by date, category, and country.
                - View various charts and trends by switching tabs.
                - The 'Risk Matrix' shows the relationship between issue types and risk decisions.
            """)
        
        return filtered_df

    def render_tabs(self, df: pd.DataFrame):
        """Displays the main content tabs with visualizations."""
        tabs = st.tabs(["Overview", "Temporal Trends", "Geographic Analysis", "Risk Matrix"])

        with tabs[0]:
            st.write("### Overview of Notifications")
            st.dataframe(df)
        
        with tabs[1]:
            # Temporal trend analysis
            temporal_data = self.analyzer.calculate_temporal_trends(df)
            fig_trends = px.line(temporal_data, x='date', y='count', color='Hazard Category', title="Temporal Trends by Hazard Category")
            st.plotly_chart(fig_trends)

        with tabs[2]:
            # Geographic distribution map
            map_data = self.analyzer.prepare_map_data(df)
            fig_map = px.choropleth(map_data, locations='Notification From', locationmode='country names', color='count', title="Geographic Distribution")
            st.plotly_chart(fig_map)

        with tabs[3]:
            # Risk matrix heatmap
            risk_matrix = pd.crosstab(df['risk_decision'], df['Hazard Category'])
            fig_matrix = px.imshow(risk_matrix, title="Risk Matrix by Hazard Category", labels=dict(x="Hazard Category", y="Risk Decision", color="Count"))
            st.plotly_chart(fig_matrix)

    async def load_data(self):
        """Loads data from the remote URL and preprocesses it."""
        try:
            # Load initial data
            df = pd.read_csv(Config.CSV_URL)
            # Clean and standardize data
            df = self.standardizer.clean_data(df)
            return df
        except Exception as e:
            st.error(f"Error loading data: {e}")
            return pd.DataFrame()

    async def run(self):
        st.set_page_config(page_title="Enhanced RASFF Dashboard", layout="wide")
        st.title("RASFF Data Dashboard - Enhanced")

        # Load and preprocess data
        df = await self.load_data()
        
        if not df.empty:
            # Render sidebar filters and apply them to the data
            filtered_df = self.render_sidebar(df)
            
            # Render main content tabs with filtered data
            self.render_tabs(filtered_df)
        else:
            st.error("No data available. Check the data source or URL.")

if __name__ == "__main__":
    dashboard = EnhancedRASFFDashboard()
    import asyncio
    asyncio.run(dashboard.run())

