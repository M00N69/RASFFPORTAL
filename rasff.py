import streamlit as st
import pandas as pd

# URL to the main CSV file
DATA_URL = "https://raw.githubusercontent.com/M00N69/RASFFPORTAL/main/rasff_%202020TO30OCT2024.csv"

class RASFFDashboard:
    def __init__(self):
        self.data = self.load_data()
        
        # Check if data loaded correctly
        if not self.data.empty:
            self.filtered_data = self.render_sidebar(self.data)
            self.display_statistics(self.filtered_data)
        else:
            st.warning("Data failed to load or is empty.")
    
    def load_data(self) -> pd.DataFrame:
        """Loads data from a URL, standardizes columns, parses dates, and handles missing values."""
        try:
            df = pd.read_csv(DATA_URL)
        except Exception as e:
            st.error(f"Failed to load data from the URL: {e}")
            return pd.DataFrame()
        
        # Standardize column names
        column_mapping = {
            "Date of Case": "date_of_case",
            "Reference": "reference",
            "Notification From": "notification_from",
            "Country Origin": "country_origin",
            "Product": "product",
            "Product Category": "product_category",
            "Hazard Substance": "hazard_substance",
            "Hazard Category": "hazard_category"
        }
        df = df.rename(columns=column_mapping)
        
        # Parse the date_of_case column as a date
        if 'date_of_case' in df.columns:
            df['date_of_case'] = pd.to_datetime(df['date_of_case'], errors='coerce')
        
        # Handle missing values by filling with "N/A" for critical columns
        critical_columns = ['date_of_case', 'notification_from', 'country_origin', 'product_category', 'hazard_category']
        df[critical_columns] = df[critical_columns].fillna("N/A")
        
        # Clean up the hazard_category column
        df['hazard_category'] = df['hazard_category'].apply(self.clean_hazard_category)
        
        return df
    
    def clean_hazard_category(self, hazard):
        """Split and return the primary hazard category."""
        # Split on ";" and return the first unique category in case of multiple values
        if pd.isna(hazard) or hazard == "N/A":
            return "N/A"
        
        # Take only unique values
        unique_hazards = set(hazard.split(";"))
        
        # Option 1: Join them back for display, or just take the first category
        return "; ".join(sorted(unique_hazards))  # sorted to ensure consistent order in lists

    def render_sidebar(self, df: pd.DataFrame) -> pd.DataFrame:
        """Set up filters in the sidebar and return filtered data."""
        st.sidebar.header("Filter Options")
        
        # Sidebar multiselect filters
        selected_categories = st.sidebar.multiselect("Product Categories", sorted(df['product_category'].dropna().unique()))
        selected_hazards = st.sidebar.multiselect("Hazard Categories", sorted(df['hazard_category'].dropna().unique()))
        selected_notifying_countries = st.sidebar.multiselect("Notifying Countries", sorted(df['notification_from'].dropna().unique()))
        selected_origin_countries = st.sidebar.multiselect("Country of Origin", sorted(df['country_origin'].dropna().unique()))

        # Apply filters
        filtered_df = df.copy()
        if selected_categories:
            filtered_df = filtered_df[filtered_df['product_category'].isin(selected_categories)]
        if selected_hazards:
            filtered_df = filtered_df[filtered_df['hazard_category'].isin(selected_hazards)]
        if selected_notifying_countries:
            filtered_df = filtered_df[filtered_df['notification_from'].isin(selected_notifying_countries)]
        if selected_origin_countries:
            filtered_df = filtered_df[filtered_df['country_origin'].isin(selected_origin_countries)]
        
        # Display a message if the filtered data is empty
        if filtered_df.empty:
            st.warning("No data matches the selected filters.")
        
        return filtered_df

    def display_statistics(self, df: pd.DataFrame):
        """Display key statistics based on the filtered data."""
        st.header("Key Statistics")

        if df.empty:
            st.warning("No data available for statistics.")
            return
        
        col1, col2, col3 = st.columns(3)
        
        total_notifications = len(df)
        unique_products = df['product_category'].nunique() if 'product_category' in df.columns else 0
        unique_hazards = df['hazard_category'].nunique() if 'hazard_category' in df.columns else 0
        
        col1.metric("Total Notifications", total_notifications)
        col2.metric("Unique Product Categories", unique_products)
        col3.metric("Unique Hazard Categories", unique_hazards)

# Instantiate the class to run the filtering and display process
if __name__ == "__main__":
    st.title("RASFF Data Dashboard - Hazard Category Grouping")
    dashboard = RASFFDashboard()
