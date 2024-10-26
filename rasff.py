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

# Define the missing data structures
product_categories = {
    "fruits and vegetables": "Fruits et Légumes",
    "herbs and spices": "Herbes et Épices",
    "nuts, nut products and seeds": "Fruits à coque et Graines",
    "cereals and bakery products": "Céréales et Produits de Boulangerie",
    "fish and fish products": "Poissons et Produits de la Mer",
    "meat and meat products": "Viande et Produits Carnés",
    "milk and milk products": "Lait et Produits Laitiers",
    "eggs and egg products": "Œufs et Ovoproduits",
    "prepared dishes and snacks": "Plats Préparés et Snacks",
    "food supplements": "Compléments Alimentaires",
    "beverages": "Boissons",
    "confectionery": "Confiserie",
    "food contact materials": "Matériaux au Contact des Aliments"
}

hazards = [
    "Pesticide residues",
    "Heavy metals",
    "Mycotoxins",
    "Food additives",
    "Allergens",
    "Pathogenic microorganisms",
    "Foreign bodies",
    "GMO/Novel food",
    "Poor or insufficient controls",
    "Packaging defective/incorrect",
    "Chemical contamination",
    "Composition",
    "Organoleptic aspects",
    "Labelling absent/incomplete/incorrect",
    "Migration"
]

hazard_categories = {
    "Chemical": "chemical contamination|pesticide|heavy metal|mycotoxin|food additive|migration",
    "Biological": "pathogenic|microorganism|mould|bacteria|virus",
    "Physical": "foreign body|packaging defective",
    "Allergens": "allergen",
    "Controls": "control|insufficient|poor",
    "Labelling": "label|marking",
    "Quality": "organoleptic|composition"
}

notifying_countries = [
    "Austria", "Belgium", "Bulgaria", "Croatia", "Cyprus", "Czech Republic",
    "Denmark", "Estonia", "Finland", "France", "Germany", "Greece", "Hungary",
    "Ireland", "Italy", "Latvia", "Lithuania", "Luxembourg", "Malta",
    "Netherlands", "Poland", "Portugal", "Romania", "Slovakia", "Slovenia",
    "Spain", "Sweden", "United Kingdom", "Norway", "Switzerland"
]

origin_countries = notifying_countries + [
    "China", "India", "Turkey", "United States", "Brazil", "Vietnam",
    "Thailand", "Indonesia", "Malaysia", "Russia", "South Africa", "Mexico",
    "Argentina", "Chile", "Morocco", "Egypt", "Tunisia", "Other"
]

# Type hints for better code organization
DataFrameType = pd.DataFrame
WeekType = int
YearType = int

@dataclass
class Config:
    """Configuration class to store constants and settings"""
    URL_TEMPLATE: str = "https://www.sirene-diffusion.fr/regia/000-rasff/{}/rasff-{}-{}.xls"
    MAX_LEVENSHTEIN_DISTANCE: int = 3
    DATE_FORMAT: str = "%d-%m-%Y %H:%M:%S"
    MAX_WEEKS: int = 52

class DataCleaner:
    """Class responsible for data cleaning operations"""
    
    def __init__(self, product_categories: Dict, hazards: List[str], 
                 hazard_categories: Dict, notifying_countries: List[str], 
                 origin_countries: List[str]):
        self.product_categories = product_categories
        self.hazards = hazards
        self.hazard_categories = hazard_categories
        self.notifying_countries = notifying_countries
        self.origin_countries = origin_countries

    @lru_cache(maxsize=1000)
    def correct_hazard(self, hazard_name: str) -> str:
        """Corrects typos in hazard names using cached results"""
        hazard_name = str(hazard_name)
        best_match = min(self.hazards, key=lambda x: distance(x, hazard_name))
        return best_match if distance(best_match, hazard_name) <= Config.MAX_LEVENSHTEIN_DISTANCE else hazard_name

    def map_hazard_to_category(self, hazard: str) -> str:
        """Maps hazards to categories efficiently"""
        hazard_lower = hazard.lower()
        for category, description in self.hazard_categories.items():
            if any(term in hazard_lower for term in description.split('|')):
                return category
        return "Autre"

    def clean_data(self, df: DataFrameType) -> DataFrameType:
        """Cleans and standardizes the data with improved error handling"""
        try:
            # Create a copy to avoid modifying the original
            df = df.copy()
            
            # Clean country data
            df["notifying_country"] = df["notifying_country"].where(
                df["notifying_country"].isin(self.notifying_countries), "Other")
            df["origin"] = df["origin"].where(
                df["origin"].isin(self.origin_countries), "Other")
            
            # Clean categories
            df["category"] = df["category"].map(self.product_categories).fillna("Other")
            
            # Clean hazards if present
            if "hazards" in df.columns:
                df["hazards"] = df["hazards"].apply(self.correct_hazard)
                df["hazard_category"] = df["hazards"].apply(self.map_hazard_to_category)
            
            # Convert dates
            try:
                df["date"] = pd.to_datetime(df["date"], format=Config.DATE_FORMAT)
            except ValueError:
                st.warning("Date conversion failed. Using original format.")
            
            return df.fillna("")
            
        except Exception as e:
            st.error(f"Error during data cleaning: {str(e)}")
            return df

