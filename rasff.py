import streamlit as st
import pandas as pd
import plotly.express as px
from io import BytesIO
import requests
import datetime
from typing import List
import re

# Mapping for hazard categories in French
hazard_categories = {
    "GMO / novel food": "OGM / nouveau aliment",
    "TSEs": "EST",
    "adulteration / fraud": "Adultération / fraude",
    "allergens": "Allergènes",
    "biological contaminants": "Contaminants biologiques",
    "biotoxins (other)": "Biotoxines (autres)",
    "chemical contamination (other)": "Contamination chimique (autres)",
    "composition": "Composition",
    "environmental pollutants": "Polluants environnementaux",
    "feed additives": "Additifs pour l'alimentation animale",
    "food additives and flavourings": "Additifs alimentaires et arômes",
    "foreign bodies": "Corps étrangers",
    "genetically modified": "Génétiquement modifié",
    "heavy metals": "Métaux lourds",
    "industrial contaminants": "Contaminants industriels",
    "labelling absent/incomplete/incorrect": "Étiquetage absent/incomplet/incorrect",
    "migration": "Migration",
    "mycotoxins": "Mycotoxines",
    "natural toxins (other)": "Toxines naturelles (autres)",
    "non-pathogenic micro-organisms": "Micro-organismes non pathogènes",
    "not determined (other)": "Non déterminé (autres)",
    "novel food": "Nouveau aliment",
    "organoleptic aspects": "Aspects organoleptiques",
    "packaging defective / incorrect": "Emballage défectueux / incorrect",
    "parasitic infestation": "Infestation parasitaire",
    "pathogenic micro-organisms": "Micro-organismes pathogènes",
    "pesticide residues": "Résidus de pesticides",
    "poor or insufficient controls": "Contrôles insuffisants ou de mauvaise qualité",
    "radiation": "Radiation",
    "residues of veterinary medicinal": "Résidus de médicaments vétérinaires",
}

def telecharger_et_nettoyer_donnees(annee, semaines: List[int]) -> pd.DataFrame:
    """Downloads and cleans data from multiple weeks."""
    dfs = []
    url_template = "https://www.sirene-diffusion.fr/regia/000-rasff/{}/rasff-{}-{}.xls"

    for semaine in semaines:
        url = url_template.format(str(annee)[2:], annee, str(semaine).zfill(2))
        response = requests.get(url)
        if response.status_code == 200:
            df = pd.read_excel(BytesIO(response.content))
            dfs.append(df)
        else:
            st.error(f"Failed to download data for week {semaine}.")

    if dfs:
        df = pd.concat(dfs, ignore_index=True)
        df = nettoyer_donnees(df)
        return df
    else:
        return pd.DataFrame()

def nettoyer_donnees(df: pd.DataFrame) -> pd.DataFrame:
    """Cleans and standardizes the data."""
    # Basic cleaning steps
    df.columns = [col.lower().replace(" ", "_") for col in df.columns]
    df['date'] = pd.to_datetime(df['date_of_case'], errors='coerce')
    df = df.dropna(subset=['date'])

    # Standardize `notification_from` and `country_origin`
    df['notification_from'] = df['notification_from'].apply(lambda x: re.sub(r"\s*\(.*\)", "", str(x)).strip())
    df['country_origin'] = df['country_origin'].apply(lambda x: re.sub(r"\s*\(.*\)", "", str(x)).strip())

    # Map hazard categories to French terms
    df['hazard_category_mapped'] = df['hazard_category'].apply(lambda x: hazard_categories.get(x.strip().lower(), x))

    return df

