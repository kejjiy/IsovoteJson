# aggregator.py

import json
import os
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
    Calcule des statistiques globales :
     - total_files
     - total_decisions (somme de len(data_item["decisions"]) si existe)
     - liste cumulative de tous les rapporteurs / présidents
     - ...
    Renvoie un dict 'aggregated' contenant ces infos.
    """

    aggregated = {
        "total_files": 0,
        "total_decisions": 0,
        "rapporteurs_count": Counter(),   # ex: "#VEDEL" => 3
        "presidents_count": Counter(),    # ex: "#noel_leon" => 5
        # On peut stocker d'autres stats, ex: "presence_absence"
        # ou "top_interlocuteurs" etc.
    }

    aggregated["total_files"] = len(all_data)

    for item in all_data:
        # decisions
        decisions = item.get("decisions", [])
        aggregated["total_decisions"] += len(decisions)

        # cumuler rapporteurs/presidents
        for dec in decisions:
            rap = dec.get("rapporteur")
            if rap:
                aggregated["rapporteurs_count"][rap] += 1
            pres = dec.get("president")
            if pres:
                aggregated["presidents_count"][pres] += 1

    # Convertir les Counter en dict si besoin
    aggregated["rapporteurs_count"] = dict(aggregated["rapporteurs_count"])
    aggregated["presidents_count"] = dict(aggregated["presidents_count"])

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
    print("Rapporteurs rencontrés :", aggregated["rapporteurs_count"])
    print("Présidents rencontrés :", aggregated["presidents_count"])

if __name__ == "__main__":
    main()
