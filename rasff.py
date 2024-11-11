import streamlit as st
import pandas as pd
import plotly.express as px
import requests
from io import BytesIO
import asyncio
from page.RASFFPortalLab import display_rasff_portal_lab
import os

# Set the page configuration
st.set_page_config(page_title="RASFF Data Dashboard", layout="wide")

# Local file to store the RASFF data
DATA_URL = "rasff_data.csv"  

class RASFFDashboard:
    def __init__(self):
        self.data = self.load_data()

    def load_data(self) -> pd.DataFrame:
        """Loads and returns the CSV data as a DataFrame."""
        if os.path.exists(DATA_URL):
            df = pd.read_csv(DATA_URL, parse_dates=['date_of_case'])
            df.columns = [col.strip().replace(" ", "_").lower() for col in df.columns]
            
            # Check for missing expected columns
            expected_columns = {'date_of_case', 'product_category', 'hazard_category', 
                                'notification_from', 'country_origin'}
            missing_columns = expected_columns - set(df.columns)
            if missing_columns:
                st.error(f"Missing columns in the CSV file: {missing_columns}")
                return pd.DataFrame()  # Return an empty DataFrame if columns are missing
        else:
            st.warning("Data file not found. Please check the path.")
            df = pd.DataFrame()
        return df

    def telecharger_et_nettoyer_donnees(self, annee, semaines) -> pd.DataFrame:
        """Downloads and cleans data for specified year and weeks."""
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
            df = self.nettoyer_donnees(df)
            return df
        else:
            return pd.DataFrame()  # Return an empty DataFrame if no files could be downloaded

    def nettoyer_donnees(self, df: pd.DataFrame) -> pd.DataFrame:
        """Cleans the downloaded data to match the existing data format."""
        # Standardize column names and ensure compatibility with the main CSV
        df.columns = [col.strip().replace(" ", "_").lower() for col in df.columns]
        df = df.rename(columns={
            "date": "date_of_case",
            "category": "product_category",
            "hazards": "hazard_category",
            "notifying_country": "notification_from",
            "origin": "country_origin"
        })
        
        # Ensure date format is consistent and only extract the date part
        df['date_of_case'] = pd.to_datetime(df['date_of_case'], errors='coerce').dt.date
        
        # Select only relevant columns to match the CSV structure
        expected_columns = ['date_of_case', 'product_category', 'hazard_category', 
                            'notification_from', 'country_origin']
        df = df[expected_columns]
        
        # Fill any missing values with placeholder if necessary
        df = df.fillna("N/A")
        return df

    def update_csv_with_latest_data(self, annee, semaines):
        """Appends the latest data for the given year and weeks to the CSV file."""
        new_data = self.telecharger_et_nettoyer_donnees(annee, semaines)
        if not new_data.empty:
            # Append new data to CSV
            if os.path.exists(DATA_URL):
                new_data.to_csv(DATA_URL, mode='a', header=False, index=False)
            else:
                new_data.to_csv(DATA_URL, mode='w', header=True, index=False)
            st.success("Data updated successfully!")
            # Reload data to reflect the new entries in the dashboard
            self.data = self.load_data()
        else:
            st.error("No new data was downloaded to update the CSV.")

    def render_sidebar(self, df: pd.DataFrame) -> pd.DataFrame:
        st.sidebar.header("Filter Options")

        if df.empty:
            st.error("No data available to display filters.")
            return df

        # Safely attempt to access columns; if missing, skip filtering
        selected_categories = st.sidebar.multiselect("Product Categories", sorted(df['product_category'].dropna().unique())) if 'product_category' in df else []
        selected_hazards = st.sidebar.multiselect("Hazard Categories", sorted(df['hazard_category'].dropna().unique())) if 'hazard_category' in df else []
        selected_notifying_countries = st.sidebar.multiselect("Notifying Countries", sorted(df['notification_from'].dropna().unique())) if 'notification_from' in df else []
        selected_origin_countries = st.sidebar.multiselect("Country of Origin", sorted(df['country_origin'].dropna().unique())) if 'country_origin' in df else []

        filtered_df = df.copy()
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
        col2.metric("Unique Product Categories", df['product_category'].nunique() if 'product_category' in df else 0)
        col3.metric("Unique Hazard Categories", df['hazard_category'].nunique() if 'hazard_category' in df else 0)

    def display_visualizations(self, df: pd.DataFrame):
        st.header("Visualizations")

        if 'notification_from' in df:
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

        if 'country_origin' in df:
            fig_origin_map = px.choropleth(
                df.groupby('country_origin').size().reset_index(name='count'),
                locations='country_origin',
                locationmode='country names',
                color='count',
                title="World Map of Origin Countries",
                color_continuous_scale='Reds'
            )
            st.plotly_chart(fig_origin_map)

        if 'product_category' in df:
            product_counts = df['product_category'].value_counts().head(10)
            fig_bar = px.bar(product_counts, x=product_counts.index, y=product_counts.values, title="Top Product Categories")
            st.plotly_chart(fig_bar)

        if 'hazard_category' in df:
            hazard_counts = df['hazard_category'].value_counts().head(10)
            fig_pie = px.pie(hazard_counts, values=hazard_counts.values, names=hazard_counts.index, title="Top 10 Hazard Categories")
            st.plotly_chart(fig_pie)

    async def run(self):
        st.title("RASFF Data Dashboard")

        # Sidebar for updating data
        with st.sidebar:
            st.header("Update Data")
            annee = st.number_input("Year", min_value=2000, max_value=2100, value=2024, step=1)
            semaines = st.text_input("Weeks (comma-separated)", "1,2,3")  # Input weeks as "1,2,3"
            semaines = [int(week.strip()) for week in semaines.split(",")]

            if st.button("Update Data"):
                self.update_csv_with_latest_data(annee, semaines)

        # Sidebar filters
        filtered_df = self.render_sidebar(self.data)

        # Display statistics
        self.display_statistics(filtered_df)

        # Display visualizations
        self.display_visualizations(filtered_df)

# Run the dashboard or load the additional lab page
if __name__ == "__main__":
    dashboard = RASFFDashboard()
    page = st.sidebar.radio("Select Page", ["Dashboard", "RASFF Portal Lab"])

    if page == "Dashboard":
        asyncio.run(dashboard.run())
    elif page == "RASFF Portal Lab":
        display_rasff_portal_lab()
