import os
import json
import math
import streamlit as st
import plotly.graph_objects as go
import networkx as nx
from pyvis.network import Network
import streamlit.components.v1 as components

import aggregator  # votre script aggregator.py (pour la Vue globale)

###################################
# 1) Fonctions d'affichage (modules + graphes)
###################################

def display_presence_absence(module_data):
    st.header("Présence / Absence")
    all_present = module_data.get("all_present", True)
    exceptions = module_data.get("exceptions", [])
    st.write("**Tous présents ?**", all_present)
    if not all_present:
        st.write("**Exceptions :**", exceptions)

def display_votes(module_data):
    st.header("Votes")
    if not module_data:
        st.write("Aucun vote détecté.")
        return
    for i, vote in enumerate(module_data):
        with st.expander(f"Vote {i+1}"):
            st.markdown(f"**Texte** : {vote.get('text','')}")
            analysis = vote.get("analysis", {})
            st.write("**Analyse :**", analysis)

def display_global_stats(module_data):
    st.header("Statistiques globales")
    total_paragraphs = module_data.get("total_paragraphs", 0)
    total_words = module_data.get("total_words", 0)
    st.write(f"- **Nombre total de paragraphes** : {total_paragraphs}")
    st.write(f"- **Nombre total de mots** : {total_words}")

    global_chrono = module_data.get("global_chronology", [])
    if global_chrono:
        with st.expander("Voir la chronologie globale"):
            for c in global_chrono:
                paragraph_index = c.get("paragraph_index")
                paragraph_text = c.get("paragraph_text", "")
                speakers = c.get("speakers", [])
                st.markdown(f"- **Paragraphe {paragraph_index}** : {paragraph_text[:80]}...")
                st.write(f"  Intervenant(s) : {speakers}")

    speakers_count = module_data.get("speakers_global_count", {})
    if speakers_count:
        with st.expander("Voir le décompte d'interventions par intervenant (global)"):
            st.json(speakers_count)

def display_questions(module_data):
    st.header("Questions")
    if not module_data:
        st.write("Aucune question détectée.")
        return

    for q_idx, question in enumerate(module_data):
        with st.expander(f"Question {q_idx+1}"):
            st.subheader("Statistiques de participants")
            participants_stats = question.get("participants_stats", {})
            st.json(participants_stats)

            st.subheader("Citations de lois")
            law_citations = question.get("law_citations", [])
            if law_citations:
                for law in law_citations:
                    st.write(f"- {law}")
            else:
                st.write("Aucune citation de loi.")

            st.subheader("Dates détectées dans les paragraphes")
            dates_paragraphs = question.get("dates_paragraphs", [])
            for d_p in dates_paragraphs:
                d_par = d_p.get("paragraph", "")
                d_list = d_p.get("dates", [])
                st.markdown(f"- **Paragraphe** : {d_par[:80]}...")
                st.write(f"  Dates : {d_list}")

def display_decisions(module_data):
    st.header("Décisions")
    if not module_data:
        st.write("Aucune décision détectée.")
        return
    for i, dec in enumerate(module_data):
        with st.expander(f"Décision {i+1} - {dec.get('decision_id','???')}"):
            st.write("**Rapporteur :**", dec.get("rapporteur"))
            st.write("**Président :**", dec.get("president"))
            st.write("**Membres présents :**", dec.get("members_present", []))
            wps = dec.get("words_per_speaker", {})
            st.write("**Moyenne de mots par prise de parole :**")
            st.json(wps)

###################################
# 2) Fonctions pour "decision_graphs" interactives
###################################
def plot_decision_timeline_interactive(timeline_points, decision_id):
    """
    Graphe Plotly : 
    X = index local, Y = wordcount
    Taille du point ~ sqrt(wordcount)
    Info-bulle => speaker + snippet
    """
    if not timeline_points:
        st.write(f"Pas de timeline_points pour la décision {decision_id}.")
        return

    x_vals = []
    y_vals = []
    sizes = []
    hover_texts = []

    for pt in timeline_points:
        idx = pt["index"]
        speaker = pt["speaker"]
        wc = pt["wordcount"]
        snippet = pt.get("paragraph_snippet", "")
        x_vals.append(idx)
        y_vals.append(wc)
        size = max(5, math.sqrt(wc)*10) if wc>0 else 5
        sizes.append(size)
        hover_text = f"Speaker: {speaker}<br>Words: {wc}<br>{snippet}"
        hover_texts.append(hover_text)

    fig = go.Figure(
        data=go.Scatter(
            x=x_vals,
            y=y_vals,
            mode='markers+lines',
            text=hover_texts,
            hoverinfo='text',
            marker=dict(
                size=sizes,
                color='blue',
                opacity=0.7,
                line=dict(width=1, color='DarkSlateGrey')
            )
        )
    )
    fig.update_layout(
        title=f"Timeline Interactif - Décision {decision_id}",
        xaxis_title="Index prise de parole",
        yaxis_title="Nombre de mots",
        height=500
    )

    st.plotly_chart(fig, use_container_width=True)


