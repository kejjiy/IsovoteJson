# JsonInterfacer.py

import os
import json
import math
import streamlit as st
import plotly.graph_objects as go
import networkx as nx
from pyvis.network import Network
import streamlit.components.v1 as components
from collections import Counter, defaultdict

################################################
# 1) Agrégation (ancien aggregator.py) intégré
################################################

def load_extracted_data(json_file_path):
    """
    Charge la liste de documents (all_data) depuis un fichier JSON.
    Renvoie une liste de dicts (ou [] si problème).
    """
    if not os.path.exists(json_file_path):
        return []
    try:
        with open(json_file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, list):
            return []
        return data
    except:
        return []

def aggregate_all_data(all_data):
    """
    Parcourt la liste 'all_data' (un dict par fichier).
    Calcule des statistiques globales sur :
      - presence_absence
      - advanced_law_citations
      - global_stats
      - decisions
      - decision_graphs
      - votes

    De plus, on crée un "global_decision_graph" fusionnant tous
    les timeline_points & transitions, pour un graphe global.
    """

    aggregated = {
        "total_files": len(all_data),

        # presence_absence
        "files_all_present_count": 0,
        "files_not_all_present_count": 0,
        "absent_lists": [],

        # advanced_law_citations
        "all_law_citations": set(),

        # global_stats
        "sum_total_paragraphs": 0,
        "sum_total_words": 0,
        "speakers_global_counter": Counter(),

        # decisions
        "total_decisions": 0,
        "rapporteurs_count": Counter(),
        "presidents_count": Counter(),

        # decision_graphs
        "total_decision_graphs": 0,
        "sum_timeline_points": 0,
        "transition_counter": Counter(),

        # votes
        "vote_count": 0,
        "vote_result_counter": Counter(),

        # Le graphe global unique
        "global_decision_graph": {
            "timeline_points": [],
            "transitions": {},
            "all_speakers": set()
        }
    }

    global_index = 0  # pour donner un index unique aux timeline_points

    for item in all_data:
        # presence_absence
        pa = item.get("presence_absence")
        if pa:
            if pa.get("all_present", False):
                aggregated["files_all_present_count"] += 1
            else:
                aggregated["files_not_all_present_count"] += 1
            absent_list = pa.get("absent_list", [])
            for ab in absent_list:
                aggregated["absent_lists"].append(ab)

        # advanced_law_citations
        alc = item.get("advanced_law_citations", [])
        for law_cit in alc:
            aggregated["all_law_citations"].add(law_cit)

        # global_stats
        gs = item.get("global_stats")
        if gs:
            aggregated["sum_total_paragraphs"] += gs.get("total_paragraphs", 0)
            aggregated["sum_total_words"] += gs.get("total_words", 0)
            sp_count = gs.get("speakers_global_count", {})
            for spk, val in sp_count.items():
                aggregated["speakers_global_counter"][spk] += val

        # decisions
        decs = item.get("decisions", [])
        aggregated["total_decisions"] += len(decs)
        for dec in decs:
            rap = dec.get("rapporteur")
            if rap:
                aggregated["rapporteurs_count"][rap] += 1
            pres = dec.get("president")
            if pres:
                aggregated["presidents_count"][pres] += 1

        # decision_graphs
        dgraphs = item.get("decision_graphs", [])
        aggregated["total_decision_graphs"] += len(dgraphs)

        for dg in dgraphs:
            tpoints = dg.get("timeline_points", [])
            aggregated["sum_timeline_points"] += len(tpoints)
            transitions = dg.get("transitions", {})

            # fusion dans global_decision_graph
            for tp in tpoints:
                new_tp = {
                    "index": global_index,
                    "speaker": tp.get("speaker", "#unknown"),
                    "wordcount": tp.get("wordcount", 0),
                    "paragraph_snippet": tp.get("paragraph_snippet", "")
                }
                aggregated["global_decision_graph"]["timeline_points"].append(new_tp)
                spk = new_tp["speaker"]
                aggregated["global_decision_graph"]["all_speakers"].add(spk)

                global_index += 1

            for tkey, tval in transitions.items():
                aggregated["transition_counter"][tkey] += tval

        # votes
        votes_list = item.get("votes", [])
        aggregated["vote_count"] += len(votes_list)
        for vt in votes_list:
            analysis = vt.get("analysis", {})
            res = analysis.get("result", "inconnu")
            aggregated["vote_result_counter"][res] += 1

    # convert counters/sets en structures JSON-compatibles
    aggregated["all_law_citations"] = sorted(list(aggregated["all_law_citations"]))
    aggregated["speakers_global_counter"] = dict(aggregated["speakers_global_counter"])
    aggregated["rapporteurs_count"] = dict(aggregated["rapporteurs_count"])
    aggregated["presidents_count"] = dict(aggregated["presidents_count"])
    aggregated["transition_counter"] = dict(aggregated["transition_counter"])
    aggregated["vote_result_counter"] = dict(aggregated["vote_result_counter"])

    # remplir global_decision_graph transitions + all_speakers
    aggregated["global_decision_graph"]["transitions"] = dict(aggregated["transition_counter"])
    aggregated["global_decision_graph"]["all_speakers"] = list(aggregated["global_decision_graph"]["all_speakers"])

    return aggregated


