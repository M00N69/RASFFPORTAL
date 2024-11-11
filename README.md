# RASFF Data Dashboard - Code Explanation

This document explains the functionality and structure of the `RASFF Data Dashboard` code, which is implemented using **Streamlit** for the interface, **Plotly** for data visualizations, and **Pandas** for data handling.

## Overview

The **RASFF Data Dashboard** is a Streamlit application that loads and visualizes data from the Rapid Alert System for Food and Feed (RASFF). It displays notification counts, hazards, product categories, and country-based insights, with options to filter and visualize data interactively.

## Code Breakdown

### 1. Imports and Initial Setup

The code starts by importing the necessary libraries:
- `streamlit` for building the web interface.
- `pandas` for loading and manipulating data.
- `plotly.express` for creating interactive visualizations.
- `asyncio` for asynchronous function execution.
- `display_rasff_portal_lab` from `page.RASFFPortalLab`, which adds extra page functionality.

The Streamlit page configuration is set with:
```python
st.set_page_config(page_title="RASFF Data Dashboard", layout="wide")
2. Data Source and Loading
The URL to the CSV file is hardcoded:

python
Copier le code
DATA_URL = "https://raw.githubusercontent.com/M00N69/RASFFPORTAL/main/rasff_%202020TO30OCT2024.csv"
Data is loaded once when the RASFFDashboard class is initialized.

3. RASFFDashboard Class
The RASFFDashboard class manages the main dashboard functions. It includes:

__init__(): Initializes by calling load_data to load and preprocess data.
load_data(): Loads the CSV, parses Date of Case as a date, and standardizes column names.
render_sidebar(): Creates sidebar filters for product categories, hazard types, notifying countries, and origin countries. Filters data based on selections.
display_statistics(): Shows key statistics (total notifications, unique product categories, and hazards).
display_visualizations(): Generates visualizations including:
European map of notifying countries.
World map of origin countries.
Bar chart of top product categories.
Pie chart of top hazard categories.
4. load_data Method
Reads the CSV and preprocesses:

Parses Date of Case as a date.
Standardizes column names by converting to lowercase and replacing spaces with underscores.
5. render_sidebar Method
Displays filters in the sidebar, allowing users to filter data by:

Product Categories
Hazard Categories
Notifying Countries
Country of Origin
Filtered data is returned for visualization.

6. display_statistics Method
Shows an overview of key metrics:

Total Notifications: Total notifications in the filtered data.
Unique Product Categories: Number of unique product categories.
Unique Hazard Categories: Number of unique hazard categories.
7. display_visualizations Method
Generates four main visualizations using Plotly:

European Choropleth Map for Notifying Countries.
World Map for Origin Countries.
Top Product Categories (Bar Chart).
Top Hazard Categories (Pie Chart).
8. Main Application Execution
The main block initializes RASFFDashboard and allows page selection:

python
Copier le code
if __name__ == "__main__":
    dashboard = RASFFDashboard()
    page = st.sidebar.radio("Select Page", ["Dashboard", "RASFF Portal Lab"])

    if page == "Dashboard":
        asyncio.run(dashboard.run())
    elif page == "RASFF Portal Lab":
        display_rasff_portal_lab()
Page Navigation: Allows users to switch between "Dashboard" and "RASFF Portal Lab".
Asynchronous Execution: asyncio.run() loads the main run function, ensuring efficient loading.
Summary
The RASFF Data Dashboard provides an interactive interface to explore RASFF data. With filters, statistical summaries, and visualizations, it helps users gain insights into notifications across countries and product categories. The modular code structure improves readability, maintainability, and extensibility.
