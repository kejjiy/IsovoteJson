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
    Parcourt la liste 'all_data' (chacun correspondant à un fichier).
    Calcule des stats globales sur tous les modules possibles :
      - presence_absence : Combien de fichiers "all_present" ?
                           Nombre total d'absences relevées, etc.
      - advanced_law_citations : l'union (ou somme) de toutes les citations
      - global_stats : on sum le total_paragraphs, total_words, 
                      et on agrège speakers_global_count.
      - decisions : nb total de décisions, cumuler presidents, rapporteurs
      - decision_graphs : on compte total de decisions, total de timeline_points, etc.
      - votes : on compte combien de votes "adoptés", "rejetés", "inconnu", etc.
    Renvoie un dict 'aggregated' contenant tout ça.
    """

    aggregated = {
        "total_files": 0,
        # presence_absence
        "files_all_present_count": 0,
        "files_not_all_present_count": 0,
        "absent_lists": [],  # on peut stocker la concat de toutes absent_list
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
        "vote_result_counter": Counter(),  # ex: "adopté", "rejeté", "inconnu"
        "vote_count": 0
    }

    aggregated["total_files"] = len(all_data)

    for item in all_data:
        # -------- presence_absence ----------
        pa = item.get("presence_absence")
        if pa:
            allp = pa.get("all_present", False)
            if allp:
                aggregated["files_all_present_count"] += 1
            else:
                aggregated["files_not_all_present_count"] += 1
            # absent_list
            absent_list = pa.get("absent_list", [])
            for ab in absent_list:
                aggregated["absent_lists"].append(ab)

        # -------- advanced_law_citations ----------
        alc = item.get("advanced_law_citations", [])
        for law_cit in alc:
            aggregated["all_law_citations"].add(law_cit)

        # -------- global_stats ----------
        gs = item.get("global_stats")
        if gs:
            aggregated["sum_total_paragraphs"] += gs.get("total_paragraphs", 0)
            aggregated["sum_total_words"] += gs.get("total_words", 0)
            sp_count = gs.get("speakers_global_count", {})
            for spk, val in sp_count.items():
                aggregated["speakers_global_counter"][spk] += val

        # -------- decisions ----------
        decs = item.get("decisions", [])
        aggregated["total_decisions"] += len(decs)
        for dec in decs:
            rap = dec.get("rapporteur")
            if rap:
                aggregated["rapporteurs_count"][rap] += 1
            pres = dec.get("president")
            if pres:
                aggregated["presidents_count"][pres] += 1

        # -------- decision_graphs ----------
        dgraphs = item.get("decision_graphs", [])
        aggregated["total_decision_graphs"] += len(dgraphs)
        # on peut compter le total de timeline_points etc.
        for dg in dgraphs:
            tpoints = dg.get("timeline_points", [])
            aggregated["sum_timeline_points"] += len(tpoints)
            transitions = dg.get("transitions", {})
            # transitions est un dict "(spA,spB)": int
            for tkey, tval in transitions.items():
                aggregated["transition_counter"][tkey] += tval

        # -------- votes ----------
        votes_list = item.get("votes", [])
        aggregated["vote_count"] += len(votes_list)
        for vt in votes_list:
            analysis = vt.get("analysis", {})
            # ex: analysis["result"] = "adopté"|"rejeté"|"inconnu"
            res = analysis.get("result", "inconnu")
            aggregated["vote_result_counter"][res] += 1

    # Convertir certains counters/datas en dict ou list
    aggregated["speakers_global_counter"] = dict(aggregated["speakers_global_counter"])
    aggregated["rapporteurs_count"] = dict(aggregated["rapporteurs_count"])
    aggregated["presidents_count"] = dict(aggregated["presidents_count"])
    aggregated["transition_counter"] = dict(aggregated["transition_counter"])
    aggregated["vote_result_counter"] = dict(aggregated["vote_result_counter"])
    aggregated["all_law_citations"] = sorted(list(aggregated["all_law_citations"]))

    return aggregated

def main():
    """
    Exemple d'utilisation : on lit un JSON,
    on agrège, puis on affiche les stats globales en console.
    """
    json_file_path = "extracted_data_modular_all_modules.json"
    all_data = load_extracted_data(json_file_path)

    if not all_data:
        print("Pas de données ou fichier introuvable.")
        return

    aggregated = aggregate_all_data(all_data)

    print("===== STATISTIQUES GLOBALES =====")
    print(f"Nb total de fichiers traités : {aggregated['total_files']}")
    print(f"Nb total de décisions : {aggregated['total_decisions']}")
    print(f"Nb total de decision_graphs : {aggregated['total_decision_graphs']}")
    print(f"Nb total de votes : {aggregated['vote_count']}")

    print("\nPrésence Absence :")
    print(f"  Fichiers all_present : {aggregated['files_all_present_count']}")
    print(f"  Fichiers not_all_present : {aggregated['files_not_all_present_count']}")
    print(f"  absent_lists (extrait) : {aggregated['absent_lists'][:5]} ...")

    print("\nLois référencées (extrait) :")
    print(aggregated["all_law_citations"][:5], "...")

    print("\nGlobal stats (paragraphes & mots) :")
    print(f"  Somme total_paragraphs = {aggregated['sum_total_paragraphs']}")
    print(f"  Somme total_words = {aggregated['sum_total_words']}")
    print("  speakers_global_counter (extrait) : ", dict(list(aggregated["speakers_global_counter"].items())[:5]))

    print("\nRapporteurs rencontrés : ", aggregated["rapporteurs_count"])
    print("\nPrésidents rencontrés : ", aggregated["presidents_count"])

    print("\nTransitions ex : ", dict(list(aggregated["transition_counter"].items())[:5]))

    print("\nVote results : ", aggregated["vote_result_counter"])

if __name__ == "__main__":
    main()
