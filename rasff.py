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
        return country if country in self.notifying_countries else "Other"
    
    def standardize_date(self, date):
        if pd.isna(date):
            return pd.NaT
        try:
            return pd.to_datetime(date, errors='coerce')
        except:
            return pd.NaT
    
    def split_and_standardize_multivalue(self, value: str) -> List[str]:
        if pd.isna(value):
            return ["Unknown"]
        return [item.strip() for item in value.split(',')]
    
    def clean_data(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.drop(columns=['Unnamed: 0'], errors='ignore')  # Drop unnecessary columns
        
        # Standardize country columns
        df['notifying_country'] = df['notifying_country'].apply(self.standardize_country)
        df['origin'] = df['origin'].apply(self.standardize_country)
        
        # Parse date
        df['date'] = df['date'].apply(self.standardize_date)
        
        # Split and standardize multivalued columns
        multivalue_columns = ['distribution', 'forAttention', 'forFollowUp', 'operator']
        for col in multivalue_columns:
            df[col] = df[col].apply(self.split_and_standardize_multivalue)
        
        # Fill missing hazard and hazard_category
        df['hazards'].fillna("Unknown", inplace=True)
        df['hazard_category'].fillna("Other", inplace=True)
        
        # Convert to lowercase for consistency
        df['category'] = df['category'].str.lower()
        df['type'] = df['type'].str.lower()
        df['classification'] = df['classification'].str.lower()
        df['risk_decision'] = df['risk_decision'].str.lower()
        
        return df
# Classe DataCleaner pour corriger et mapper les dangers (hazards)
class DataCleaner:
    def __init__(self, hazard_categories: dict):
        self.hazard_categories = hazard_categories
        self.hazards = []

    @lru_cache(maxsize=1000)
    def correct_hazard(self, hazard_name: str) -> str:
        best_match = min(self.hazards, key=lambda x: distance(x, hazard_name))
        return best_match if distance(best_match, hazard_name) <= Config.MAX_LEVENSHTEIN_DISTANCE else hazard_name

    def map_hazard_to_category(self, hazard: Optional[str]) -> str:
        if not isinstance(hazard, str):
            return "Other"
        for category, terms in self.hazard_categories.items():
            if any(term in hazard.lower() for term in terms.split('|')):
                return category
        return "Other"

    def clean_data(self, df: pd.DataFrame) -> pd.DataFrame:
        if "hazards" in df.columns:
            self.hazards = df["hazards"].dropna().unique().tolist()
            df["hazards"] = df["hazards"].apply(lambda h: self.correct_hazard(h) if pd.notna(h) else h)
            df["hazard_category"] = df["hazards"].apply(self.map_hazard_to_category)
        df["notifying_country"] = df["notifying_country"].where(df["notifying_country"].isin(notifying_countries), "Other")
        df["origin"] = df["origin"].where(df["origin"].isin(origin_countries), "Other")
        df["date"] = pd.to_datetime(df["date"], errors='coerce', format=Config.DATE_FORMAT)
        return df.fillna("")

# Classe DataFetcher pour la récupération asynchrone des données
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
        dfs = []
        for week in weeks:
            url = Config.URL_TEMPLATE.format(str(year)[2:], year, str(week).zfill(2))
            print(f"Fetching data from: {url}")
            content = await DataFetcher.fetch_data(url)
            if content:
                df = pd.read_excel(BytesIO(content))
                dfs.append(df)
            else:
                st.warning(f"Données indisponibles pour l'URL : {url}")
        return dfs

# Classe DataAnalyzer pour générer des statistiques descriptives
class DataAnalyzer:
    @staticmethod
    def calculate_descriptive_stats(df: pd.DataFrame) -> Tuple[pd.Series, pd.DataFrame]:
        try:
            grouped = df.groupby(['notifying_country', 'hazard_category']).size().reset_index(name='notifications_count')
            stats = grouped['notifications_count'].describe()
            return stats, grouped
        except Exception as e:
            st.error(f"Erreur de calcul des statistiques : {e}")
            return pd.Series(), pd.DataFrame()
# Classe principale RASFFDashboard pour gérer l'interface utilisateur
class RASFFDashboard:
    def __init__(self):
        self.data_cleaner = DataCleaner(hazard_categories)
        self.data_analyzer = DataAnalyzer()
        self.standardizer = DataStandardizer(notifying_countries, origin_countries)

    def render_data_overview(self, df: pd.DataFrame):
        st.markdown("## Aperçu des données")
        st.dataframe(df)

    def render_statistics(self, df: pd.DataFrame):
        stats, grouped = self.data_analyzer.calculate_descriptive_stats(df)
        st.markdown("## Statistiques descriptives des notifications")
        st.write(stats)
        st.markdown("### Nombre de notifications par pays et type de danger")
        st.dataframe(grouped)

    def render_visualizations(self, df: pd.DataFrame):
        if {"notifying_country", "hazard_category", "notifications_count"}.issubset(df.columns):
            st.markdown("### Notifications par pays")
            fig_countries = px.bar(
                df, x="notifying_country", y="notifications_count", 
                color="hazard_category", title="Notifications par pays"
            )
            st.plotly_chart(fig_countries, use_container_width=True)

            st.markdown("### Distribution des catégories de danger")
            fig_hazards = px.histogram(df, x="hazard_category", title="Distribution des catégories de danger")
            st.plotly_chart(fig_hazards, use_container_width=True)
        else:
            st.warning("Les colonnes de données nécessaires pour les visualisations sont manquantes.")

    async def run(self):
        st.title("Analyseur de données RASFF")
        
        # Sélection de la plage de dates
        start_date = st.date_input("Date de début", datetime.date.today() - datetime.timedelta(weeks=8))
        end_date = st.date_input("Date de fin", datetime.date.today())
        selected_weeks = [start_date.isocalendar()[1] + i for i in range((end_date - start_date).days // 7 + 1)]
        
        # Chargement et nettoyage des données
        current_year = start_date.year
        dfs = await DataFetcher.get_data_by_weeks(current_year, selected_weeks)

        if dfs:
            df = pd.concat(dfs, ignore_index=True)
            df = self.standardizer.clean_data(df)  # Standardize data
            df = self.data_cleaner.clean_data(df)  # Further clean hazards
            
            # Affichage structuré des données dans des onglets
            tabs = st.tabs(["Aperçu", "Statistiques", "Visualisations"])
            
            with tabs[0]:
                self.render_data_overview(df)
            with tabs[1]:
                self.render_statistics(df)
            with tabs[2]:
                self.render_visualizations(df)
        else:
            st.error("Aucune donnée disponible pour les semaines sélectionnées.")

# Exécution de l'application Streamlit
if __name__ == "__main__":
    dashboard = RASFFDashboard()
    import asyncio
    asyncio.run(dashboard.run())
