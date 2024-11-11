import streamlit as st
import pandas as pd

# URL to the main CSV file
DATA_URL = "https://raw.githubusercontent.com/M00N69/RASFFPORTAL/main/rasff_%202020TO30OCT2024.csv"

class RASFFDashboard:
    def __init__(self):
        self.data = self.load_data()
        
        # Inspect the loaded data
        if not self.data.empty:
            st.write("Data loaded and columns standardized. Here are the first few rows:")
            st.write(self.data.head())
            st.write("Columns in the loaded data:", self.data.columns)
        else:
            st.warning("Data failed to load or is empty.")
    
    def load_data(self) -> pd.DataFrame:
        """Loads data from a URL and returns it as a standardized DataFrame."""
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
        
        return df
