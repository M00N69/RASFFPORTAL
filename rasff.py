import streamlit as st
import pandas as pd
import plotly.express as px
import requests
from io import BytesIO
from datetime import datetime

# Configure la page Streamlit (doit être exécuté en premier)
st.set_page_config(page_title="RASFF Data Dashboard", layout="wide")

# Main CSV data URL
MAIN_DATA_URL = "https://raw.githubusercontent.com/M00N69/RASFFPORTAL/main/unified_rasff_data_with_grouping.csv"

@st.cache_data
def load_data(url: str) -> pd.DataFrame:
    try:
        df = pd.read_csv(url, parse_dates=['Date of Case'])
        df.columns = [col.strip().replace(" ", "_").lower() for col in df.columns]  # Standardize column names
        return df
    except Exception as e:
        st.error(f"Failed to load data: {e}")
        return pd.DataFrame()

# Standard column names expected in the main data
expected_columns = [
    "date_of_case", "reference", "notification_from", "country_origin", 
    "product", "product_category", "hazard_substance", "hazard_category",
    "prodcat", "groupprod", "hazcat", "grouphaz"
]

# Column mapping for transforming weekly file structure to match main data
weekly_column_mapping = {
    "Date of Case": "date_of_case",
    "Reference": "reference",
    "Notification From": "notification_from",
    "Country Origin": "country_origin",
    "Product": "product",
    "Product Category": "product_category",
    "Hazard Substance": "hazard_substance",
    "Hazard Category": "hazard_category"
}

# Function to download and clean weekly data
def download_and_clean_weekly_data(year, weeks):
    url_template = "https://www.sirene-diffusion.fr/regia/000-rasff/{}/rasff-{}-{}.xls"
    dfs = []
    for week in weeks:
        url = url_template.format(str(year)[2:], year, str(week).zfill(2))
        response = requests.get(url)
        if response.status_code == 200:
            try:
                # Attempt to read and transform the weekly data
                df = pd.read_excel(BytesIO(response.content))
                
                # Rename columns according to the mapping
                df = df.rename(columns=weekly_column_mapping)
                
                # Ensure all expected columns are present, filling missing columns with None
                for col in expected_columns:
                    if col not in df.columns:
                        df[col] = None  # Add missing column with default None values
                        
                # Select and reorder columns to match the main DataFrame
                df = df[expected_columns]
                
                # Apply category mappings
                df = apply_mappings(df)
                
                dfs.append(df)
                st.info(f"Data for week {week} loaded successfully.")
            except Exception as e:
                st.warning(f"Failed to process data for week {week}: {e}")
        else:
            st.warning(f"Data for week {week} could not be downloaded.")
    
    if dfs:
        return pd.concat(dfs, ignore_index=True)
    else:
        return pd.DataFrame()  # Return an empty DataFrame if no files could be downloaded

