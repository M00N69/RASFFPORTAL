import streamlit as st
st.set_page_config(page_title="Analyseur RASFF", page_icon="📊", layout="wide")

import pandas as pd
import plotly.express as px
import httpx
import datetime
from io import BytesIO
from typing import List, Optional, Tuple
from Levenshtein import distance
from dataclasses import dataclass
from functools import lru_cache

# Import des fichiers locaux comme modules
from hazard_categories import hazard_categories
from notifying_countries import notifying_countries
from origin_countries import origin_countries

# Configuration des constantes avec un modèle de données
@dataclass
class Config:
    URL_TEMPLATE: str = "https://www.sirene-diffusion.fr/regia/000-rasff/{}/rasff-{}-{}.xls"
    MAX_LEVENSHTEIN_DISTANCE: int = 3
    DATE_FORMAT: str = "%Y-%m-%dT%H:%M:%S.%f"

class DataStandardizer:
    def __init__(self, notifying_countries: List[str], origin_countries: List[str]):
        self.notifying_countries = notifying_countries
        self.origin_countries = origin_countries
    
    def standardize_country(self, country: str) -> str:
        """Standardize country names based on a predefined list, marking unknown countries as 'Other'."""
        return country if country in self.notifying_countries else "Other"
    
    def standardize_date(self, date):
        """Convert date strings to datetime format, handling missing values gracefully."""
        if pd.isna(date):
            return pd.NaT
        try:
            return pd.to_datetime(date, errors='coerce')
        except:
            return pd.NaT
    
    def split_and_standardize_multivalue(self, value: str) -> List[str]:
        """Split multivalue fields (comma-separated) into lists and handle missing values."""
        if pd.isna(value):
            return ["Unknown"]
        return [item.strip() for item in value.split(',')]
    
    def clean_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Apply data standardization steps across multiple columns."""
        df = df.drop(columns=['Unnamed: 0'], errors='ignore')  # Drop unnecessary columns
        
        # Standardize country columns if they exist
        if 'notifying_country' in df.columns:
            df['notifying_country'] = df['notifying_country'].apply(self.standardize_country)
        if 'origin' in df.columns:
            df['origin'] = df['origin'].apply(self.standardize_country)
        
        # Parse date if it exists
        if 'date' in df.columns:
            df['date'] = df['date'].apply(self.standardize_date)
        
        # Split and standardize multivalued columns if they exist
        multivalue_columns = ['distribution', 'forAttention', 'forFollowUp', 'operator']
        for col in multivalue_columns:
            if col in df.columns:
                df[col] = df[col].apply(self.split_and_standardize_multivalue)
        
        # Fill missing values in hazards and hazard_category if they exist
        if 'hazards' in df.columns:
            df['hazards'].fillna("Unknown", inplace=True)
        if 'hazard_category' in df.columns:
            df['hazard_category'].fillna("Other", inplace=True)
        
        # Convert to lowercase for consistency in specific columns if they exist
        for col in ['category', 'type', 'classification', 'risk_decision']:
            if col in df.columns:
                df[col] = df[col].str.lower()
        
        return df

class DataCleaner:
    def __init__(self, hazard_categories: dict):
        self.hazard_categories = hazard_categories
        self.hazards = []

    @lru_cache(maxsize=1000)
    def correct_hazard(self, hazard_name: str) -> str:
        """Use Levenshtein distance to find the best match for correcting hazard names."""
        best_match = min(self.hazards, key=lambda x: distance(x, hazard_name))
        return best_match if distance(best_match, hazard_name) <= Config.MAX_LEVENSHTEIN_DISTANCE else hazard_name

    def map_hazard_to_category(self, hazard: Optional[str]) -> str:
        """Map hazard names to categories based on predefined keywords."""
        if not isinstance(hazard, str):
            return "Other"
        for category, terms in self.hazard_categories.items():
            if any(term in hazard.lower() for term in terms.split('|')):
                return category
        return "Other"

    def clean_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Apply hazard correction and category mapping to the DataFrame."""
        # Check and correct hazards and hazard_category columns if they exist
        if "hazards" in df.columns:
            self.hazards = df["hazards"].dropna().unique().tolist()
            df["hazards"] = df["hazards"].apply(lambda h: self.correct_hazard(h) if pd.notna(h) else h)
        if "hazard_category" in df.columns:
            df["hazard_category"] = df["hazards"].apply(self.map_hazard_to_category)
        
        return df.fillna("")

class DataFetcher:
    @staticmethod
    async def fetch_data(url: str) -> Optional[bytes]:
        """Retrieve data from a URL asynchronously and handle errors."""
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(url, timeout=10)
                response.raise_for_status()
                return response.content
            except httpx.RequestError as e:
                st.warning(f"Échec de la connexion au serveur pour {url}: {e}")
            except httpx.HTTPStatusError as e:
                st.warning(f"Erreur HTTP {e.response.status_code} pour {url}: {e}")
        return None

    @staticmethod
    async def get_data_by_weeks(year: int, weeks: List[int]) -> List[pd.DataFrame]:
        """Fetch data for a list of weeks and return as a list of DataFrames."""
        dfs = []
        for week in weeks:
            url = Config.URL_TEMPLATE.format(str(year)[2:], year, str(week).zfill(2))
            content = await DataFetcher.fetch_data(url)
            if content:
                df = pd.read_excel(BytesIO(content))
                dfs.append(df)
            else:
                st.warning(f"Données indisponibles pour l'URL : {url}")
        return dfs