def plot_speaker_transition_interactive(transitions_dict, all_speakers, decision_id):
    if not transitions_dict or not all_speakers:
        st.write(f"Aucune transition pour la décision {decision_id}.")
        return

    G = nx.DiGraph()
    for sp in all_speakers:
        G.add_node(sp)

    for key, val in transitions_dict.items():
        raw = key.strip("()")
        parts = raw.split(",")
        if len(parts) == 2:
            a, b = parts
            G.add_edge(a, b, weight=val)

    net = Network(height="600px", width="100%", directed=True)
    net.force_atlas_2based()

    for node in G.nodes:
        net.add_node(node, label=node)

    for (u, v) in G.edges():
        w = G[u][v]['weight']
        width = 1 + 0.5 * w
        net.add_edge(u, v, value=w, width=width)

    # ✔ On génère directement la chaîne HTML:
    html_contents = net.generate_html()
    # ✔ Puis on l'affiche dans Streamlit
    st.subheader(f"Graphe transitions (Décision {decision_id})")
    components.html(html_contents, height=650, scrolling=True)


def display_decision_graphs_interactive(module_data):
    """
    On affiche data["decision_graphs"], 
    propose d'afficher timeline & transitions en mode interactif.
    """
    st.header("Decision Graphs (Interactif)")
    if not module_data:
        st.write("Aucun 'decision_graphs' détecté.")
        return

    for i, dec_data in enumerate(module_data):
        dec_id = dec_data.get("decision_id", f"Q{i+1}")
        with st.expander(f"Decision Graph #{i+1} - {dec_id}"):
            timeline_points = dec_data.get("timeline_points", [])
            transitions_dict = dec_data.get("transitions", {})
            all_speakers = dec_data.get("all_speakers", [])

            if st.checkbox(f"Afficher timeline (Plotly) - {dec_id}", key=f"timeline_{i}"):
                plot_decision_timeline_interactive(timeline_points, dec_id)

            if st.checkbox(f"Afficher transitions (PyVis) - {dec_id}", key=f"trans_{i}"):
                plot_speaker_transition_interactive(transitions_dict, all_speakers, dec_id)

###################################
# 3) Registre automatique des modules
###################################
MODULE_DISPLAYERS = {
    "presence_absence": display_presence_absence,
    "votes": display_votes,
    "global_stats": display_global_stats,
    "questions": display_questions,
    "decisions": display_decisions,
    "decision_graphs": display_decision_graphs_interactive  # version interactive
}

###################################
# 4) Script Streamlit principal
###################################
def main():
    st.title("Explorateur des données extraites (Modulaire) + Aggregation + Graphs Interactifs")

    json_file_path = "extracted_data_modular_all_modules.json"

    mode = st.sidebar.radio("Mode d'affichage", ["Vue par fichier", "Vue globale"])

    # ---- Vue globale => aggregator ----
    if mode == "Vue globale":
        st.header("Statistiques globales agrégées")
        all_data = aggregator.load_extracted_data(json_file_path)
        if not all_data:
            st.error("Impossible de charger le JSON ou données vides.")
            return
        agg = aggregator.aggregate_all_data(all_data)
        st.subheader("Récap global :")
        st.write(f"- **Nombre total de fichiers** : {agg['total_files']}")
        st.write(f"- **Nombre total de décisions** : {agg['total_decisions']}")
        st.write(f"- **Nombre total de decision_graphs** : {agg['total_decision_graphs']}")
        st.write(f"- **Nombre total de votes** : {agg['vote_count']}")

        st.subheader("Présence Absence")
        st.write(f"Fichiers all_present: {agg['files_all_present_count']}")
        st.write(f"Fichiers not_all_present: {agg['files_not_all_present_count']}")
        st.write("Absent-lists (extrait) :", agg["absent_lists"][:10])

        st.subheader("Lois citées (extrait)")
        st.write(agg["all_law_citations"][:10])

        st.subheader("Global stats (paragraphs/words)")
        st.write(f"- sum_total_paragraphs = {agg['sum_total_paragraphs']}")
        st.write(f"- sum_total_words = {agg['sum_total_words']}")
        st.subheader("Speakers global (extrait)")
        sp_items = list(agg["speakers_global_counter"].items())[:10]
        st.json(dict(sp_items))

        st.subheader("Rapporteurs (cumulés)")
        st.json(agg["rapporteurs_count"])

        st.subheader("Présidents (cumulés)")
        st.json(agg["presidents_count"])

        st.subheader("Transitions (extrait)")
        trans_items = list(agg["transition_counter"].items())[:10]
        st.json(dict(trans_items))

        st.subheader("Votes")
        st.json(agg["vote_result_counter"])
        return

    # ---- Vue par fichier ----
    if not os.path.exists(json_file_path):
        st.error(f"Fichier JSON introuvable : {json_file_path}")
        return

    with open(json_file_path, "r", encoding='utf-8') as f:
        all_data = json.load(f)

    if not isinstance(all_data, list):
        st.warning("Le JSON n'est pas une liste.")
        return

    file_names = [item["file"] for item in all_data if "file" in item]
    if not file_names:
        st.warning("Aucun fichier dans le JSON.")
        return

    selected_file = st.selectbox("Sélectionnez un fichier :", file_names)
    data_item = next((x for x in all_data if x.get("file") == selected_file), None)
    if not data_item:
        st.warning("Données non trouvées pour ce fichier.")
        return

    st.subheader(f"Contenu pour '{selected_file}' :")

    # On parcourt les clés => on appelle un display_func si on en a un
    for key, mod_data in data_item.items():
        if key in ("file", "error"):
            continue
        display_func = MODULE_DISPLAYERS.get(key, None)
        if display_func:
            display_func(mod_data)
        else:
            st.header(f"{key} (module inconnu)")
            st.json(mod_data)

if __name__ == "__main__":
    main()