# Apply category mappings
def apply_mappings(df: pd.DataFrame) -> pd.DataFrame:
    product_category_mapping = {
    "alcoholic beverages": ("Alcoholic Beverages", "Beverages"),
    "animal by-products": ("Animal By-products", "Animal Products"),
    "bivalve molluscs and products thereof": ("Bivalve Molluscs", "Seafood"),
    "cephalopods and products thereof": ("Cephalopods", "Seafood"),
    "cereals and bakery products": ("Cereals and Bakery Products", "Grains and Bakery"),
    "cocoa and cocoa preparations, coffee and tea": ("Cocoa, Coffee, and Tea", "Beverages"),
    "compound feeds": ("Compound Feeds", "Animal Feed"),
    "confectionery": ("Confectionery", "Grains and Bakery"),
    "crustaceans and products thereof": ("Crustaceans", "Seafood"),
    "dietetic foods, food supplements and fortified foods": ("Dietetic Foods and Supplements", "Specialty Foods"),
    "eggs and egg products": ("Eggs and Egg Products", "Animal Products"),
    "fats and oils": ("Fats and Oils", "Fats and Oils"),
    "feed additives": ("Feed Additives", "Animal Feed"),
    "feed materials": ("Feed Materials", "Animal Feed"),
    "feed premixtures": ("Feed Premixtures", "Animal Feed"),
    "fish and fish products": ("Fish and Fish Products", "Seafood"),
    "food additives and flavourings": ("Food Additives and Flavourings", "Additives"),
    "food contact materials": ("Food Contact Materials", "Packaging"),
    "fruits and vegetables": ("Fruits and Vegetables", "Fruits and Vegetables"),
    "gastropods": ("Gastropods", "Seafood"),
    "herbs and spices": ("Herbs and Spices", "Spices"),
    "honey and royal jelly": ("Honey and Royal Jelly", "Specialty Foods"),
    "ices and desserts": ("Ices and Desserts", "Grains and Bakery"),
    "live animals": ("Live Animals", "Animal Products"),
    "meat and meat products (other than poultry)": ("Meat (Non-Poultry)", "Meat Products"),
    "milk and milk products": ("Milk and Milk Products", "Dairy"),
    "natural mineral waters": ("Natural Mineral Waters", "Beverages"),
    "non-alcoholic beverages": ("Non-Alcoholic Beverages", "Beverages"),
    "nuts, nut products and seeds": ("Nuts and Seeds", "Seeds and Nuts"),
    "other food product / mixed": ("Mixed Food Products", "Other"),
    "pet food": ("Pet Food", "Animal Feed"),
    "plant protection products": ("Plant Protection Products", "Additives"),
    "poultry meat and poultry meat products": ("Poultry Meat", "Meat Products"),
    "prepared dishes and snacks": ("Prepared Dishes and Snacks", "Prepared Foods"),
    "soups, broths, sauces and condiments": ("Soups, Broths, Sauces", "Prepared Foods"),
    "water for human consumption (other)": ("Water (Human Consumption)", "Beverages"),
    "wine": ("Wine", "Beverages")
    }
    hazard_category_mapping = {
    "GMO / novel food": ("GMO / Novel Food", "Food Composition"),
    "TSEs": ("Transmissible Spongiform Encephalopathies (TSEs)", "Biological Hazard"),
    "adulteration / fraud": ("Adulteration / Fraud", "Food Fraud"),
    "allergens": ("Allergens", "Biological Hazard"),
    "biological contaminants": ("Biological Contaminants", "Biological Hazard"),
    "biotoxins (other)": ("Biotoxins", "Biological Hazard"),
    "chemical contamination (other)": ("Chemical Contamination", "Chemical Hazard"),
    "composition": ("Composition", "Food Composition"),
    "environmental pollutants": ("Environmental Pollutants", "Chemical Hazard"),
    "feed additives": ("Feed Additives", "Chemical Hazard"),
    "food additives and flavourings": ("Food Additives and Flavourings", "Additives"),
    "foreign bodies": ("Foreign Bodies", "Physical Hazard"),
    "genetically modified": ("Genetically Modified", "Food Composition"),
    "heavy metals": ("Heavy Metals", "Chemical Hazard"),
    "industrial contaminants": ("Industrial Contaminants", "Chemical Hazard"),
    "labelling absent/incomplete/incorrect": ("Labelling Issues", "Food Fraud"),
    "migration": ("Migration", "Chemical Hazard"),
    "mycotoxins": ("Mycotoxins", "Biological Hazard"),
    "natural toxins (other)": ("Natural Toxins", "Biological Hazard"),
    "non-pathogenic micro-organisms": ("Non-Pathogenic Micro-organisms", "Biological Hazard"),
    "not determined (other)": ("Not Determined", "Other"),
    "novel food": ("Novel Food", "Food Composition"),
    "organoleptic aspects": ("Organoleptic Aspects", "Other"),
    "packaging defective / incorrect": ("Packaging Issues", "Physical Hazard"),
    "parasitic infestation": ("Parasitic Infestation", "Biological Hazard"),
    "pathogenic micro-organisms": ("Pathogenic Micro-organisms", "Biological Hazard"),
    "pesticide residues": ("Pesticide Residues", "Pesticide Hazard"),
    "poor or insufficient controls": ("Insufficient Controls", "Food Fraud"),
    "radiation": ("Radiation", "Physical Hazard"),
    "residues of veterinary medicinal": ("Veterinary Medicinal Residues", "Chemical Hazard")
    }
    
    # Map Product Category
    df[['prodcat', 'groupprod']] = df['product_category'].apply(
        lambda x: pd.Series(product_category_mapping.get(str(x).lower(), ("Unknown", "Unknown")))
    )

    # Map Hazard Category
    df[['hazcat', 'grouphaz']] = df['hazard_category'].apply(
        lambda x: pd.Series(hazard_category_mapping.get(str(x).lower(), ("Unknown", "Unknown")))
    )

    return df

