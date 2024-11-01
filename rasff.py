import streamlit as st
import pandas as pd
import datetime
from ipyvizzu import Chart, Data, Config, Style, Animation
import streamlit.components.v1 as components
from typing import List, Optional
from dataclasses import dataclass
import plotly.express as px
from streamlit_vizzu import VizzuChart

# Réutilisation des imports et classes existantes...
from hazard_categories import hazard_categories
from hazards import hazards
from notifying_countries import notifying_countries
from origin_countries import origin_countries
from product_categories import product_categories

# Les classes Config, DataStandardizer, DataCleaner, et DataFetcher restent inchangées...

class EnhancedDataAnalyzer:
    @staticmethod
    def prepare_vizzu_data(df: pd.DataFrame) -> dict:
        """Prépare les données pour PageVizzu."""
        vizzu_data = {
            'series': [
                {'name': 'Product Category', 'values': df['Product Category'].tolist()},
                {'name': 'issue_type', 'values': df['issue_type'].tolist()},
                {'name': 'count', 'values': [1] * len(df)},
                {'name': 'notifying_country', 'values': df['notifying_country'].tolist()},
                {'name': 'date', 'values': df['date'].dt.strftime('%Y-%m').tolist()},
                {'name': 'risk_decision', 'values': df['risk_decision'].tolist()}
            ]
        }
        return vizzu_data

    @staticmethod
    def create_temporal_analysis(df: pd.DataFrame) -> dict:
        """Analyse temporelle des notifications."""
        temporal_data = df.groupby([
            pd.Grouper(key='date', freq='M'),
            'issue_type'
        ]).size().reset_index(name='count')
        return temporal_data