class DataFetcher:
    """Class responsible for fetching RASFF data"""
    
    @staticmethod
    async def fetch_data(url: str) -> Optional[bytes]:
        """Asynchronously fetch data from URL with error handling"""
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            return response.content
        except requests.RequestException as e:
            st.warning(f"Failed to fetch data: {str(e)}")
            return None

    @staticmethod
    async def get_latest_available_week() -> Tuple[YearType, WeekType]:
        """Determines the latest available week with improved error handling"""
        current_date = datetime.datetime.now()
        current_year, current_week, _ = current_date.isocalendar()
        
        # Check current year
        for week in range(current_week, 0, -1):
            url = Config.URL_TEMPLATE.format(
                str(current_year)[2:],
                current_year,
                str(week).zfill(2)
            )
            try:
                response = requests.head(url, timeout=5)
                if response.status_code == 200:
                    return current_year, week
            except requests.RequestException:
                continue
        
        # Check previous year if needed
        prev_year = current_year - 1
        for week in range(Config.MAX_WEEKS, 0, -1):
            url = Config.URL_TEMPLATE.format(
                str(prev_year)[2:],
                prev_year,
                str(week).zfill(2)
            )
            try:
                response = requests.head(url, timeout=5)
                if response.status_code == 200:
                    return prev_year, week
            except requests.RequestException:
                continue
        
        return current_year, current_week

class DataAnalyzer:
    """Class responsible for data analysis"""
    
    @staticmethod
    def calculate_descriptive_stats(df: DataFrameType) -> Tuple[pd.Series, DataFrameType]:
        """Calculates descriptive statistics with error handling"""
        try:
            grouped = (df.groupby(['notifying_country', 'hazard_category'])
                      .size()
                      .reset_index(name='notifications_count'))
            stats = grouped['notifications_count'].describe()
            return stats, grouped
        except Exception as e:
            st.error(f"Error calculating statistics: {str(e)}")
            return pd.Series(), pd.DataFrame()

class RASFFDashboard:
    """Main dashboard class"""
    
    def __init__(self):
        self.data_cleaner = DataCleaner(
            product_categories=product_categories,
            hazards=hazards,
            hazard_categories=hazard_categories,
            notifying_countries=notifying_countries,
            origin_countries=origin_countries
        )
        self.data_fetcher = DataFetcher()
        self.data_analyzer = DataAnalyzer()

    def render_data_overview(self, df: DataFrameType):
        """Renders data overview tab"""
        st.markdown("## Données analysées")
        st.dataframe(df)

    def render_statistics(self, df: DataFrameType):
        """Renders statistics tab"""
        stats, grouped = self.data_analyzer.calculate_descriptive_stats(df)
        st.markdown("## Statistiques descriptives sur les notifications")
        st.write(stats)
        st.markdown("### Nombre de notifications par pays et type de danger")
        st.dataframe(grouped)

    def render_visualizations(self, df: DataFrameType):
        """Renders visualization tab"""
        stats, grouped = self.data_analyzer.calculate_descriptive_stats(df)
        
        # Notifications by country
        st.markdown("### Nombre de notifications par pays")
        fig_countries = px.bar(
            grouped,
            x="notifying_country",
            y="notifications_count",
            title="Notifications par pays",
            color="hazard_category"
        )
        st.plotly_chart(fig_countries, use_container_width=True)
        
        # Hazard categories distribution
        if "hazard_category" in df.columns:
            st.markdown("### Distribution des catégories de dangers")
            fig_hazards = px.histogram(
                grouped,
                x="hazard_category",
                y="notifications_count",
                title="Distribution des catégories de dangers"
            )
            st.plotly_chart(fig_hazards, use_container_width=True)

    async def run(self):
        """Main application loop"""
        st.title("Analyseur de Données RASFF")

        # Get latest available week
        year, latest_week = await self.data_fetcher.get_latest_available_week()
        st.write(f"Dernière semaine disponible : {latest_week} de l'année {year}")

        # Week selection
        weeks_options = list(range(1, latest_week + 1))
        selected_weeks = st.multiselect(
            "Sélectionnez les semaines",
            weeks_options,
            default=[latest_week]
        )

        if selected_weeks:
            # Fetch and process data
            dfs = []
            for week in selected_weeks:
                url = Config.URL_TEMPLATE.format(str(year)[2:], year, str(week).zfill(2))
                content = await self.data_fetcher.fetch_data(url)
                if content:
                    df = pd.read_excel(BytesIO(content))
                    dfs.append(df)

            if dfs:
                # Process combined data
                df = pd.concat(dfs, ignore_index=True)
                df = self.data_cleaner.clean_data(df)

                # Create tabs
                tabs = st.tabs(["Aperçu", "Statistiques", "Visualisations"])
                
                with tabs[0]:
                    self.render_data_overview(df)
                with tabs[1]:
                    self.render_statistics(df)
                with tabs[2]:
                    self.render_visualizations(df)
            else:
                st.error("Aucune donnée disponible pour les semaines sélectionnées.")

if __name__ == "__main__":
    st.set_page_config(
        page_title="RASFF Analyzer",
        page_icon="📊",
        layout="wide"
    )
    
    dashboard = RASFFDashboard()
    import asyncio
    asyncio.run(dashboard.run())