################################################
# 2) Fonctions d'affichage de modules
################################################

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
    st.header("Statistiques globales (par fichier)")
    total_paragraphs = module_data.get("total_paragraphs", 0)
    total_words = module_data.get("total_words", 0)
    st.write(f"- **Nombre total de paragraphes** : {total_paragraphs}")
    st.write(f"- **Nombre total de mots** : {total_words}")

    global_chrono = module_data.get("global_chronology", [])
    if global_chrono:
        with st.expander("Voir la chronologie globale (FICHIER)"):
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

################################################
# 3) Graphes interactifs (Plotly + PyVis)
################################################

def plot_decision_timeline_interactive(timeline_points, decision_id):
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
        hover_texts.append(f"Speaker: {speaker}<br>Words: {wc}<br>{snippet}")

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
        title=f"Timeline Interactif - {decision_id}",
        xaxis_title="Index prise de parole",
        yaxis_title="Nb de mots",
        height=500
    )

    st.plotly_chart(fig, use_container_width=True)

def plot_speaker_transition_interactive(transitions_dict, all_speakers, decision_id):
    """
    Crée un graphe interactif via PyVis pour les transitions entre interlocuteurs.
    Les nœuds sont affichés avec une taille légèrement agrandie et des labels en police plus grande.
    """
    if not transitions_dict or not all_speakers:
        st.write(f"Aucune transition pour {decision_id}.")
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
    # Ajuster le layout pour améliorer l'espacement
    net.barnes_hut(gravity=-20000, central_gravity=0.3, spring_length=250, spring_strength=0.001, damping=0.95)

    # Ajouter les nœuds avec taille légèrement agrandie et police en plus grand
    for node in G.nodes():
        net.add_node(node, label=node, size=35, font={"size": 16})
    
    # Ajouter les arêtes en ajustant leur épaisseur
    for (u, v) in G.edges():
        w = G[u][v]['weight']
        width = 1 + 0.5 * w  # ajustement du coefficient si besoin
        net.add_edge(u, v, value=w, width=width)

    # Générer le HTML directement en mémoire
    html_contents = net.generate_html()
    st.subheader(f"Graphe transitions {decision_id}")
    st.components.v1.html(html_contents, height=650, scrolling=True)

def display_decision_graphs_interactive(module_data):
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
# 4) Dictionnaire de displayers
###################################
MODULE_DISPLAYERS = {
    "presence_absence": display_presence_absence,
    "votes": display_votes,
    "global_stats": display_global_stats,
    "questions": display_questions,
    "decisions": display_decisions,
    "decision_graphs": display_decision_graphs_interactive
}

###################################
# 5) Main Streamlit
###################################
def main():
    st.title("Explorateur : Fichiers / Global + Graph Interactif")

    json_file_path = "extracted_data_modular_all_modules.json"

    mode = st.sidebar.radio("Mode d'affichage", ["Vue par fichier", "Vue globale"])

    if not os.path.exists(json_file_path):
        st.error(f"Fichier JSON introuvable : {json_file_path}")
        return

    all_data = load_extracted_data(json_file_path)
    if not all_data:
        st.warning("Le JSON est vide ou invalide.")
        return

    # Agrégation
    agg = aggregate_all_data(all_data)

    if mode == "Vue globale":
        st.header("Statistiques globales")
        st.write(f"**Total Files** : {agg['total_files']}")
        st.write(f"**Total Decisions** : {agg['total_decisions']}")
        st.write(f"**Total Decision Graphs** : {agg['total_decision_graphs']}")
        st.write(f"**Total Votes** : {agg['vote_count']}")

        st.subheader("Présence Absence")
        st.write(f"files_all_present_count = {agg['files_all_present_count']}")
        st.write(f"files_not_all_present_count = {agg['files_not_all_present_count']}")
        st.write("absent_lists (extrait) :", agg['absent_lists'][:10])

        st.subheader("Lois citées (extrait)")
        st.write(agg["all_law_citations"][:10])

        st.subheader("Global Stats (paragraphs/words)")
        st.write(f"sum_total_paragraphs = {agg['sum_total_paragraphs']}")
        st.write(f"sum_total_words = {agg['sum_total_words']}")

        st.subheader("Speakers global (extrait)")
        spc = list(agg["speakers_global_counter"].items())[:10]
        st.json(dict(spc))

        st.subheader("Rapporteurs (cumulés)")
        st.json(agg["rapporteurs_count"])

        st.subheader("Présidents (cumulés)")
        st.json(agg["presidents_count"])

        st.subheader("Transitions (extrait)")
        trans_items = list(agg["transition_counter"].items())[:10]
        st.json(dict(trans_items))

        st.subheader("Votes (résultats)")
        st.json(agg["vote_result_counter"])

        # On affiche un graphe global
        # => same logic, on a agg["global_decision_graph"]
        gdg = agg["global_decision_graph"]
        if st.checkbox("Afficher timeline global (Plotly)"):
            tpoints = gdg["timeline_points"]
            plot_decision_timeline_interactive(tpoints, "GLOBAL")

        if st.checkbox("Afficher transitions global (PyVis)"):
            transitions_dict = gdg["transitions"]
            all_sp = gdg["all_speakers"]
            plot_speaker_transition_interactive(transitions_dict, all_sp, "GLOBAL")

        return

    # Sinon => Vue par fichier
    st.header("Vue par fichier")

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
