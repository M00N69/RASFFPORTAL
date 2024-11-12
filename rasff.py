import streamlit as st
import pandas as pd
import plotly.express as px
import requests
from io import BytesIO
from datetime import datetime

# Main CSV data URL
MAIN_DATA_URL = "https://raw.githubusercontent.com/M00N69/RASFFPORTAL/main/unified_rasff_data_with_grouping.csv"

# Load the main CSV data from GitHub
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
        "meat and meat products (other than poultry)": ("Meat (Non-Poultry)", "Meat Products"),
        "cereals and bakery products": ("Cereals and Bakery Products", "Grains and Bakery"),
        # (Add more mappings as needed)
    }
    hazard_category_mapping = {
        "pathogenic micro-organisms": ("Pathogenic Micro-organisms", "Biological Hazard"),
        "mycotoxins": ("Mycotoxins", "Biological Hazard"),
        "heavy metals": ("Heavy Metals", "Chemical Hazard"),
        # (Add more mappings as needed)
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
            self.update_data_with_weeks(2024, start_week=45)

        # Sidebar filters
        filtered_df = self.render_sidebar(self.data)

        # Display statistics
        self.display_statistics(filtered_df)

        # Display visualizations
        self.display_visualizations(filtered_df)

# Run the dashboard
if __name__ == "__main__":
    st.set_page_config(page_title="RASFF Data Dashboard", layout="wide")
    dashboard = RASFFDashboard(url=MAIN_DATA_URL)
    dashboard.run()
