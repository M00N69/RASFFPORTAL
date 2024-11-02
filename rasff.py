import streamlit as st
import pandas as pd
import plotly.express as px
from io import BytesIO
import requests
import datetime
from typing import List
import re

# Load lists directly from GitHub for full data consistency
def load_list_from_github(filename: str) -> pd.DataFrame:
    base_url = "https://raw.githubusercontent.com/M00N69/RASFFPORTAL/main/"
    url = f"{base_url}{filename}"
    return pd.read_csv(url, header=None)[0].tolist()

hazard_categories = load_list_from_github("hazard_categories.py")
notifying_countries = load_list_from_github("notifying_countries.py")
origin_countries = load_list_from_github("origin_countries.py")
product_categories = load_list_from_github("product_categories.py")

# Function to download and clean data from multiple weeks
def telecharger_et_nettoyer_donnees(annee, semaines: List[int]) -> pd.DataFrame:
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

# Function to clean the main data
def nettoyer_donnees(df: pd.DataFrame) -> pd.DataFrame:
    df.columns = [col.lower().replace(" ", "_") for col in df.columns]
    df['date'] = pd.to_datetime(df['date_of_case'], errors='coerce')
    df = df.dropna(subset=['date'])

    # Standardize `notification_from` and `country_origin`
    df['notification_from'] = df['notification_from'].apply(lambda x: re.sub(r"\s*\(.*\)", "", str(x)).strip())
    df['country_origin'] = df['country_origin'].apply(lambda x: re.sub(r"\s*\(.*\)", "", str(x)).strip())

    return df

# Define the main dashboard class
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
        selected_hazards = st.sidebar.multiselect("Hazard Categories", sorted(df['hazard_category'].unique()))
        selected_notifying_countries = st.sidebar.multiselect("Notifying Countries", sorted(df['notification_from'].unique()))
        selected_origin_countries = st.sidebar.multiselect("Country of Origin", sorted(df['country_origin'].unique()))

        # Apply filters
        if selected_categories:
            filtered_df = filtered_df[filtered_df['product_category'].isin(selected_categories)]
        if selected_hazards:
            filtered_df = filtered_df[filtered_df['hazard_category'].isin(selected_hazards)]
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
        col3.metric("Unique Hazard Categories", df['hazard_category'].nunique())

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
        hazard_counts = df['hazard_category'].value_counts().head(10)
        fig_pie = px.pie(hazard_counts, values=hazard_counts.values, names=hazard_counts.index, title="Top 10 Hazard Categories")
        st.plotly_chart(fig_pie)

    async def run(self):
        st.set_page_config(page_title="RASFF Data Dashboard", layout="wide")
        st.title("RASFF Data Dashboard")

        # Load initial data
        url = "https://raw.githubusercontent.com/M00N69/RASFFPORTAL/main/rasff_%202020TO30OCT2024.csv"
        df = self.data if not self.data.empty else self.load_and_clean_data(url)

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
