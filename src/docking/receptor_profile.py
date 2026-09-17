# -*- coding: utf-8 -*-
"""
receptor_profile.py

Source unique de vérité pour tout récepteur (pompe d'efflux, dérépresseur,
ou récepteur importé par l'utilisateur en Mode 2) utilisé par VinaStudio.

Aucun autre module ne doit stocker sa propre copie des coordonnées de
grille, du chemin PDBQT ou des paramètres Vina d'un récepteur : tout passe
par un ReceptorProfile chargé depuis receptor_profiles/<profile_id>.json.

Ajouter un nouveau couple pompe/dérépresseur (Section 7 du protocole
multi-récepteurs) ne nécessite QUE :
    1. un nouveau fichier receptor_profiles/<profile_id>.json
    2. une entrée dans TARGET_ALIASES si un alias court est souhaité
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

PROJECT_ROOT = Path(__file__).resolve().parents[2]
PROFILES_DIR = PROJECT_ROOT / "receptor_profiles"

# Alias courts utilisés historiquement dans le code/l'interface
# (target="MexB"/"MexR") -> profile_id réel.
TARGET_ALIASES: dict[str, str] = {
    "mexb": "mexb_paeruginosa",
    "mexr": "mexr_paeruginosa",
}

_DEFAULT_DOCKING_PARAMS = {
    "exhaustiveness": 32,
    "num_modes": 9,
    "energy_range": 3.0,
    "seed": 2024,
    "cpu": 0,
}


@dataclass
class GridBox:
    center: tuple[float, float, float]
    size: tuple[float, float, float]

    @classmethod
    def from_dict(cls, data: dict) -> "GridBox":
        return cls(
            center=tuple(data["center"]),
            size=tuple(data["size"]),
        )


@dataclass
class ReceptorProfile:
    profile_id: str
    display_name: str
    profile_type: str  # "built_in" | "user_defined"
    pdbqt_path: Path
    grid_box: GridBox

    species: Optional[str] = None
    role: Optional[str] = None
    source_pdb: Optional[str] = None
    pdb_path_for_viewer: Optional[Path] = None

    docking_params: dict = field(default_factory=lambda: dict(_DEFAULT_DOCKING_PARAMS))

    risk_calibration: Optional[dict] = None
    validated: bool = False
    notes: str = ""

    # ------------------------------------------------------------------
    # COUPLAGE POMPE / DEREPRESSEUR
    # ------------------------------------------------------------------
    # partner_id : profile_id du partenaire biologique. Une pompe
    #   d'efflux pointe vers son derepresseur et reciproquement. C'est
    #   ce qui permet a l'interface de proposer une campagne « A + B »
    #   pour n'importe quel couple, et plus seulement MexB + MexR.
    # short_name : nom court affiche dans les menus (« AcrB »), au lieu
    #   du display_name complet (« AcrB - site 2 peripasmique, E. coli »).
    partner_id: Optional[str] = None
    short_name: Optional[str] = None

    # Un recepteur peut avoir PLUSIEURS partenaires declares — ex. une
    # seule pompe CmeB face a deux sites documentes de CmeR (cholate,
    # taurocholate). partner_id reste pour compatibilite avec les
    # couples deja declares (un seul partenaire) ; partner_ids est la
    # liste complete, fusionnee avec partner_id par get_partner_ids().
    partner_ids: list = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict) -> "ReceptorProfile":
        pdbqt_path = Path(data["pdbqt_path"])
        if not pdbqt_path.is_absolute():
            pdbqt_path = PROJECT_ROOT / pdbqt_path

        pdb_viewer = data.get("pdb_path_for_viewer")
        if pdb_viewer:
            pdb_viewer = Path(pdb_viewer)
            if not pdb_viewer.is_absolute():
                pdb_viewer = PROJECT_ROOT / pdb_viewer
        else:
            pdb_viewer = None

        return cls(
            profile_id=data["profile_id"],
            display_name=data.get("display_name", data["profile_id"]),
            profile_type=data.get("profile_type", "built_in"),
            pdbqt_path=pdbqt_path,
            grid_box=GridBox.from_dict(data["grid_box"]),
            species=data.get("species"),
            role=data.get("role"),
            source_pdb=data.get("source_pdb"),
            pdb_path_for_viewer=pdb_viewer,
            docking_params={**_DEFAULT_DOCKING_PARAMS, **data.get("docking_params", {})},
            risk_calibration=data.get("risk_calibration"),
            validated=bool(data.get("validated", False)),
            notes=data.get("notes", ""),
            partner_id=data.get("partner_id"),
            short_name=data.get("short_name"),
            partner_ids=list(data.get("partner_ids") or []),
        )

    def to_dict(self) -> dict:
        return {
            "profile_id": self.profile_id,
            "display_name": self.display_name,
            "profile_type": self.profile_type,
            "species": self.species,
            "role": self.role,
            "pdbqt_path": str(self.pdbqt_path),
            "pdb_path_for_viewer": str(self.pdb_path_for_viewer) if self.pdb_path_for_viewer else None,
            "source_pdb": self.source_pdb,
            "grid_box": {"center": list(self.grid_box.center), "size": list(self.grid_box.size)},
            "docking_params": self.docking_params,
            "risk_calibration": self.risk_calibration,
            "validated": self.validated,
            "notes": self.notes,
            "partner_id": self.partner_id,
            "short_name": self.short_name,
            "partner_ids": list(self.partner_ids or []),
        }


def list_profile_ids() -> list[str]:
    if not PROFILES_DIR.exists():
        return []
    return sorted(p.stem for p in PROFILES_DIR.glob("*.json"))


def load_profile(profile_id: str) -> ReceptorProfile:
    path = PROFILES_DIR / f"{profile_id}.json"
    if not path.exists():
        raise FileNotFoundError(
            f"Profil de récepteur introuvable : {profile_id} (attendu : {path})"
        )
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    profile = ReceptorProfile.from_dict(data)

    # Une configuration de grid box personnalisee par l'utilisateur (voir
    # save_user_grid_override) prend le pas sur celle d'origine, mais
    # uniquement pour un recepteur deja integre au logiciel — jamais pour
    # un profil importe librement, qui est deja pleinement editable.
    if profile.profile_type == "built_in":
        override = get_user_grid_override(profile.profile_id)
        if override is not None:
            profile.grid_box = override

    return profile


def resolve_target_profile(target: str) -> ReceptorProfile:
    """
    Résout un `target` (alias historique "MexB"/"MexR", ou un profile_id
    complet) vers son ReceptorProfile.

    Point d'entrée unique utilisé par vina_engine.py, config_manager.py et
    visualization_bridge.py.
    """
    normalized = str(target).strip().lower()
    profile_id = TARGET_ALIASES.get(normalized, normalized)

    try:
        return load_profile(profile_id)
    except FileNotFoundError:
        available = sorted(set(TARGET_ALIASES) | set(list_profile_ids()))
        raise ValueError(
            f"Cible de docking inconnue : {target!r}. "
            f"Cibles/profils disponibles : {available}."
        ) from None


def save_user_profile(profile: ReceptorProfile, user_profiles_dir: Optional[Path] = None) -> Path:
    """
    Sauvegarde un profil `user_defined` (Mode 2, import libre) en local.
    Jamais utilisé pour un profil built_in (protégé en écriture).
    """
    if profile.profile_type != "user_defined":
        raise ValueError(
            "save_user_profile() ne doit être utilisé que pour des profils "
            "'user_defined' — les profils built_in sont verrouillés."
        )

    target_dir = user_profiles_dir or PROFILES_DIR
    target_dir.mkdir(parents=True, exist_ok=True)

    out_path = target_dir / f"{profile.profile_id}.json"
    with out_path.open("w", encoding="utf-8") as handle:
        json.dump(profile.to_dict(), handle, indent=2, ensure_ascii=False)

    return out_path


# ======================================================================
# CONFIGURATION PERSONNALISEE DE LA GRID BOX (recepteurs built_in)
# ======================================================================
#
# Un recepteur DEJA integre au logiciel (profile_type == "built_in") a
# une grid box d'origine, fixee dans receptor_profiles/<profile_id>.json
# et jamais modifiee par ce mecanisme. L'utilisateur peut neanmoins
# enregistrer SA propre position/taille de boite pour ce recepteur :
# elle est stockee a part, dans un fichier distinct, et appliquee
# automatiquement a chaque chargement du profil (voir load_profile())
# tant qu'elle n'est pas effacee via clear_user_grid_override().
#
# Un profil "user_defined" (import libre, Mode 2) n'utilise jamais ce
# mecanisme : il est deja entierement editable via save_user_profile().

USER_GRID_OVERRIDES_DIR = PROFILES_DIR / "user_grid_overrides"


def _user_grid_override_path(profile_id: str) -> Path:
    return USER_GRID_OVERRIDES_DIR / f"{profile_id}.json"


def get_user_grid_override(profile_id: str) -> Optional[GridBox]:
    """
    Grid box personnalisee active pour ce profil, si l'utilisateur en a
    enregistre une, sinon None.
    """
    path = _user_grid_override_path(profile_id)
    if not path.exists():
        return None
    try:
        with path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
        return GridBox.from_dict(data)
    except (OSError, ValueError, KeyError, json.JSONDecodeError):
        return None


def has_user_grid_override(profile_id: str) -> bool:
    return _user_grid_override_path(profile_id).exists()


def save_user_grid_override(profile_id: str, grid_box: GridBox) -> Path:
    """
    Enregistre une grid box personnalisee pour un recepteur DEJA present
    dans le logiciel. Reserve aux profils built_in : un profil importe
    librement se configure via save_user_profile(), pas ici.

    Une fois enregistree, cette configuration est reprise automatiquement
    a chaque demarrage (voir load_profile()), jusqu'a ce que
    clear_user_grid_override() soit appelee.
    """
    try:
        profile = load_profile(profile_id)
    except FileNotFoundError:
        raise ValueError(
            f"Impossible d'enregistrer une configuration personnalisee : "
            f"profil inconnu {profile_id!r}."
        ) from None

    if profile.profile_type != "built_in":
        raise ValueError(
            "save_user_grid_override() ne s'applique qu'aux recepteurs deja "
            "integres au logiciel (profile_type == 'built_in') — un "
            "recepteur importe librement se configure via "
            "save_user_profile()."
        )

    USER_GRID_OVERRIDES_DIR.mkdir(parents=True, exist_ok=True)
    out_path = _user_grid_override_path(profile_id)
    with out_path.open("w", encoding="utf-8") as handle:
        json.dump(
            {"center": list(grid_box.center), "size": list(grid_box.size)},
            handle,
            indent=2,
            ensure_ascii=False,
        )

    return out_path


def clear_user_grid_override(profile_id: str) -> None:
    """
    Supprime la configuration personnalisee de ce profil : au prochain
    chargement, load_profile() renverra a nouveau les valeurs d'origine
    (celles fournies avec le logiciel).
    """
    path = _user_grid_override_path(profile_id)
    if path.exists():
        path.unlink()


# ======================================================================
# COUPLES POMPE / DEREPRESSEUR
# ======================================================================
#
# La philosophie de VinaStudio est le filtre a DOUBLE selectivite :
# une molecule interessante doit bien se lier a la pompe d'efflux ET
# se lier a son derepresseur. Le docking d'une cible unique reste
# possible, mais c'est le couple qui porte la valeur scientifique.
#
# Un couple est declare dans les fichiers JSON eux-memes, via
# "partner_id" et "role" — aucun code a modifier pour en ajouter un.
#
#   role = "pump"      -> pompe d'efflux (ex. MexB, AcrB, MexY, AdeB)
#   role = "repressor" -> regulateur/derepresseur (ex. MexR, AcrR)
#
# La cle de campagne d'un couple est "<pump_id> + <repressor_id>",
# construite par make_pair_key(). L'ordre est toujours pompe d'abord :
# c'est lui qui determine quelle cible recoit les colonnes "_mexb" et
# laquelle recoit "_mexr" dans le CSV fusionne, de sorte que toute la
# chaine d'analyse existante (correlations, indice de selectivite,
# classement des hits) fonctionne a l'identique sur n'importe quel
# couple.

PAIR_SEPARATOR = " + "

PUMP_ROLES = {"pump", "pompe", "efflux", "efflux_pump", "transporter"}
REPRESSOR_ROLES = {
    "repressor",
    "derepressor",
    "derepresseur",
    "regulator",
    "regulateur",
    "tf",
}


def normalize_role(role) -> Optional[str]:
    """Ramene un role ecrit librement a "pump" ou "repressor"."""

    if not role:
        return None

    value = str(role).strip().lower().replace("-", "_").replace(" ", "_")

    if value in PUMP_ROLES:
        return "pump"

    if value in REPRESSOR_ROLES:
        return "repressor"

    return None


def short_label(profile: "ReceptorProfile") -> str:
    """
    Nom court et lisible pour les menus : "MexB", "AcrB", "MexY"...

    Priorite au champ short_name du JSON. A defaut, on decoupe le
    display_name sur le premier separateur rencontre, ce qui suffit
    dans la quasi-totalite des cas.
    """

    if profile.short_name:
        return str(profile.short_name).strip()

    name = str(profile.display_name or profile.profile_id).strip()

    for separator in (" — ", " - ", " – ", " (", ",", ":", "/"):
        if separator in name:
            name = name.split(separator)[0]

    name = name.strip(" -—–(),:")

    if not name:
        name = profile.profile_id

    if len(name) > 16:
        name = name[:16].rstrip()

    return name


def get_partner_ids(profile: "ReceptorProfile") -> list:
    """
    Tous les partenaires declares d'un profil, fusion de l'ancien champ
    unique partner_id et de la liste partner_ids, sans doublon, en
    conservant l'ordre d'apparition.
    """

    ids = []

    if profile.partner_id and profile.partner_id not in ids:
        ids.append(profile.partner_id)

    for partner_id in (profile.partner_ids or []):
        if partner_id and partner_id not in ids:
            ids.append(partner_id)

    return ids


def make_pair_key(pump_id: str, repressor_id: str) -> str:
    return f"{pump_id}{PAIR_SEPARATOR}{repressor_id}"


def is_pair_key(key) -> bool:
    return bool(key) and PAIR_SEPARATOR in str(key)


def parse_pair_key(key: str) -> tuple[str, str]:
    """"<a> + <b>" -> ("<a>", "<b>")."""

    parts = str(key).split(PAIR_SEPARATOR)

    if len(parts) != 2:
        raise ValueError(f"Cle de couple invalide : {key!r}")

    return parts[0].strip(), parts[1].strip()


def list_pairs() -> list[tuple[str, str]]:
    """
    Tous les couples declares, sous forme (pump_id, repressor_id).

    Un couple est retenu si les deux profils existent, se designent
    mutuellement via partner_id, et portent des roles complementaires.
    Le couple historique MexB/MexR est inclus d'office s'il est
    declare ; sinon l'interface continue de le gerer separement.
    """

    profiles: dict[str, ReceptorProfile] = {}

    for profile_id in list_profile_ids():
        try:
            profiles[profile_id] = load_profile(profile_id)
        except Exception:
            continue

    pairs: list[tuple[str, str]] = []
    seen: set[frozenset] = set()

    for profile_id, profile in profiles.items():

        role = normalize_role(profile.role)

        if role is None:
            continue

        for partner_id in get_partner_ids(profile):

            if partner_id not in profiles:
                continue

            partner = profiles[partner_id]

            # Declaration mutuelle exigee : le partenaire doit lister
            # profile_id parmi SES propres partenaires, sinon on
            # construirait un couple dont un seul cote est au courant.
            if profile_id not in get_partner_ids(partner):
                continue

            partner_role = normalize_role(partner.role)

            if partner_role is None or partner_role == role:
                continue

            if role == "pump":
                pump_id, repressor_id = profile_id, partner_id
            else:
                pump_id, repressor_id = partner_id, profile_id

            marker = frozenset((pump_id, repressor_id))

            if marker in seen:
                continue

            seen.add(marker)
            pairs.append((pump_id, repressor_id))

    return sorted(pairs)


def resolve_pair(key: str) -> tuple["ReceptorProfile", "ReceptorProfile"]:
    """
    "<a> + <b>" -> (profil pompe, profil derepresseur), dans cet ordre,
    quel que soit l'ordre ecrit dans la cle.
    """

    first_id, second_id = parse_pair_key(key)

    first = resolve_target_profile(first_id)
    second = resolve_target_profile(second_id)

    first_role = normalize_role(first.role)
    second_role = normalize_role(second.role)

    if first_role == "repressor" and second_role == "pump":
        return second, first

    return first, second


def link_pair(pump_id: str, repressor_id: str) -> None:
    """
    Declare un couple : AJOUTE repressor_id aux partenaires de pump (et
    reciproquement), sans effacer un eventuel partenaire deja declare.
    Un meme pompe peut ainsi etre couplee a plusieurs derepresseurs
    (ou sites) different — ex. CmeB avec les deux sites de CmeR.

    Force les roles a "pump" / "repressor". Aucune autre donnee du
    profil n'est touchee.
    """

    pump = load_profile(pump_id)
    repressor = load_profile(repressor_id)

    pump.role = "pump"
    if repressor.profile_id not in get_partner_ids(pump):
        pump.partner_ids = get_partner_ids(pump) + [repressor.profile_id]
    if pump.partner_id is None:
        pump.partner_id = repressor.profile_id

    repressor.role = "repressor"
    if pump.profile_id not in get_partner_ids(repressor):
        repressor.partner_ids = get_partner_ids(repressor) + [pump.profile_id]
    if repressor.partner_id is None:
        repressor.partner_id = pump.profile_id

    for profile in (pump, repressor):
        path = PROFILES_DIR / f"{profile.profile_id}.json"
        with path.open("w", encoding="utf-8") as handle:
            json.dump(profile.to_dict(), handle, indent=2, ensure_ascii=False)

    print(f"Couple declare : {make_pair_key(pump_id, repressor_id)}")


def set_short_name(profile_id: str, short: str) -> None:
    """Fixe le nom court affiche dans les menus."""

    profile = load_profile(profile_id)
    profile.short_name = short.strip()

    path = PROFILES_DIR / f"{profile.profile_id}.json"
    with path.open("w", encoding="utf-8") as handle:
        json.dump(profile.to_dict(), handle, indent=2, ensure_ascii=False)

    print(f"{profile_id} : nom court = {profile.short_name!r}")


def _cli() -> None:
    args = sys.argv[1:]

    if not args or args[0] in ("-h", "--help"):
        print(__doc__ or "")
        print("Usage :")
        print("  --list                        inventaire des profils")
        print("  --pairs                       couples declares")
        print("  --link <pompe> <derepresseur> declarer un couple")
        print("  --short <profile_id> <nom>    fixer le nom court")
        return

    command = args[0]

    if command == "--list":
        for profile_id in list_profile_ids():
            try:
                profile = load_profile(profile_id)
            except Exception as exc:
                print(f"  [ERREUR] {profile_id} : {exc}")
                continue
            print(
                f"  {profile_id:<32} court={short_label(profile):<14} "
                f"role={normalize_role(profile.role) or '-':<10} "
                f"partenaire={profile.partner_id or '-'}"
            )
        return

    if command == "--pairs":
        pairs = list_pairs()
        if not pairs:
            print("Aucun couple declare.")
            print("Utilise : --link <pompe> <derepresseur>")
            return
        for pump_id, repressor_id in pairs:
            print(f"  {make_pair_key(pump_id, repressor_id)}")
        return

    if command == "--link" and len(args) == 3:
        link_pair(args[1], args[2])
        return

    if command == "--short" and len(args) == 3:
        set_short_name(args[1], args[2])
        return

    print("Commande inconnue. Voir --help.")


if __name__ == "__main__":
    _cli()
