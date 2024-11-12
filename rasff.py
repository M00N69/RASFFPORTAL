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
        # Add mappings here...
    }

    hazard_category_mapping = {
        # Add mappings here...
    }

    # Map Product Category
    df[['prodcat', 'groupprod']] = df['product_category'].apply(
        lambda x: pd.Series(product_category_mapping.get(x.lower(), ("Unknown", "Unknown")))
    )

    # Map Hazard Category
    df[['hazcat', 'grouphaz']] = df['hazard_category'].apply(
        lambda x: pd.Series(hazard_category_mapping.get(x.lower(), ("Unknown", "Unknown")))
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

