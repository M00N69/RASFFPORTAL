import streamlit as st
import pandas as pd
import plotly.express as px
import requests
from io import BytesIO
import asyncio
import os
from datetime import datetime, timedelta
from page.RASFFPortalLab import display_rasff_portal_lab

# Set the page configuration
st.set_page_config(page_title="RASFF Data Dashboard", layout="wide")

# URL to the main CSV file
DATA_URL = "https://raw.githubusercontent.com/M00N69/RASFFPORTAL/main/rasff_%202020TO30OCT2024.csv"
LOCAL_CSV = "rasff_data.csv"

class RASFFDashboard:
    def __init__(self):
        self.data = self.load_data()

    def load_data(self) -> pd.DataFrame:
        """Loads data from a URL or local CSV and returns it as a DataFrame."""
        if not os.path.exists(LOCAL_CSV):
            # Download the CSV file from URL if not present locally
            try:
                df = pd.read_csv(DATA_URL, parse_dates=['date_of_case'])
                df.to_csv(LOCAL_CSV, index=False)  # Save locally for caching
            except Exception as e:
                st.error(f"Failed to load data from the URL: {e}")
                return pd.DataFrame()
        else:
            df = pd.read_csv(LOCAL_CSV, parse_dates=['date_of_case'])
        
        # Standardize column names
        df.columns = [col.strip().replace(" ", "_").lower() for col in df.columns]
        
        # Ensure expected columns exist
        expected_columns = {'date_of_case', 'product_category', 'hazard_category', 'notification_from', 'country_origin'}
        missing_columns = expected_columns - set(df.columns)
        if missing_columns:
            st.error(f"Missing columns in the CSV file: {missing_columns}")
            return pd.DataFrame()  # Return an empty DataFrame if columns are missing
        
        return df

    def get_missing_weeks(self):
        """Identify missing weeks in the CSV based on the latest available week."""
        current_week = datetime.now().isocalendar()[1]
        last_available_week = current_week - 1  # Last week available for download

        # Get the weeks already in the data
        if 'date_of_case' in self.data:
            available_weeks = self.data['date_of_case'].dt.isocalendar().week.unique()
        else:
            available_weeks = []

        # Determine missing weeks
        missing_weeks = [week for week in range(1, last_available_week + 1) if week not in available_weeks]
        return missing_weeks, last_available_week

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
        df.columns = [col.strip().replace(" ", "_").lower() for col in df.columns]
        df = df.rename(columns={
            "date": "date_of_case",
            "category": "product_category",
            "hazards": "hazard_category",
            "notifying_country": "notification_from",
            "origin": "country_origin"
        })
        
        df['date_of_case'] = pd.to_datetime(df['date_of_case'], errors='coerce').dt.date
        expected_columns = ['date_of_case', 'product_category', 'hazard_category', 'notification_from', 'country_origin']
        df = df[expected_columns]
        df = df.fillna("N/A")
        return df

    def update_csv_with_latest_data(self, annee, semaines):
        """Appends the latest data for the given year and weeks to the CSV file."""
        new_data = self.telecharger_et_nettoyer_donnees(annee, semaines)
        if not new_data.empty:
            if os.path.exists(LOCAL_CSV):
                new_data.to_csv(LOCAL_CSV, mode='a', header=False, index=False)
            else:
                new_data.to_csv(LOCAL_CSV, mode='w', header=True, index=False)
            st.success("Data updated successfully!")
            self.data = self.load_data()
        else:
            st.error("No new data was downloaded to update the CSV.")

    def render_sidebar(self, df: pd.DataFrame) -> pd.DataFrame:
        st.sidebar.header("Filter Options")

        if df.empty:
            st.error("No data available to display filters.")
            return df

        selected_categories = st.sidebar.multiselect("Product Categories", sorted(df['product_category'].dropna().unique()))
        selected_hazards = st.sidebar.multiselect("Hazard Categories", sorted(df['hazard_category'].dropna().unique()))
        selected_notifying_countries = st.sidebar.multiselect("Notifying Countries", sorted(df['notification_from'].dropna().unique()))
        selected_origin_countries = st.sidebar.multiselect("Country of Origin", sorted(df['country_origin'].dropna().unique()))

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

    async def run(self):
        st.title("RASFF Data Dashboard")

        # Check for missing weeks and prompt user
        missing_weeks, last_available_week = self.get_missing_weeks()
        st.sidebar.write(f"Last available week: {last_available_week}")
        if missing_weeks:
            st.sidebar.write(f"Missing weeks: {missing_weeks}")
            if st.sidebar.button("Download Missing Weeks"):
                self.update_csv_with_latest_data(datetime.now().year, missing_weeks)

        filtered_df = self.render_sidebar(self.data)
        self.display_statistics(filtered_df)
        self.display_visualizations(filtered_df)

# Additional methods for displaying statistics and visualizations would go here

# Run the dashboard
if __name__ == "__main__":
    dashboard = RASFFDashboard()
    page = st.sidebar.radio("Select Page", ["Dashboard", "RASFF Portal Lab"])

    if page == "Dashboard":
        asyncio.run(dashboard.run())
    elif page == "RASFF Portal Lab":
        display_rasff_portal_lab()
