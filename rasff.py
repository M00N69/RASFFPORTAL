import streamlit as st
import pandas as pd
import datetime
from typing import List
from io import BytesIO
import requests
import plotly.express as px

# Hazard category mapping
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

class RASFFDashboard:
    def __init__(self):
        self.data = None

    def load_and_clean_data(self, url: str) -> pd.DataFrame:
        # Load the CSV data
        df = pd.read_csv(url)
        
        # Convert 'Date of Case' to datetime with a custom date format
        df['date'] = pd.to_datetime(df['Date of Case'], format='%b %d, %Y', errors='coerce')
        
        # Drop rows with NaT dates
        df = df.dropna(subset=['date'])
        
        # Standardize column names for easier access
        df.columns = [col.lower().replace(" ", "_") for col in df.columns]
        
        # Fill missing values with placeholders to avoid KeyError issues
        df['hazard_substance'].fillna("Unknown", inplace=True)
        df['hazard_category'].fillna("Unknown", inplace=True)
        df['product_category'].fillna("Unknown", inplace=True)
        df['notification_from'].fillna("Unknown", inplace=True)
        df['country_origin'].fillna("Unknown", inplace=True)

        # Map hazard_category to its French equivalent if present in hazard_categories dictionary
        df['hazard_category_mapped'] = df['hazard_category'].map(hazard_categories).fillna(df['hazard_category'])

        return df

    def render_sidebar(self, df: pd.DataFrame) -> pd.DataFrame:
        """Displays the sidebar filters."""
        st.sidebar.header("Filter Options")

        # Set default min_date and max_date
        min_date = df['date'].min()
        max_date = df['date'].max()

        # Date range slider
        date_range = st.sidebar.slider(
            "Date Range",
            min_value=min_date.date(),
            max_value=max_date.date(),
            value=(min_date.date(), max_date.date())
        )

        # Filter by date range
        filtered_df = df[(df['date'] >= pd.to_datetime(date_range[0])) & (df['date'] <= pd.to_datetime(date_range[1]))]

        # Multiselect filters
        selected_categories = st.sidebar.multiselect("Product Categories", sorted(df['product_category'].unique()))
        selected_hazards = st.sidebar.multiselect("Hazard Categories", sorted(df['hazard_category_mapped'].unique()))
        selected_countries = st.sidebar.multiselect("Notifying Countries", sorted(df['notification_from'].unique()))

        # Apply additional filters
        if selected_categories:
            filtered_df = filtered_df[filtered_df['product_category'].isin(selected_categories)]
        if selected_hazards:
            filtered_df = filtered_df[filtered_df['hazard_category_mapped'].isin(selected_hazards)]
        if selected_countries:
            filtered_df = filtered_df[filtered_df['notification_from'].isin(selected_countries)]

        return filtered_df

    def display_statistics(self, df: pd.DataFrame):
        st.header("Key Statistics")
        col1, col2, col3 = st.columns(3)
        col1.metric("Total Notifications", len(df))
        col2.metric("Unique Product Categories", df['product_category'].nunique())
        col3.metric("Unique Hazard Categories", df['hazard_category_mapped'].nunique())

    def display_visualizations(self, df: pd.DataFrame):
        st.header("Visualizations")

        # Notification distribution by country
        fig_map = px.choropleth(
            df.groupby('notification_from').size().reset_index(name='count'),
            locations='notification_from',
            locationmode='country names',
            color='count',
            title="Notifications by Notifying Country",
            color_continuous_scale='Viridis'
        )
        st.plotly_chart(fig_map)

    async def run(self):
        st.set_page_config(page_title="RASFF Dashboard", layout="wide")
        st.title("RASFF Data Dashboard")

        # Load data
        url = "https://raw.githubusercontent.com/M00N69/RASFFPORTAL/main/rasff_%202020TO30OCT2024.csv"
        df = self.load_and_clean_data(url)

        if df.empty:
            st.error("No data available. Check the data source or URL.")
            return

        # Render filters in the sidebar
        filtered_df = self.render_sidebar(df)

        # Display statistics
        self.display_statistics(filtered_df)

        # Display visualizations
        self.display_visualizations(filtered_df)

# Run the dashboard
if __name__ == "__main__":
    dashboard = RASFFDashboard()
    import asyncio
    asyncio.run(dashboard.run())
