import streamlit as st
import pandas as pd
import plotly.express as px
import requests
from io import BytesIO
import datetime
from Levenshtein import distance
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
from functools import lru_cache

# Constants and reusable configurations
@dataclass
class Config:
    URL_TEMPLATE: str = "https://www.sirene-diffusion.fr/regia/000-rasff/{}/rasff-{}-{}.xls"
    MAX_LEVENSHTEIN_DISTANCE: int = 3
    DATE_FORMAT: str = "%Y-%m-%dT%H:%M:%S.%f"
    MAX_WEEKS: int = 52

# Data cleaning and transformation class
class DataCleaner:
    def __init__(self):
        self.hazard_categories = {
            "Chemical": "chemical contamination|pesticide|heavy metal|mycotoxin",
            "Biological": "pathogenic|microorganism",
            "Physical": "foreign body|packaging defective",
            "Allergens": "allergen",
            "Controls": "control|insufficient|poor",
            "Labelling": "label|marking",
            "Quality": "organoleptic|composition"
        }

    @lru_cache(maxsize=1000)
    def correct_hazard(self, hazard_name: str, hazards: List[str]) -> str:
        best_match = min(hazards, key=lambda x: distance(x, hazard_name))
        return best_match if distance(best_match, hazard_name) <= Config.MAX_LEVENSHTEIN_DISTANCE else hazard_name

    def map_hazard_to_category(self, hazard: str) -> str:
        for category, terms in self.hazard_categories.items():
            if any(term in hazard.lower() for term in terms.split('|')):
                return category
        return "Other"

    def clean_data(self, df: pd.DataFrame, hazards: List[str]) -> pd.DataFrame:
        df = df.copy()
        # Standardize hazard names and categorize
        if "hazards" in df.columns:
            df["hazards"] = df["hazards"].apply(lambda h: self.correct_hazard(h, hazards))
            df["hazard_category"] = df["hazards"].apply(self.map_hazard_to_category)
        
        # Date conversion with error handling
        try:
            df["date"] = pd.to_datetime(df["date"], errors='coerce', format=Config.DATE_FORMAT)
        except Exception as e:
            st.warning(f"Error parsing dates: {str(e)}")
        
        return df.fillna("")

# Data fetching class with URL loading logic
class DataFetcher:
    @staticmethod
    async def fetch_data(url: str) -> Optional[bytes]:
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            return response.content
        except requests.RequestException as e:
            st.warning(f"Failed to fetch data: {str(e)}")
            return None

    @staticmethod
    async def get_data_by_weeks(year: int, weeks: List[int]) -> List[pd.DataFrame]:
        dfs = []
        for week in weeks:
            url = Config.URL_TEMPLATE.format(str(year)[2:], year, str(week).zfill(2))
            content = await DataFetcher.fetch_data(url)
            if content:
                df = pd.read_excel(BytesIO(content))
                dfs.append(df)
        return dfs

# Data analysis class
class DataAnalyzer:
    @staticmethod
    def calculate_descriptive_stats(df: pd.DataFrame) -> Tuple[pd.Series, pd.DataFrame]:
        try:
            grouped = df.groupby(['notifying_country', 'hazard_category']).size().reset_index(name='notifications_count')
            stats = grouped['notifications_count'].describe()
            return stats, grouped
        except Exception as e:
            st.error(f"Statistics error: {str(e)}")
            return pd.Series(), pd.DataFrame()

# Main dashboard class
class RASFFDashboard:
    def __init__(self):
        self.data_cleaner = DataCleaner()
        self.data_analyzer = DataAnalyzer()

    def render_data_overview(self, df: pd.DataFrame):
        st.markdown("## Data Overview")
        st.dataframe(df)

    def render_statistics(self, df: pd.DataFrame):
        stats, grouped = self.data_analyzer.calculate_descriptive_stats(df)
        st.markdown("## Descriptive Statistics on Notifications")
        st.write(stats)
        st.markdown("### Notifications Count by Country and Hazard Type")
        st.dataframe(grouped)

    def render_visualizations(self, df: pd.DataFrame):
        st.markdown("### Notifications by Country")
        fig_countries = px.bar(df, x="notifying_country", y="notifications_count", title="Notifications by Country", color="hazard_category")
        st.plotly_chart(fig_countries, use_container_width=True)

        if "hazard_category" in df.columns:
            st.markdown("### Hazard Category Distribution")
            fig_hazards = px.histogram(df, x="hazard_category", title="Hazard Category Distribution")
            st.plotly_chart(fig_hazards, use_container_width=True)

    async def run(self):
        st.title("RASFF Data Analyzer")
        
        # Date range selection
        start_date = st.date_input("Start Date", datetime.date.today() - datetime.timedelta(weeks=8))
        end_date = st.date_input("End Date", datetime.date.today())
        selected_weeks = [start_date.isocalendar()[1] + i for i in range((end_date - start_date).days // 7 + 1)]
        
        # Year and week validation
        current_year = start_date.year
        dfs = await DataFetcher.get_data_by_weeks(current_year, selected_weeks)

        if dfs:
            df = pd.concat(dfs, ignore_index=True)
            hazards = df["hazards"].unique().tolist()
            df = self.data_cleaner.clean_data(df, hazards)
            
            # Create tabs
            tabs = st.tabs(["Overview", "Statistics", "Visualizations"])
            
            with tabs[0]:
                self.render_data_overview(df)
            with tabs[1]:
                self.render_statistics(df)
            with tabs[2]:
                self.render_visualizations(df)
        else:
            st.error("No data available for the selected weeks.")

# Main execution
if __name__ == "__main__":
    st.set_page_config(page_title="RASFF Analyzer", page_icon="📊", layout="wide")
    dashboard = RASFFDashboard()
    import asyncio
    asyncio.run(dashboard.run())

