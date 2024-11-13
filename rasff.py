import streamlit as st
import pandas as pd
import plotly.express as px
import requests
from io import BytesIO
from datetime import datetime
from scipy.stats import chi2_contingency
import numpy as np

# URL principal pour les données consolidées
MAIN_DATA_URL = "https://raw.githubusercontent.com/M00N69/RASFFPORTAL/main/unified_rasff_data_with_grouping.csv"

@st.cache_data
def load_data(url: str) -> pd.DataFrame:
    """
    Charge les données principales depuis l'URL donnée et nettoie les colonnes.
    """
    try:
        df = pd.read_csv(url, parse_dates=['Date of Case'])
        df.columns = [col.strip().replace(" ", "_").lower() for col in df.columns]
        return df
    except Exception as e:
        st.error(f"Erreur lors du chargement des données : {e}")
        return pd.DataFrame()

def apply_mappings(df: pd.DataFrame) -> pd.DataFrame:
    """
    Applique le mapping pour les catégories de produits et de dangers.
    """
    product_category_mapping = {
        "poultry meat and poultry meat products": ("Poultry", "Meat"),
        "fish and fish products": ("Fish", "Seafood"),
        "fruits and vegetables": ("Fruits", "Vegetables"),
    }
    hazard_category_mapping = {
        "pathogenic micro-organisms": ("Pathogens", "Biological"),
        "heavy metals": ("Heavy Metals", "Chemical"),
    }
    df[['prodcat', 'groupprod']] = df['product_category'].apply(
        lambda x: pd.Series(product_category_mapping.get(str(x).lower(), ("Unknown", "Unknown")))
    )
    df[['hazcat', 'grouphaz']] = df['hazard_category'].apply(
        lambda x: pd.Series(hazard_category_mapping.get(str(x).lower(), ("Unknown", "Unknown")))
    )
    return df

def clean_and_format_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    Nettoie et formate les données principales.
    """
    df = df.dropna(subset=['date_of_case'])
    df['date_of_case'] = pd.to_datetime(df['date_of_case'], errors='coerce')
    df = apply_mappings(df)
    return df
def download_weekly_data(year, weeks):
    """
    Télécharge et nettoie les données hebdomadaires pour les semaines spécifiées.
    """
    url_template = "https://www.sirene-diffusion.fr/regia/000-rasff/{}/rasff-{}-{}.xls"
    dfs = []
    for week in weeks:
        url = url_template.format(str(year)[2:], year, str(week).zfill(2))
        try:
            response = requests.get(url)
            if response.status_code == 200:
                df = pd.read_excel(BytesIO(response.content))
                df = clean_and_format_data(df)
                dfs.append(df)
            else:
                st.warning(f"Les données de la semaine {week} ne sont pas disponibles.")
        except Exception as e:
            st.warning(f"Erreur lors du traitement de la semaine {week} : {e}")
    return pd.concat(dfs, ignore_index=True) if dfs else pd.DataFrame()
def render_filtered_table(df: pd.DataFrame):
    """
    Affiche un tableau filtré avec exportation et résumé.
    """
    st.subheader("Tableau des Données Filtrées")
    subset_columns = st.checkbox("Afficher uniquement les colonnes principales", value=True)
    display_columns = ['date_of_case', 'notification_from', 'country_origin', 'prodcat', 'hazcat'] if subset_columns else df.columns

    # Résumé des données
    st.write(f"**Nombre d'enregistrements affichés : {len(df)}**")
    st.write(f"- **Catégories de produits uniques** : {df['prodcat'].nunique()}")
    st.write(f"- **Catégories de dangers uniques** : {df['hazcat'].nunique()}")

    # Affichage du tableau
    st.dataframe(df[display_columns], use_container_width=True)

    # Options d'exportation
    st.download_button("Télécharger les données (CSV)", df.to_csv(index=False), "filtered_data.csv", "text/csv")
    st.download_button("Télécharger les données (Excel)", df.to_excel(index=False), "filtered_data.xlsx", "application/vnd.ms-excel")
def display_visualizations(df: pd.DataFrame):
    """
    Affiche les visualisations interactives.
    """
    st.header("Visualisations")
    # Carte européenne
    fig_notifying_map = px.choropleth(
        df.groupby('notification_from').size().reset_index(name='count'),
        locations='notification_from',
        locationmode='country names',
        color='count',
        scope="europe",
        title="Carte des Pays Notifiants",
        color_continuous_scale='Blues'
    )
    st.plotly_chart(fig_notifying_map)

    # Diagramme à barres
    product_counts = df['prodcat'].value_counts().head(10)
    fig_bar = px.bar(product_counts, x=product_counts.index, y=product_counts.values, title="Top Catégories de Produits")
    st.plotly_chart(fig_bar)

def display_statistics(df: pd.DataFrame):
    """
    Affiche les statistiques clés.
    """
    st.header("Statistiques Clés")
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Notifications", len(df))
    col2.metric("Catégories de Produits Uniques", df['prodcat'].nunique())
    col3.metric("Catégories de Dangers Uniques", df['hazcat'].nunique())
def correlation_analysis(df: pd.DataFrame):
    """
    Analyse les corrélations entre catégories de produits et de dangers.
    """
    st.header("Analyse des Corrélations")
    st.write("Analyse basée sur le test Chi-Carré.")

    # Table de contingence
    contingency_table = pd.crosstab(df['prodcat'], df['hazcat'])
    chi2, p, _, _ = chi2_contingency(contingency_table)

    # Afficher les p-valeurs
    st.write(f"**P-value du test Chi-Carré : {p:.5f}**")
    if p < 0.05:
        st.success("Corrélation significative détectée.")
    else:
        st.info("Aucune corrélation significative détectée.")

    # Carte thermique
    fig_heatmap = px.imshow(contingency_table, title="Corrélations Produits vs Dangers", labels=dict(x="Danger", y="Produit"))
    st.plotly_chart(fig_heatmap)
class RASFFDashboard:
    def __init__(self, url: str):
        raw_data = load_data(url)
        self.data = clean_and_format_data(raw_data)

    def update_data_with_weeks(self, year, start_week):
        current_week = datetime.now().isocalendar()[1]
        weeks_to_download = list(range(start_week, current_week))
        new_data = download_weekly_data(year, weeks_to_download)
        if not new_data.empty:
            self.data = pd.concat([self.data, new_data], ignore_index=True)
            st.success("Données mises à jour avec succès.")
        else:
            st.info("Aucune nouvelle donnée disponible pour les semaines spécifiées.")

    def run(self):
        st.title("Tableau de Bord RASFF")
        tabs = st.tabs(["Tableau Filtré", "Visualisations", "Corrélations"])
        with tabs[0]:
            filtered_df = render_filtered_table(self.data)
        with tabs[1]:
            display_statistics(filtered_df)
            display_visualizations(filtered_df)
        with tabs[2]:
            correlation_analysis(filtered_df)

if __name__ == "__main__":
    st.set_page_config(page_title="RASFF Dashboard", layout="wide")
    dashboard = RASFFDashboard(url=MAIN_DATA_URL)
    dashboard.run()

