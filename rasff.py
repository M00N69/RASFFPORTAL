import streamlit as st
import pandas as pd
import plotly.express as px
import requests
from io import BytesIO
import datetime
from Levenshtein import distance
from typing import List, Optional
from dataclasses import dataclass
from functools import lru_cache

# Configuration with constants
@dataclass
class Config:
    URL_TEMPLATE: str = "https://www.sirene-diffusion.fr/regia/000-rasff/{}/rasff-{}-{}.xls"
    MAX_LEVENSHTEIN_DISTANCE: int = 3
    DATE_FORMAT: str = "%Y-%m-%dT%H:%M:%S.%f"

# Function to load lists from external sources securely
def load_external_list(url: str) -> List[str]:
    """Fetch and evaluate list data from raw GitHub URLs."""
    try:
        response = requests.get(url)
        response.raise_for_status()
        return eval(response.text)
    except Exception as e:
        st.error(f"Failed to load data from {url}: {e}")
        return []

# Load data lists from GitHub
notifying_countries = load_external_list("https://raw.githubusercontent.com/M00N69/RASFFPORTAL/refs/heads/main/notifying_countries.py")
hazard_categories = load_external_list("https://raw.githubusercontent.com/M00N69/RASFFPORTAL/refs/heads/main/hazard_categories.py")
origin_countries = load_external_list("https://raw.githubusercontent.com/M00N69/RASFFPORTAL/refs/heads/main/origin_countries.py")

# DataCleaner class for hazard correction and mapping
class DataCleaner:
    def __init__(self, hazard_categories: List[str]):
        # Convert hazard categories to a dictionary
        self.hazard_categories = {hc: desc for hc, desc in hazard_categories}
        self.hazards = []  # Dynamically populated with hazards in data

    @lru_cache(maxsize=1000)
    def correct_hazard(self, hazard_name: str) -> str:
        """Correct misspelled hazard names based on Levenshtein distance."""
        best_match = min(self.hazards, key=lambda x: distance(x, hazard_name))
        return best_match if distance(best_match, hazard_name) <= Config.MAX_LEVENSHTEIN_DISTANCE else hazard_name

    def map_hazard_to_category(self, hazard: Optional[str]) -> str:
        """Map hazard to category based on keywords."""
        if not isinstance(hazard, str):  # Handle non-string types
            return "Other"
        for category, terms in self.hazard_categories.items():
            if any(term in hazard.lower() for term in terms.split('|')):
                return category
        return "Other"

    def clean_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Clean and standardize data for consistency."""
        if "hazards" in df.columns:
            self.hazards = df["hazards"].dropna().unique().tolist()
            df["hazards"] = df["hazards"].apply(lambda h: self.correct_hazard(h) if pd.notna(h) else h)
            df["hazard_category"] = df["hazards"].apply(self.map_hazard_to_category)
        df["notifying_country"] = df["notifying_country"].where(df["notifying_country"].isin(notifying_countries), "Other")
        df["origin"] = df["origin"].where(df["origin"].isin(origin_countries), "Other")
        df["date"] = pd.to_datetime(df["date"], errors='coerce', format=Config.DATE_FORMAT)
        return df.fillna("")

# DataFetcher for asynchronous data retrieval
class DataFetcher:
    @staticmethod
    async def fetch_data(url: str) -> Optional[bytes]:
        """Retrieve data from a URL asynchronously."""
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            return response.content
        except requests.RequestException as e:
            st.warning(f"Failed to fetch data from {url}: {e}")
            return None

    @staticmethod
    async def get_data_by_weeks(year: int, weeks: List[int]) -> List[pd.DataFrame]:
        """Consolidate weekly data from multiple URLs."""
        dfs = []
        for week in weeks:
            url = Config.URL_TEMPLATE.format(str(year)[2:], year, str(week).zfill(2))
            content = await DataFetcher.fetch_data(url)
            if content:
                df = pd.read_excel(BytesIO(content))
                dfs.append(df)
        return dfs

# DataAnalyzer for statistics generation
class DataAnalyzer:
    @staticmethod
    def calculate_descriptive_stats(df: pd.DataFrame) -> Tuple[pd.Series, pd.DataFrame]:
        """Generate descriptive statistics on grouped data."""
        try:
            grouped = df.groupby(['notifying_country', 'hazard_category']).size().reset_index(name='notifications_count')
            stats = grouped['notifications_count'].describe()
            return stats, grouped
        except Exception as e:
            st.error(f"Statistics calculation error: {e}")
            return pd.Series(), pd.DataFrame()

# Main Dashboard class to organize and render UI
class RASFFDashboard:
    def __init__(self):
        self.data_cleaner = DataCleaner(hazard_categories)
        self.data_analyzer = DataAnalyzer()

    def render_data_overview(self, df: pd.DataFrame):
        st.markdown("## Data Overview")
        st.dataframe(df)

    def render_statistics(self, df: pd.DataFrame):
        """Render descriptive statistics and grouped counts."""
        stats, grouped = self.data_analyzer.calculate_descriptive_stats(df)
        st.markdown("## Descriptive Statistics on Notifications")
        st.write(stats)
        st.markdown("### Notifications Count by Country and Hazard Type")
        st.dataframe(grouped)

    def render_visualizations(self, df: pd.DataFrame):
        """Render bar and histogram charts for insights."""
        # Check if columns needed for visualization are available
        if {"notifying_country", "hazard_category", "notifications_count"}.issubset(df.columns):
            st.markdown("### Notifications by Country")
            fig_countries = px.bar(
                df, x="notifying_country", y="notifications_count", 
                color="hazard_category", title="Notifications by Country"
            )
            st.plotly_chart(fig_countries, use_container_width=True)

            st.markdown("### Hazard Category Distribution")
            fig_hazards = px.histogram(df, x="hazard_category", title="Hazard Category Distribution")
            st.plotly_chart(fig_hazards, use_container_width=True)
        else:
            st.warning("Required data columns are missing for visualizations.")

    async def run(self):
        st.title("RASFF Data Analyzer")
        
        # Interactive date range selection
        start_date = st.date_input("Start Date", datetime.date.today() - datetime.timedelta(weeks=8))
        end_date = st.date_input("End Date", datetime.date.today())
        selected_weeks = [start_date.isocalendar()[1] + i for i in range((end_date - start_date).days // 7 + 1)]
        
        # Load and clean data
        current_year = start_date.year
        dfs = await DataFetcher.get_data_by_weeks(current_year, selected_weeks)

        if dfs:
            df = pd.concat(dfs, ignore_index=True)
            df = self.data_cleaner.clean_data(df)
            
            # Display data in structured tabs
            tabs = st.tabs(["Overview", "Statistics", "Visualizations"])
            
            with tabs[0]:
                self.render_data_overview(df)
            with tabs[1]:
                self.render_statistics(df)
            with tabs[2]:
                self.render_visualizations(df)
        else:
            st.error("No data available for the selected weeks.")

# Execute the Streamlit application
if __name__ == "__main__":
    st.set_page_config(page_title="RASFF Analyzer", page_icon="📊", layout="wide")
    dashboard = RASFFDashboard()
    import asyncio
    asyncio.run(dashboard.run())
