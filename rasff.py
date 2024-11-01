import streamlit as st
st.set_page_config(page_title="Analyseur RASFF", page_icon="📊", layout="wide")

import pandas as pd
import datetime
from io import BytesIO
from typing import List, Optional
from dataclasses import dataclass
from functools import lru_cache
from Levenshtein import distance
import httpx
import plotly.express as px

# Configuration for data constants
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
        df = df.drop(columns=['Unnamed: 0'], errors='ignore')
        
        if 'notifying_country' in df.columns:
            df['notifying_country'] = df['notifying_country'].apply(self.standardize_country)
        if 'origin' in df.columns:
            df['origin'] = df['origin'].apply(self.standardize_country)
        
        if 'date' in df.columns:
            df['date'] = df['date'].apply(self.standardize_date)
        
        multivalue_columns = ['distribution', 'forAttention', 'forFollowUp', 'operator']
        for col in multivalue_columns:
            if col in df.columns:
                df[col] = df[col].apply(self.split_and_standardize_multivalue)
        
        if 'hazards' in df.columns:
            df['hazards'].fillna("Unknown", inplace=True)
        if 'hazard_category' in df.columns:
            df['hazard_category'].fillna("Other", inplace=True)
        
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
        if "hazard_category" in df.columns:
            df["hazard_category"] = df["hazards"].apply(self.map_hazard_to_category)
        
        return df.fillna("")

class DataFetcher:
    @staticmethod
    async def fetch_data(url: str) -> Optional[bytes]:
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
            content = await DataFetcher.fetch_data(url)
            if content:
                df = pd.read_excel(BytesIO(content))
                dfs.append(df)
            else:
                st.warning(f"Données indisponibles pour l'URL : {url}")
        return dfs

class DataAnalyzer:
    @staticmethod
    def calculate_descriptive_stats(df: pd.DataFrame) -> pd.DataFrame:
        try:
            grouped = df.groupby(['Product Category', 'issue_type']).size().reset_index(name='notifications_count')
            return grouped
        except Exception as e:
            st.error(f"Erreur de calcul des statistiques : {e}")
            return pd.DataFrame()
import plotly.express as px

def classify_issue(hazard_substance: str, hazard_category: str) -> str:
    categories = hazard_category.lower().split(";")
    classification_set = set()

    for category in categories:
        category = category.strip()
        if 'pathogenic micro-organisms' in category:
            classification_set.add("Pathogenic Micro-organism")
        elif 'mycotoxins' in category:
            classification_set.add("Mycotoxins")
        elif 'pesticide residues' in category:
            classification_set.add("Pesticide Residue")
        elif 'heavy metals' in category:
            classification_set.add("Heavy Metals")
        elif 'chemical contamination' in category:
            classification_set.add("Chemical Contamination")
        elif 'composition' in category:
            classification_set.add("Composition Issue")
        elif 'migration' in category:
            classification_set.add("Migration Issue")
        elif 'allergens' in category:
            classification_set.add("Allergens")
        elif 'food additives and flavourings' in category:
            classification_set.add("Food Additives and Flavourings")
        elif 'environmental pollutants' in category:
            classification_set.add("Environmental Pollutants")
        elif 'veterinary medicinal products' in category:
            classification_set.add("Veterinary Residues")
        elif 'foreign bodies' in category:
            classification_set.add("Foreign Bodies")
        elif 'parasitic infestation' in category:
            classification_set.add("Parasitic Infestation")
        elif 'natural toxins' in category:
            classification_set.add("Natural Toxins")
        elif 'industrial contaminants' in category:
            classification_set.add("Industrial Contaminants")
        elif 'biological contaminants' in category:
            classification_set.add("Biological Contaminants")
        elif 'genetically modified' in category:
            classification_set.add("Genetically Modified")
        elif 'organoleptic aspects' in category:
            classification_set.add("Organoleptic Aspects")
        elif 'novel food' in category:
            classification_set.add("Novel Food")
        else:
            classification_set.add("Other")

    return ", ".join(classification_set)