class EnhancedRASFFDashboard:
    def __init__(self):
        self.data_cleaner = DataCleaner(hazard_categories)
        self.data_analyzer = EnhancedDataAnalyzer()
        self.standardizer = DataStandardizer(notifying_countries, origin_countries)

    def create_vizzu_chart(self, data: dict, chart_type: str):
        """Crée un graphique PageVizzu."""
        chart = VizzuChart()
        
        if chart_type == "distribution":
            chart.animate(
                Data.filter("record.Product Category !== null"),
                Config({
                    "channels": {
                        "y": {"set": ["count"]},
                        "x": {"set": ["Product Category"]},
                        "color": {"set": ["issue_type"]}
                    },
                    "title": "Distribution des notifications par catégorie de produit",
                    "geometry": "rectangle"
                })
            )
        elif chart_type == "timeline":
            chart.animate(
                Data.filter("record.date !== null"),
                Config({
                    "channels": {
                        "x": {"set": ["date"]},
                        "y": {"set": ["count"]},
                        "color": {"set": ["issue_type"]}
                    },
                    "title": "Évolution temporelle des notifications",
                    "geometry": "line"
                })
            )

        return chart

    def render_enhanced_filters(self, df: pd.DataFrame):
        """Affiche des filtres améliorés."""
        st.sidebar.header("Filtres avancés")
        
        # Filtres temporels
        date_range = st.sidebar.date_input(
            "Période",
            value=(df['date'].min(), df['date'].max()),
            min_value=df['date'].min(),
            max_value=df['date'].max()
        )

        # Filtres multi-sélection
        selected_categories = st.sidebar.multiselect(
            "Catégories de produits",
            options=sorted(df['Product Category'].unique())
        )

        selected_issues = st.sidebar.multiselect(
            "Types de problèmes",
            options=sorted(df['issue_type'].unique())
        )

        selected_countries = st.sidebar.multiselect(
            "Pays notifiants",
            options=sorted(df['notifying_country'].unique())
        )

        # Filtre de décision de risque
        risk_decisions = st.sidebar.multiselect(
            "Décisions de risque",
            options=sorted(df['risk_decision'].unique())
        )

        # Application des filtres
        filtered_df = df.copy()
        if selected_categories:
            filtered_df = filtered_df[filtered_df['Product Category'].isin(selected_categories)]
        if selected_issues:
            filtered_df = filtered_df[filtered_df['issue_type'].isin(selected_issues)]
        if selected_countries:
            filtered_df = filtered_df[filtered_df['notifying_country'].isin(selected_countries)]
        if risk_decisions:
            filtered_df = filtered_df[filtered_df['risk_decision'].isin(risk_decisions)]
        
        filtered_df = filtered_df[
            (filtered_df['date'] >= pd.to_datetime(date_range[0])) &
            (filtered_df['date'] <= pd.to_datetime(date_range[1]))
        ]

        return filtered_df

    def render_enhanced_visualizations(self, df: pd.DataFrame):
        """Affiche des visualisations améliorées avec PageVizzu."""
        st.header("Visualisations interactives avancées")

        # Préparation des données pour PageVizzu
        vizzu_data = self.data_analyzer.prepare_vizzu_data(df)

        # Création des onglets pour différentes visualisations
        viz_tabs = st.tabs(["Distribution", "Évolution temporelle", "Analyse géographique", "Matrices de risque"])

        with viz_tabs[0]:
            distribution_chart = self.create_vizzu_chart(vizzu_data, "distribution")
            st.write(distribution_chart)

        with viz_tabs[1]:
            temporal_data = self.data_analyzer.create_temporal_analysis(df)
            timeline_chart = self.create_vizzu_chart(temporal_data, "timeline")
            st.write(timeline_chart)

        with viz_tabs[2]:
            # Carte choroplèthe des notifications par pays
            fig_map = px.choropleth(
                df.groupby('notifying_country').size().reset_index(name='count'),
                locations='notifying_country',
                locationmode='country names',
                color='count',
                title="Répartition géographique des notifications",
                color_continuous_scale='Viridis'
            )
            st.plotly_chart(fig_map, use_container_width=True)

        with viz_tabs[3]:
            # Matrice de risque interactive
            risk_matrix = pd.crosstab(
                df['risk_decision'],
                df['issue_type'],
                margins=True
            )
            
            fig_matrix = px.imshow(
                risk_matrix,
                title="Matrice de risque par type de problème",
                labels=dict(x="Type de problème", y="Décision de risque", color="Nombre de cas")
            )
            st.plotly_chart(fig_matrix, use_container_width=True)

    async def run(self):
        st.set_page_config(page_title="Analyseur RASFF Amélioré", layout="wide")
        st.title("Analyseur de données RASFF - Version améliorée")

        try:
            # Chargement des données
            csv_url = "https://raw.githubusercontent.com/M00N69/RASFFPORTAL/refs/heads/main/rasff_%202020TO30OCT2024.csv"
            df = pd.read_csv(csv_url)
            
            # Nettoyage et standardisation
            df = self.standardizer.clean_data(df)
            df = self.data_cleaner.clean_data(df)
            df['issue_type'] = df.apply(lambda row: classify_issue(row['Hazard Substance'], row['Hazard Category']), axis=1)

            if not df.empty:
                # Application des filtres
                filtered_df = self.render_enhanced_filters(df)
                
                # Affichage des visualisations
                self.render_enhanced_visualizations(filtered_df)
                
                # Ajout d'une section de statistiques résumées
                st.header("Statistiques clés")
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.metric("Total des notifications", len(filtered_df))
                with col2:
                    st.metric("Catégories de produits uniques", filtered_df['Product Category'].nunique())
                with col3:
                    st.metric("Types de problèmes uniques", filtered_df['issue_type'].nunique())

                # Option d'export des données filtrées
                if st.button("Exporter les données filtrées (CSV)"):
                    csv = filtered_df.to_csv(index=False)
                    st.download_button(
                        "Télécharger",
                        csv,
                        "rasff_filtered_data.csv",
                        "text/csv",
                        key='download-csv'
                    )
            else:
                st.error("Le fichier CSV est vide ou les données n'ont pas pu être chargées.")

        except Exception as e:
            st.error(f"Erreur lors du chargement des données: {e}")

if __name__ == "__main__":
    dashboard = EnhancedRASFFDashboard()
    import asyncio
    asyncio.run(dashboard.run())
