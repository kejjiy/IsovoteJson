# aggregator.py

import os
import json
from collections import Counter, defaultdict

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

    De plus, on crée un "global_decision_graph" fusionnant tous les
    'decision_graphs' en un seul :
      aggregator["global_decision_graph"] = {
        "timeline_points": [...],  # concat de tous
        "transitions": {...},      # merge de tous
        "all_speakers": [...],     # union de tous
      }

    Puis on renvoie un dict 'aggregated' avec tout.

    Exemple d'accès :
      aggregated["global_decision_graph"]["timeline_points"]
      aggregated["global_decision_graph"]["transitions"]
      aggregated["global_decision_graph"]["all_speakers"]
    pour tracer un unique graphe global dans Streamlit.
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

    # On garde un "global_index" si on veut un index unique pour la timeline
    global_index = 0

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

            # On fusionne tout dans le "global_decision_graph"
            for tp in tpoints:
                # On prend la structure, mais on modifie "index" => on utilise global_index
                new_tp = {
                    "index": global_index,
                    "speaker": tp.get("speaker", "#unknown"),
                    "wordcount": tp.get("wordcount", 0),
                    "paragraph_snippet": tp.get("paragraph_snippet", "")
                }
                aggregated["global_decision_graph"]["timeline_points"].append(new_tp)
                # On incrémente
                global_index += 1

                # On enregistre le speaker dans all_speakers
                spk = new_tp["speaker"]
                aggregated["global_decision_graph"]["all_speakers"].add(spk)

            # transitions
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

    # On finit par remplir aggregator["global_decision_graph"]["transitions"]
    # en prenant aggregated["transition_counter"]
    aggregated["global_decision_graph"]["transitions"] = dict(aggregated["transition_counter"])
    # On convertit set -> list
    all_speakers_set = aggregated["global_decision_graph"]["all_speakers"]
    aggregated["global_decision_graph"]["all_speakers"] = list(all_speakers_set)

    return aggregated

def main():
    """
    Exemple d'utilisation : on lit le JSON, on agrège, on affiche en console.
    """
    json_file_path = "extracted_data_modular_all_modules.json"
    if not os.path.exists(json_file_path):
        print("Fichier introuvable.")
        return
    with open(json_file_path, "r", encoding="utf-8") as f:
        all_data = json.load(f)

    if not isinstance(all_data, list):
        print("Le JSON n'est pas une liste.")
        return

    aggregated = aggregate_all_data(all_data)
    print("=== Statistiques globales ===")
    print(f"Fichiers total : {aggregated['total_files']}")
    print(f"Decisions total : {aggregated['total_decisions']}")
    print(f"Decision_graphs total : {aggregated['total_decision_graphs']}")
    print("Lois citées (extrait) :", aggregated["all_law_citations"][:5])
    print("Vote_result_counter :", aggregated["vote_result_counter"])

    # On peut aussi afficher aggregator["global_decision_graph"]
    # ex:
    ggraph = aggregated["global_decision_graph"]
    print(f"Global timeline_points: {len(ggraph['timeline_points'])}")
    print(f"Global transitions: {len(ggraph['transitions'])}")
    print(f"Global all_speakers: {len(ggraph['all_speakers'])}")

if __name__ == "__main__":
    main()