class RASFFDashboard:
    def __init__(self):
        self.data_cleaner = DataCleaner(hazard_categories)
        self.data_analyzer = DataAnalyzer()
        self.standardizer = DataStandardizer(notifying_countries, origin_countries)

    def render_data_overview(self, df: pd.DataFrame):
        st.markdown("## Aperçu des données")
        st.dataframe(df)

    def render_statistics(self, df: pd.DataFrame):
        # Generate descriptive statistics based on Product Category and issue_type
        grouped = self.data_analyzer.calculate_descriptive_stats(df)
        
        if grouped.empty:
            st.warning("Aucune donnée disponible pour les statistiques.")
            return
        
        st.markdown("## Statistiques descriptives des notifications")
        st.write("### Nombre de notifications par type de produit et type de problème")
        st.dataframe(grouped)

    def render_visualizations(self, df: pd.DataFrame):
        st.markdown("### Visualisations interactives avec filtres")
        
        # Dropdown filters for issue_type and product_category
        issue_type_options = ["Tous"] + sorted(df["issue_type"].dropna().unique())
        product_category_options = ["Tous"] + sorted(df["Product Category"].dropna().unique())

        selected_issue_type = st.selectbox("Filtrer par type de problème", options=issue_type_options)
        selected_product_category = st.selectbox("Filtrer par catégorie de produit", options=product_category_options)
        
        # Apply filters to the DataFrame
        if selected_issue_type != "Tous":
            df = df[df["issue_type"] == selected_issue_type]
        if selected_product_category != "Tous":
            df = df[df["Product Category"] == selected_product_category]

        if df.empty:
            st.warning("Aucune donnée disponible pour les filtres sélectionnés.")
        else:
            # Bar chart of notifications by product type
            fig_categories = px.bar(
                df, x="Product Category", y="Reference", 
                color="issue_type", title="Notifications par type de produit",
                labels={"Reference": "Nombre de notifications"}
            )
            st.plotly_chart(fig_categories, use_container_width=True)

            # Pie chart for issue type distribution
            fig_issues = px.pie(df, names="issue_type", title="Répartition des types de problèmes")
            st.plotly_chart(fig_issues, use_container_width=True)
    async def run(self):
        st.title("Analyseur de données RASFF")
        
        # Define the URL for the CSV file on GitHub
        csv_url = "https://raw.githubusercontent.com/M00N69/RASFFPORTAL/refs/heads/main/rasff_%202020TO30OCT2024.csv"
        
        try:
            # Load data directly from the GitHub URL
            df = pd.read_csv(csv_url)
            
            # Standardize and clean data
            df = self.standardizer.clean_data(df)
            df = self.data_cleaner.clean_data(df)
            
            # Classify each row based on the hazard substance and hazard category
            df['issue_type'] = df.apply(lambda row: classify_issue(row['Hazard Substance'], row['Hazard Category']), axis=1)
            
            if not df.empty:
                # Display data overview, statistics, and visualizations using Streamlit tabs
                tabs = st.tabs(["Aperçu", "Statistiques", "Visualisations"])
                with tabs[0]:
                    self.render_data_overview(df)
                with tabs[1]:
                    self.render_statistics(df)
                with tabs[2]:
                    self.render_visualizations(df)
            else:
                st.error("Le fichier CSV est vide ou les données n'ont pas pu être chargées.")
                
        except Exception as e:
            st.error(f"Erreur lors du chargement des données: {e}")

        # Date range for future weeks (starting from Nov 4, 2024)
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
                future_data = pd.concat(dfs, ignore_index=True)
                future_data = self.standardizer.clean_data(future_data)
                future_data = self.data_cleaner.clean_data(future_data)

                # Concatenate future data with existing data
                df = pd.concat([df, future_data], ignore_index=True)
                st.success("Données futures ajoutées avec succès.")

                # Update visualizations and statistics with combined data
                with tabs[1]:
                    self.render_statistics(df)
                with tabs[2]:
                    self.render_visualizations(df)
            else:
                st.warning("Aucune donnée disponible pour les semaines sélectionnées.")

# Execution of the Streamlit application
if __name__ == "__main__":
    dashboard = RASFFDashboard()
    import asyncio
    asyncio.run(dashboard.run())