# Main RASFF Dashboard class
class RASFFDashboard:
    def __init__(self, url: str):
        raw_data = load_data(url)
        self.data = apply_mappings(raw_data)

    def update_data_with_weeks(self, year, start_week):
        # Determine weeks to download based on start week
        current_week = datetime.now().isocalendar()[1]
        weeks_to_download = list(range(start_week, current_week))
        new_data = download_and_clean_weekly_data(year, weeks_to_download)
        if not new_data.empty:
            self.data = pd.concat([self.data, new_data], ignore_index=True)
            st.success("Data updated with new weekly entries.")
        else:
            st.info("No new data was available for the specified weeks.")

    def render_sidebar(self, df: pd.DataFrame) -> pd.DataFrame:
        st.sidebar.header("Filter Options")

        # Date range filter
        min_date = df['date_of_case'].min().date()
        max_date = df['date_of_case'].max().date()
        start_date, end_date = st.sidebar.date_input(
            "Date Range", 
            [min_date, max_date]
        )
        filtered_df = df[(df['date_of_case'] >= pd.to_datetime(start_date)) & (df['date_of_case'] <= pd.to_datetime(end_date))]

        # Multiselect filters for grouped categories
        selected_prod_groups = st.sidebar.multiselect("Product Groups", sorted(df['groupprod'].dropna().unique()))
        selected_hazard_groups = st.sidebar.multiselect("Hazard Groups", sorted(df['grouphaz'].dropna().unique()))
        selected_notifying_countries = st.sidebar.multiselect("Notifying Countries", sorted(df['notification_from'].dropna().unique()))
        selected_origin_countries = st.sidebar.multiselect("Country of Origin", sorted(df['country_origin'].dropna().unique()))

        # Apply filters
        if selected_prod_groups:
            filtered_df = filtered_df[filtered_df['groupprod'].isin(selected_prod_groups)]
        if selected_hazard_groups:
            filtered_df = filtered_df[filtered_df['grouphaz'].isin(selected_hazard_groups)]
        if selected_notifying_countries:
            filtered_df = filtered_df[filtered_df['notification_from'].isin(selected_notifying_countries)]
        if selected_origin_countries:
            filtered_df = filtered_df[filtered_df['country_origin'].isin(selected_origin_countries)]

        return filtered_df

    def display_statistics(self, df: pd.DataFrame):
        st.header("Key Statistics")
        col1, col2, col3 = st.columns(3)
        col1.metric("Total Notifications", len(df))
        col2.metric("Unique Product Categories", df['prodcat'].nunique())
        col3.metric("Unique Hazard Categories", df['hazcat'].nunique())

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
        product_counts = df['prodcat'].value_counts().head(10)
        fig_bar = px.bar(product_counts, x=product_counts.index, y=product_counts.values, title="Top Product Categories")
        st.plotly_chart(fig_bar)

        # Pie Chart for Top Hazard Categories
        hazard_counts = df['hazcat'].value_counts().head(10)
        fig_pie = px.pie(hazard_counts, values=hazard_counts.values, names=hazard_counts.index, title="Top 10 Hazard Categories")
        st.plotly_chart(fig_pie)

    def run(self):
        st.title("RASFF Data Dashboard")

        # Update data button
        st.sidebar.header("Update Data")
        if st.sidebar.button("Update Data with New Weeks"):
            self.update_data_with_weeks(2024, start_week=44)

        # Sidebar filters
        filtered_df = self.render_sidebar(self.data)

        # Display statistics
        self.display_statistics(filtered_df)

        # Display visualizations
        self.display_visualizations(filtered_df)

# Lancement du tableau de bord
if __name__ == "__main__":
    dashboard = RASFFDashboard(url=MAIN_DATA_URL)
    dashboard.run()
