import streamlit as st
import pandas as pd
import datetime
import plotly.express as px
import requests
from io import BytesIO
from typing import List, Dict, Optional
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
    WEEKLY_DATA_URL_TEMPLATE: str = "https://www.sirene-diffusion.fr/regia/000-rasff/{}/rasff-{}-{}.xls"

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
        # Standardize and clean necessary columns
        df['date'] = pd.to_datetime(df['Date of Case'], errors='coerce')
        df['Notification From'] = df['Notification From'].apply(self.standardize_country)
        df['Country Origin'] = df['Country Origin'].apply(self.standardize_country)
        df['Hazard Category'] = df['Hazard Category'].fillna("Unknown")
        return df

# Function to download and integrate weekly data starting from November 4, 2024
def download_weekly_data(year: int, weeks: List[int]) -> pd.DataFrame:
    dfs = []
    for week in weeks:
        url = Config.WEEKLY_DATA_URL_TEMPLATE.format(str(year)[2:], year, str(week).zfill(2))
        response = requests.get(url)
        if response.status_code == 200:
            df = pd.read_excel(BytesIO(response.content))
            dfs.append(df)
        else:
            st.error(f"Failed to download data for week {week}.")
    
    if dfs:
        combined_df = pd.concat(dfs, ignore_index=True)
        combined_df = DataStandardizer(notifying_countries, origin_countries).clean_data(combined_df)
        return combined_df
    return pd.DataFrame()  # Return empty if no data

class DataAnalyzer:
    @staticmethod
    def calculate_temporal_trends(df: pd.DataFrame) -> pd.DataFrame:
        temporal_data = df.groupby([pd.Grouper(key='date', freq='M'), 'Hazard Category']).size().reset_index(name='count')
        return temporal_data

    @staticmethod
    def prepare_map_data(df: pd.DataFrame) -> pd.DataFrame:
        return df.groupby('Notification From').size().reset_index(name='count')

class EnhancedRASFFDashboard:
    def __init__(self):
        self.standardizer = DataStandardizer(notifying_countries, origin_countries)
        self.analyzer = DataAnalyzer()

    def render_sidebar(self, df: pd.DataFrame) -> pd.DataFrame:
        st.sidebar.header("Filter Options")

        # Date range slider
        min_date, max_date = df['date'].min(), df['date'].max()
        date_range = st.sidebar.slider("Date Range", min_value=min_date, max_value=max_date, value=(min_date, max_date))
        
        # Filtering
        selected_categories = st.sidebar.multiselect("Product Categories", sorted(df['Product Category'].dropna().unique()))
        selected_issues = st.sidebar.multiselect("Issue Types", sorted(df['Hazard Category'].dropna().unique()))
        selected_countries = st.sidebar.multiselect("Notifying Countries", sorted(df['Notification From'].dropna().unique()))

        filtered_df = df[(df['date'] >= date_range[0]) & (df['date'] <= date_range[1])]
        if selected_categories:
            filtered_df = filtered_df[filtered_df['Product Category'].isin(selected_categories)]
        if selected_issues:
            filtered_df = filtered_df[filtered_df['Hazard Category'].isin(selected_issues)]
        if selected_countries:
            filtered_df = filtered_df[filtered_df['Notification From'].isin(selected_countries)]
        
        return filtered_df

    def render_tabs(self, df: pd.DataFrame):
        tabs = st.tabs(["Overview", "Temporal Trends", "Geographic Analysis", "Risk Matrix"])

        with tabs[0]:
            st.write("### Overview of Notifications")
            st.dataframe(df)
        
        with tabs[1]:
            temporal_data = self.analyzer.calculate_temporal_trends(df)
            fig_trends = px.line(temporal_data, x='date', y='count', color='Hazard Category', title="Temporal Trends by Hazard Category")
            st.plotly_chart(fig_trends)

        with tabs[2]:
            map_data = self.analyzer.prepare_map_data(df)
            fig_map = px.choropleth(map_data, locations='Notification From', locationmode='country names', color='count', title="Geographic Distribution")
            st.plotly_chart(fig_map)

        with tabs[3]:
            risk_matrix = pd.crosstab(df['risk_decision'], df['Hazard Category'])
            fig_matrix = px.imshow(risk_matrix, title="Risk Matrix by Hazard Category", labels=dict(x="Hazard Category", y="Risk Decision", color="Count"))
            st.plotly_chart(fig_matrix)

    async def load_data(self) -> pd.DataFrame:
        try:
            df_main = pd.read_csv(Config.CSV_URL)
            df_main = self.standardizer.clean_data(df_main)

            # Add new weekly data starting from November 2024
            current_year = 2024
            start_week = datetime.datetime(2024, 11, 4).isocalendar()[1]
            current_week = datetime.datetime.now().isocalendar()[1]
            weeks = list(range(start_week, current_week + 1))
            df_weekly = download_weekly_data(current_year, weeks)
            
            if not df_weekly.empty:
                df_combined = pd.concat([df_main, df_weekly], ignore_index=True)
                return df_combined
            return df_main
        except Exception as e:
            st.error(f"Error loading data: {e}")
            return pd.DataFrame()

    async def run(self):
        st.set_page_config(page_title="Enhanced RASFF Dashboard", layout="wide")
        st.title("RASFF Data Dashboard - Enhanced")

        df = await self.load_data()
        
        if not df.empty:
            filtered_df = self.render_sidebar(df)
            self.render_tabs(filtered_df)
        else:
            st.error("No data available. Check the data source or URL.")

if __name__ == "__main__":
    dashboard = EnhancedRASFFDashboard()
    import asyncio
    asyncio.run(dashboard.run())

