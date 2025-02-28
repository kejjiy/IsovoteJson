# aggregator.py

import os
import json
import math
import streamlit as st
from collections import Counter, defaultdict

###################################################
# 1) Fonctions de base pour chargement & agrégation
###################################################

def load_extracted_data(json_file_path):
    """
    Charge la liste de documents (all_data) depuis un fichier JSON.
    Renvoie une liste de dict (ou [] si problème).
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
    Parcourt la liste 'all_data' (chacun correspondant à un fichier).
    Calcule des stats globales sur les différents modules :

      * presence_absence
         - combien de fichiers all_present
         - absent_list cumulée

      * advanced_law_citations
         - set de toutes les lois citées

      * global_stats
         - somme total_paragraphs
         - somme total_words
         - merge speakers_global_count

      * decisions
         - total_decisions
         - rapporteurs_count
         - presidents_count

      * decision_graphs
         - total_decision_graphs
         - sum_timeline_points
         - transition_counter

      * votes
         - nb total de votes
         - vote_result_counter (adopté, rejeté, inconnu, etc.)

    Renvoie un dict 'aggregated' rassemblant tout ça.
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
        "vote_result_counter": Counter()
    }

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
            for tkey, tval in transitions.items():
                aggregated["transition_counter"][tkey] += tval

        # votes
        votes_list = item.get("votes", [])
        aggregated["vote_count"] += len(votes_list)
        for vt in votes_list:
            analysis = vt.get("analysis", {})
            res = analysis.get("result", "inconnu")
            aggregated["vote_result_counter"][res] += 1

    # Convertir en types JSON-compatibles
    aggregated["all_law_citations"] = sorted(list(aggregated["all_law_citations"]))
    aggregated["speakers_global_counter"] = dict(aggregated["speakers_global_counter"])
    aggregated["rapporteurs_count"] = dict(aggregated["rapporteurs_count"])
    aggregated["presidents_count"] = dict(aggregated["presidents_count"])
    aggregated["transition_counter"] = dict(aggregated["transition_counter"])
    aggregated["vote_result_counter"] = dict(aggregated["vote_result_counter"])

    return aggregated


###################################################
# 2) Interface Streamlit pour afficher l'agrégat
###################################################

def display_aggregated_stats(aggregated):
    """
    Affichage Streamlit de l'agrégat, 
    pour visualiser les statistiques globales en mode interactif.
    """
    st.title("Statistiques globales (Agrégées)")
    st.write(f"**Nombre total de fichiers** : {aggregated['total_files']}")
    st.write(f"**Fichiers all_present** : {aggregated['files_all_present_count']}")
    st.write(f"**Fichiers not_all_present** : {aggregated['files_not_all_present_count']}")

    st.write(f"**Nombre total de décisions** : {aggregated['total_decisions']}")
    st.write(f"**Nombre total de decision_graphs** : {aggregated['total_decision_graphs']}")

    st.write(f"**Nombre total de votes** : {aggregated['vote_count']}")

    st.subheader("Votes : results")
    st.json(aggregated["vote_result_counter"])

    st.subheader("Rapporteurs (cumulés)")
    st.json(aggregated["rapporteurs_count"])

    st.subheader("Présidents (cumulés)")
    st.json(aggregated["presidents_count"])

    st.subheader("Absent-lists (extrait)")
    st.write(aggregated["absent_lists"][:10])  # on limite l'affichage

    st.subheader("Lois citées (extrait)")
    st.write(aggregated["all_law_citations"][:10])

    st.subheader("Global stats paragraphs/words")
    st.write(f"- **Sum paragraphs** : {aggregated['sum_total_paragraphs']}")
    st.write(f"- **Sum words** : {aggregated['sum_total_words']}")

    st.subheader("Speakers global counter (extrait)")
    # on limite l'affichage
    items_list = list(aggregated["speakers_global_counter"].items())[:10]
    st.json(dict(items_list))

    st.subheader("Transitions ex (extrait)")
    trans_items = list(aggregated["transition_counter"].items())[:10]
    st.json(dict(trans_items))


###################################################
# 3) Point d'entrée Streamlit
###################################################
def main():
    st.write("## Agrégateur de données - Extrait JSON")
    json_file_path = "extracted_data_modular_all_modules.json"

    if not os.path.exists(json_file_path):
        st.error(f"Fichier introuvable : {json_file_path}")
        return

    # Charger
    all_data = load_extracted_data(json_file_path)
    if not all_data:
        st.warning("Le JSON est vide ou invalide.")
        return

    aggregated = aggregate_all_data(all_data)

    # Affichage
    display_aggregated_stats(aggregated)

if __name__ == "__main__":
    # Si on exécute en tant que script: 
    #   streamlit run aggregator.py
    # On lance la fonction main
    main()