class RASFFDashboard:
    def __init__(self, url: str):
        self.data = self.load_and_clean_data(url)

    def load_and_clean_data(self, url: str) -> pd.DataFrame:
        df = pd.read_csv(url)
        return nettoyer_donnees(df)

    def render_sidebar(self, df: pd.DataFrame) -> pd.DataFrame:
        st.sidebar.header("Filter Options")

        # Date range filter
        min_date, max_date = df['date'].min(), df['date'].max()
        date_range = st.sidebar.slider("Date Range", min_value=min_date, max_value=max_date, value=(min_date, max_date))
        filtered_df = df[(df['date'] >= date_range[0]) & (df['date'] <= date_range[1])]

        # Multiselect filters
        selected_categories = st.sidebar.multiselect("Product Categories", sorted(df['product_category'].unique()))
        selected_hazards = st.sidebar.multiselect("Hazard Categories", sorted(df['hazard_category_mapped'].unique()))
        selected_notifying_countries = st.sidebar.multiselect("Notifying Countries", sorted(df['notification_from'].unique()))
        selected_origin_countries = st.sidebar.multiselect("Country of Origin", sorted(df['country_origin'].unique()))

        # Apply filters
        if selected_categories:
            filtered_df = filtered_df[filtered_df['product_category'].isin(selected_categories)]
        if selected_hazards:
            filtered_df = filtered_df[filtered_df['hazard_category_mapped'].isin(selected_hazards)]
        if selected_notifying_countries:
            filtered_df = filtered_df[filtered_df['notification_from'].isin(selected_notifying_countries)]
        if selected_origin_countries:
            filtered_df = filtered_df[filtered_df['country_origin'].isin(selected_origin_countries)]

        return filtered_df

    def display_statistics(self, df: pd.DataFrame):
        st.header("Key Statistics")
        col1, col2, col3 = st.columns(3)
        col1.metric("Total Notifications", len(df))
        col2.metric("Unique Product Categories", df['product_category'].nunique())
        col3.metric("Unique Hazard Categories", df['hazard_category_mapped'].nunique())

    def display_visualizations(self, df: pd.DataFrame):
        st.header("Visualizations")

        # European Map for Notifying Countries
        fig_notifying_map = px.choropleth(
            df.groupby('notification_from').size().reset_index(name='count'),
            locations='notification_from',
            locationmode='country names',
            color='count',
            scope="europe",
            title="European Map of Notifying Countries",
            color_continuous_scale='Blues'
        )
        st.plotly_chart(fig_notifying_map)

        # World Map for Origin Countries
        fig_origin_map = px.choropleth(
            df.groupby('country_origin').size().reset_index(name='count'),
            locations='country_origin',
            locationmode='country names',
            color='count',
            title="World Map of Origin Countries",
            color_continuous_scale='Reds'
        )
        st.plotly_chart(fig_origin_map)

        # Bar Chart for Product Categories
        product_counts = df['product_category'].value_counts().head(10)
        fig_bar = px.bar(product_counts, x=product_counts.index, y=product_counts.values, title="Top Product Categories")
        st.plotly_chart(fig_bar)

        # Pie Chart for Top Hazard Categories
        hazard_counts = df['hazard_category_mapped'].value_counts().head(10)
        fig_pie = px.pie(hazard_counts, values=hazard_counts.values, names=hazard_counts.index, title="Top 10 Hazard Categories")
        st.plotly_chart(fig_pie)

    async def run(self):
        st.set_page_config(page_title="RASFF Data Dashboard", layout="wide")
        st.title("RASFF Data Dashboard")

        # Load initial data
        url = "https://raw.githubusercontent.com/M00N69/RASFFPORTAL/main/rasff_%202020TO30OCT2024.csv"
        df = self.data or self.load_and_clean_data(url)

        if df.empty:
            st.error("No data available. Check the data source or URL.")
            return

        # Sidebar filters
        filtered_df = self.render_sidebar(df)

        # Display statistics
        self.display_statistics(filtered_df)

        # Display visualizations
        self.display_visualizations(filtered_df)

# Run the dashboard
if __name__ == "__main__":
    dashboard = RASFFDashboard(url="https://raw.githubusercontent.com/M00N69/RASFFPORTAL/main/rasff_%202020TO30OCT2024.csv")
    import asyncio
    asyncio.run(dashboard.run())