class DataAnalyzer:
    @staticmethod
    def calculate_descriptive_stats(df: pd.DataFrame) -> Tuple[pd.Series, pd.DataFrame]:
        """Calculate and return descriptive statistics on the data."""
        try:
            grouped = df.groupby(['category', 'issue_type']).size().reset_index(name='notifications_count')
            stats = grouped['notifications_count'].describe()
            return stats, grouped
        except Exception as e:
            st.error(f"Erreur de calcul des statistiques : {e}")
            return pd.Series(), pd.DataFrame()

class RASFFDashboard:
    def __init__(self):
        self.data_cleaner = DataCleaner(hazard_categories)
        self.data_analyzer = DataAnalyzer()
        self.standardizer = DataStandardizer(notifying_countries, origin_countries)

    def render_data_overview(self, df: pd.DataFrame):
        """Display an overview of the data."""
        st.markdown("## Aperçu des données")
        st.dataframe(df)

    def render_statistics(self, df: pd.DataFrame):
        """Generate and display descriptive statistics."""
        stats, grouped = self.data_analyzer.calculate_descriptive_stats(df)
        st.markdown("## Statistiques descriptives des notifications")
        st.write(stats)
        st.markdown("### Nombre de notifications par type de produit et type de problème")
        st.dataframe(grouped)

    def render_visualizations(self, df: pd.DataFrame):
        """Generate bar and histogram visualizations of the data."""
        if {"category", "issue_type", "notifications_count"}.issubset(df.columns):
            st.markdown("### Notifications par type de produit")
            fig_categories = px.bar(
                df, x="category", y="notifications_count", 
                color="issue_type", title="Notifications par type de produit"
            )
            st.plotly_chart(fig_categories, use_container_width=True)

            st.markdown("### Distribution des types de problèmes")
            fig_issues = px.pie(df, names="issue_type", values="notifications_count", title="Répartition des types de problèmes")
            st.plotly_chart(fig_issues, use_container_width=True)
        else:
            st.warning("Les colonnes de données nécessaires pour les visualisations sont manquantes.")

    async def run(self):
        """Main function to execute the Streamlit dashboard."""
        st.title("Analyseur de données RASFF")
        
        # Load initial data from CSV file
        df = pd.read_csv('/mnt/data/rasff_ 2020TO30OCT2024.csv')
        
        # Standardize and clean data
        # Standardize and clean data
        df = self.standardizer.clean_data(df)  # Standardize data
        df = self.data_cleaner.clean_data(df)  # Further clean hazards
        
        # Display overview and analyze data if available
        if not df.empty:
            # Classify and calculate statistics
            df['issue_type'] = df.apply(lambda row: classify_issue(row['subject'], row['hazards']), axis=1)
            stats, grouped = self.data_analyzer.calculate_descriptive_stats(df)
            
            # Setup tabs for structured display
            tabs = st.tabs(["Aperçu", "Statistiques", "Visualisations"])
            
            with tabs[0]:
                self.render_data_overview(df)
            with tabs[1]:
                self.render_statistics(df)
            with tabs[2]:
                self.render_visualizations(grouped)
        else:
            st.error("Le fichier CSV est vide ou les données n'ont pas pu être chargées.")

        # Select date range for additional data fetching (future weeks starting from Nov 4, 2024)
        start_date = datetime.date(2024, 11, 4)
        end_date = st.date_input("Date de fin pour les semaines supplémentaires", datetime.date.today())
        
        if end_date > start_date:
            future_weeks = [
                start_date.isocalendar()[1] + i
                for i in range((end_date - start_date).days // 7 + 1)
            ]
            current_year = start_date.year
            dfs = await DataFetcher.get_data_by_weeks(current_year, future_weeks)

            if dfs:
                # Concatenate future data with existing data
                future_data = pd.concat(dfs, ignore_index=True)
                future_data = self.standardizer.clean_data(future_data)
                future_data = self.data_cleaner.clean_data(future_data)

                # Add future data to the main dataframe
                df = pd.concat([df, future_data], ignore_index=True)
                st.success("Données futures ajoutées avec succès.")

                # Update visualizations and statistics with combined data
                stats, grouped = self.data_analyzer.calculate_descriptive_stats(df)
                with tabs[1]:
                    self.render_statistics(df)
                with tabs[2]:
                    self.render_visualizations(grouped)
            else:
                st.warning("Aucune donnée disponible pour les semaines sélectionnées.")

# Execution of the Streamlit application
if __name__ == "__main__":
    dashboard = RASFFDashboard()
    import asyncio
    asyncio.run(dashboard.run())

