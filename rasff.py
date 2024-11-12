import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime

# Load main CSV data from GitHub
@st.cache_data
def load_data(url: str) -> pd.DataFrame:
    try:
        df = pd.read_csv(url, parse_dates=['Date of Case'])
        df.columns = [col.strip().replace(" ", "_").lower() for col in df.columns]  # Standardize column names
        return df
    except Exception as e:
        st.error(f"Failed to load data: {e}")
        return pd.DataFrame()

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

# Main class for the RASFF Dashboard
class RASFFDashboard:
    def __init__(self, url: str):
        raw_data = load_data(url)
        self.data = apply_mappings(raw_data)

    def render_sidebar(self, df: pd.DataFrame) -> pd.DataFrame:
        st.sidebar.header("Filter Options")

        # Date range filter using date_input
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

        # Sidebar filters
        filtered_df = self.render_sidebar(self.data)

        # Display statistics
        self.display_statistics(filtered_df)

        # Display visualizations
        self.display_visualizations(filtered_df)

# Run the dashboard
if __name__ == "__main__":
    st.set_page_config(page_title="RASFF Data Dashboard", layout="wide")
    dashboard = RASFFDashboard(url="https://raw.githubusercontent.com/M00N69/RASFFPORTAL/main/unified_rasff_data_with_grouping.csv")
    dashboard.run()
