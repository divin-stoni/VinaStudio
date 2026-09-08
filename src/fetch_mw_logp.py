"""
fetch_mw_logp.py
Script optionnel : enrichit un CSV (colonne 'cid' = PubChem CID) avec le
poids moléculaire (MW) et le LogP (XLogP3), via l'API PubChem PUG REST.
Nécessite une connexion internet. Usage :

    python fetch_mw_logp.py scores_fusionnes.csv scores_fusionnes_enrichi.csv
"""
import sys
import time
import json
import os
import requests
import pandas as pd

CACHE_FILE = "pubchem_mw_logp_cache.json"
BASE_URL = "https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/cid/{cid}/property/MolecularWeight,XLogP/JSON"


def load_cache():
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE) as f:
            return json.load(f)
    return {}


def save_cache(cache):
    with open(CACHE_FILE, "w") as f:
        json.dump(cache, f, indent=2)


def fetch_one(cid, cache, retries=3):
    cid = str(int(cid))
    if cid in cache:
        return cache[cid]
    url = BASE_URL.format(cid=cid)
    for attempt in range(retries):
        try:
            r = requests.get(url, timeout=15)
            if r.status_code == 200:
                props = r.json()["PropertyTable"]["Properties"][0]
                mw = props.get("MolecularWeight")
                logp = props.get("XLogP")
                cache[cid] = {"MW": mw, "LogP": logp}
                return cache[cid]
            else:
                time.sleep(1)
        except Exception as e:
            print(f"  [!] CID {cid} tentative {attempt+1} échouée : {e}")
            time.sleep(2)
    cache[cid] = {"MW": None, "LogP": None}
    return cache[cid]


def main():
    if len(sys.argv) != 3:
        print("Usage : python fetch_mw_logp.py <entree.csv> <sortie.csv>")
        sys.exit(1)
    in_path, out_path = sys.argv[1], sys.argv[2]
    df = pd.read_csv(in_path)
    if "cid" not in df.columns:
        print("Erreur : le CSV doit contenir une colonne 'cid' (PubChem CID).")
        sys.exit(1)

    cache = load_cache()
    mws, logps = [], []
    for i, cid in enumerate(df["cid"], start=1):
        res = fetch_one(cid, cache)
        mws.append(res["MW"])
        logps.append(res["LogP"])
        print(f"[{i}/{len(df)}] CID {cid} → MW={res['MW']} LogP={res['LogP']}")
        time.sleep(0.2)  # politesse envers l'API PubChem
        if i % 20 == 0:
            save_cache(cache)

    save_cache(cache)
    df["MW"] = mws
    df["LogP"] = logps
    df.to_csv(out_path, index=False)
    print(f"\nTerminé → {out_path}")
    n_missing = df["MW"].isna().sum()
    if n_missing:
        print(f"⚠ {n_missing} composés sans MW/LogP (CID invalide ou non trouvé sur PubChem).")


if __name__ == "__main__":
    main()
