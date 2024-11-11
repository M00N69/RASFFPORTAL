import streamlit as st
import pandas as pd

# URL to the main CSV file
DATA_URL = "https://raw.githubusercontent.com/M00N69/RASFFPORTAL/main/rasff_%202020TO30OCT2024.csv"

class RASFFDashboard:
    def __init__(self):
        self.data = self.load_data()
        
        # Inspect the loaded data
        if not self.data.empty:
            st.write("Data loaded successfully with standardized columns.")
            st.write("Here are the first few rows after parsing dates and handling missing values:")
            st.write(self.data.head())
            st.write("Columns in the loaded data:", list(self.data.columns))
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
        
        return df

# Instantiate the class to run the loading, date parsing, and missing value handling
if __name__ == "__main__":
    st.title("RASFF Data Dashboard - Step 2: Parse Dates and Handle Missing Values")
    dashboard = RASFFDashboard()

