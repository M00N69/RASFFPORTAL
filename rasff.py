import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np
from scipy.stats import chi2_contingency
from io import BytesIO

# Assurez-vous que `set_page_config` est appelé ici, immédiatement après les imports.
st.set_page_config(page_title="RASFF Data Dashboard", layout="wide")

@st.cache_data
def load_data(url: str) -> pd.DataFrame:
    df = pd.read_csv(url, parse_dates=['Date of Case'])
    df.columns = [col.strip().replace(" ", "_").lower() for col in df.columns]
    return df

# Télécharger le fichier exporté
def export_data(df: pd.DataFrame):
    csv = df.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="Télécharger les données filtrées (CSV)",
        data=csv,
        file_name='filtered_data.csv',
        mime='text/csv',
    )

def correlation_analysis(df: pd.DataFrame, var1: str, var2: str):
    contingency_table = pd.crosstab(df[var1], df[var2])
    chi2, p, _, _ = chi2_contingency(contingency_table)
    return chi2, p

def render_main_page(df: pd.DataFrame):
    st.title("Tableau de Bord RASFF")

    # Filtres interactifs
    date_range = st.sidebar.date_input("Filtrer par date", [df['date_of_case'].min(), df['date_of_case'].max()])
    df_filtered = df[(df['date_of_case'] >= pd.to_datetime(date_range[0])) & (df['date_of_case'] <= pd.to_datetime(date_range[1]))]

    # Résumé des données
    st.header("Résumé des Données")
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Notifications", len(df_filtered))
    col2.metric("Catégories de Produits", df_filtered['product_category'].nunique())
    col3.metric("Catégories de Dangers", df_filtered['hazard_category'].nunique())

    # Options de colonnes
    columns_to_display = st.multiselect("Colonnes à afficher", options=df.columns, default=df.columns)

    # Tableau de données avec pagination
    st.dataframe(df_filtered[columns_to_display], use_container_width=True)
    export_data(df_filtered)

def render_correlation_page(df: pd.DataFrame):
    st.title("Analyse des Corrélations")
    var1 = st.selectbox("Choisir la première variable catégorielle", df.select_dtypes('object').columns)
    var2 = st.selectbox("Choisir la deuxième variable catégorielle", df.select_dtypes('object').columns)

    chi2, p_value = correlation_analysis(df, var1, var2)
    st.write(f"Test du Chi-carré entre **{var1}** et **{var2}**:")
    st.write(f"Chi² = {chi2:.2f}, p-valeur = {p_value:.4f}")

    if p_value < 0.05:
        st.success("Corrélation significative détectée!")
    else:
        st.warning("Pas de corrélation significative.")

    # Carte thermique des corrélations
    st.header("Carte Thermique des Corrélations")
    heatmap_data = df.groupby([var1, var2]).size().unstack(fill_value=0)
    fig = px.imshow(heatmap_data, text_auto=True, title="Carte Thermique des Fréquences")
    st.plotly_chart(fig, use_container_width=True)

    # Graphique à barres
    st.header("Graphique à Barres des Fréquences")
    bar_data = df[var1].value_counts()
    fig_bar = px.bar(bar_data, x=bar_data.index, y=bar_data.values, labels={'y': 'Fréquence', 'x': var1}, title=f"Distribution des {var1}")
    st.plotly_chart(fig_bar, use_container_width=True)

def main():
    st.sidebar.title("Navigation")
    page = st.sidebar.radio("Aller à", ["Tableau Principal", "Analyse des Corrélations"])

    df = load_data("https://raw.githubusercontent.com/M00N69/RASFFPORTAL/main/unified_rasff_data_with_grouping.csv")

    if page == "Tableau Principal":
        render_main_page(df)
    elif page == "Analyse des Corrélations":
        render_correlation_page(df)

if __name__ == "__main__":
    main()
