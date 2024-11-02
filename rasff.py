import streamlit as st
import pandas as pd
import datetime
import plotly.express as px
from typing import List
from dataclasses import dataclass
import httpx
from io import BytesIO

# Import local data files for hazards and categories
from hazard_categories import hazard_categories
from hazards import hazards
from notifying_countries import notifying_countries
from origin_countries import origin_countries
from product_categories import product_categories

# Configuration for constants
@dataclass
class Config:
    URL_TEMPLATE: str = "https://www.sirene-diffusion.fr/regia/000-rasff/{}/rasff-{}-{}.xls"
    MAX_LEVENSHTEIN_DISTANCE: int = 3
    CSV_URL: str = "https://raw.githubusercontent.com/M00N69/RASFFPORTAL/refs/heads/main/rasff_%202020TO30OCT2024.csv"

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
        df = df.drop(columns=['Unnamed: 0'], errors='ignore')
        
        # Standardize country columns
        if 'notifying_country' in df.columns:
            df['notifying_country'] = df['notifying_country'].apply(self.standardize_country)
        if 'origin' in df.columns:
            df['origin'] = df['origin'].apply(self.standardize_country)
        
        # Parse and standardize date column
        if 'date' in df.columns:
            df['date'] = df['date'].apply(self.standardize_date)
        
        # Fill missing values in key columns
        df['hazard_category'].fillna("Unknown", inplace=True)
        df['Product Category'].fillna("Unknown", inplace=True)
        
        return df
class DataAnalyzer:
    @staticmethod
    def calculate_temporal_trends(df: pd.DataFrame) -> pd.DataFrame:
        """Analyze notifications trends over time."""
        temporal_data = df.groupby([pd.Grouper(key='date', freq='M'), 'issue_type']).size().reset_index(name='count')
        return temporal_data

    @staticmethod
    def prepare_map_data(df: pd.DataFrame) -> pd.DataFrame:
        """Prepare data for geographic visualization."""
        return df.groupby('notifying_country').size().reset_index(name='count')
class EnhancedRASFFDashboard:
    def __init__(self):
        self.standardizer = DataStandardizer(notifying_countries, origin_countries)
        self.analyzer = DataAnalyzer()

    def render_sidebar(self, df: pd.DataFrame):
        """Displays the sidebar filters and instructions."""
        st.sidebar.header("Filter Options")
        
        # Date range filter
        min_date, max_date = df['date'].min(), df['date'].max()
        date_range = st.sidebar.slider("Date Range", min_value=min_date, max_value=max_date, value=(min_date, max_date))
        
        # Category filters
        selected_categories = st.sidebar.multiselect("Product Categories", sorted(df['Product Category'].unique()))
        selected_issues = st.sidebar.multiselect("Issue Types", sorted(df['issue_type'].unique()))
        selected_countries = st.sidebar.multiselect("Notifying Countries", sorted(df['notifying_country'].unique()))
        
        # Apply filters
        filtered_df = df[(df['date'] >= date_range[0]) & (df['date'] <= date_range[1])]
        if selected_categories:
            filtered_df = filtered_df[filtered_df['Product Category'].isin(selected_categories)]
        if selected_issues:
            filtered_df = filtered_df[filtered_df['issue_type'].isin(selected_issues)]
        if selected_countries:
            filtered_df = filtered_df[filtered_df['notifying_country'].isin(selected_countries)]
        
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
            fig_trends = px.line(temporal_data, x='date', y='count', color='issue_type', title="Temporal Trends by Issue Type")
            st.plotly_chart(fig_trends)

        with tabs[2]:
            # Geographic distribution map
            map_data = self.analyzer.prepare_map_data(df)
            fig_map = px.choropleth(map_data, locations='notifying_country', locationmode='country names', color='count', title="Geographic Distribution")
            st.plotly_chart(fig_map)

        with tabs[3]:
            # Risk matrix heatmap
            risk_matrix = pd.crosstab(df['risk_decision'], df['issue_type'])
            fig_matrix = px.imshow(risk_matrix, title="Risk Matrix by Issue Type", labels=dict(x="Issue Type", y="Risk Decision", color="Count"))
            st.plotly_chart(fig_matrix)

    async def load_data(self):
        """Loads data from the remote URL and preprocesses it."""
        try:
            # Load initial data
            df = pd.read_csv(Config.CSV_URL)
            df = self.standardizer.clean_data(df)
            return df
        except Exception as e:
            st.error(f"Error loading data: {e}")
            return pd.DataFrame()

    async def run(self):
        st.set_page_config(page_title="Enhanced RASFF Dashboard", layout="wide")
        st.title("RASFF Data Dashboard")
        
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
