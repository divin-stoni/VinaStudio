# VinaStudio — Molecular Docking & Analysis

**VinaStudio** est une application de bureau pour le criblage virtuel (docking moléculaire) et l'analyse statistique de candidats inhibiteurs de la pompe d'efflux **MexAB-OprM** chez *Pseudomonas aeruginosa*.

L'automatisation du docking (Vina, préparation des ligands, extraction des poses) existe déjà dans d'autres outils (PyRx, VSpipe, EasyDock). Ce que VinaStudio apporte de spécifique, et qui constitue le cœur du logiciel, c'est le **filtre à double critère** : un bon inhibiteur de MexB n'est pas forcément un candidat sûr — il peut aussi dé-réprimer le régulateur MexR et donc *sur-exprimer* la pompe qu'on cherche à inhiber. La plupart des criblages virtuels ignorent ce risque et classent les candidats sur le seul score de docking (ΔG MexB).

VinaStudio calcule systématiquement deux affinités (MexB *et* MexR) pour chaque candidat, puis applique un double filtre :
1. **Efficacité** — ΔG(MexB) suffisamment favorable
2. **Sécurité de régulation** — ΔG(MexR) moins négatif qu'un seuil de risque calibré sur un contrôle positif de dérépression (pyocyanine)

Un candidat n'est retenu que s'il passe les deux filtres. Cette approche a révélé qu'un classement au score MexB seul aurait sélectionné des molécules "à risque" (ex. Vilazodone) et écarté à tort des candidats plus sûrs (ex. Sertraline, Opipramol) — validée sur 139 composés à travers 4 familles chimiques (r = 0,834 à 0,924 selon la famille).

## Pourquoi cet outil

Deux problèmes à la fois : le docking classique ignore le risque de dérépression, et les étudiants qui voudraient appliquer ce contrôle restent souvent limités à la paillasse faute d'accès simple à la ligne de commande. VinaStudio rend le double filtre — le criblage en lui-même — accessible via une interface graphique, sans connaissance préalable en bioinformatique.

## Fonctionnalités

- **Filtre à double critère** (cœur du logiciel) : calcul de l'indice de sélectivité, seuil de risque de dérépression réglable, classement des candidats efficacité + sécurité
- **Mode prédictif** : estimation du risque MexR à partir du seul score MexB (sans redocker), basé sur la corrélation MexB/MexR validée statistiquement
- **Docking dual-cible** : récepteurs MexB (PDB 3W9J) et MexR (superposition 1LNW) pré-configurés avec grilles de docking calibrées (AutoDock Vina)
- **Analyse des interactions** : calcul PLIP, diagrammes d'interaction 2D (reconstruction moléculaire RDKit) fidèles à la géométrie du complexe
- **Statistiques avancées** : corrélations Pearson/Spearman par famille avec correction FDR, bootstrap, leave-one-out, corrélation partielle (contrôle MW/LogP), ANCOVA d'homogénéité des pentes
- **Import externe** : possibilité d'importer des résultats de docking déjà réalisés ailleurs (CSV) pour appliquer le filtre à double critère sans redocker
- **Frontière de session** : tout résultat généré pendant une session est temporaire tant qu'il n'est pas explicitement exporté par l'utilisateur ; nettoyage automatique à l'ouverture/fermeture, sans jamais toucher aux fichiers d'entrée, au code source ou aux exports déjà réalisés
- **Interface** : français / anglais

## Téléchargement

Dernière version disponible sur la page [Releases](https://github.com/divin-stoni/VinaStudio/releases/latest) :

| Plateforme | Fichier |
|---|---|
| Windows | `VinaStudio.exe` |
| Linux (Ubuntu/Debian, installable) | `vinastudio_x.x.x_amd64.deb` |
| Linux (archive portable) | `VinaStudio-Linux-x86_64.tar.gz` |

### Installation

**Windows** : télécharger et lancer `VinaStudio.exe`. L'exécutable n'étant pas signé numériquement, Windows SmartScreen peut afficher un avertissement au premier lancement — cliquer sur *Informations complémentaires* puis *Exécuter quand même*.

**Linux (.deb)** :
```bash
sudo apt install ./vinastudio_x.x.x_amd64.deb
```
L'application apparaît ensuite dans le menu des applications.

**Linux (archive portable)** :
```bash
tar -xzf VinaStudio-Linux-x86_64.tar.gz
cd VinaStudio-Linux-x86_64
./VinaStudio
```

## Stack technique

Python / PySide6 (interface) · AutoDock Vina 1.2.x (docking) · Open Babel (conversion de formats chimiques) · PLIP (calcul des interactions ligand-récepteur) · RDKit (reconstruction moléculaire et rendu des diagrammes d'interaction 2D) · pandas, NumPy, SciPy, statsmodels (moteur statistique) · Matplotlib (figures)

UCSF ChimeraX est détecté comme dépendance externe par le logiciel, mais son intégration (visualisation 3D des poses) est fournie sous forme de scripts autonomes, non encore branchés à l'interface graphique actuelle. L'espace **Visualisation** de l'application s'appuie exclusivement sur le pipeline PLIP + diagrammes d'interaction 2D.

## Contexte scientifique

Ce logiciel s'appuie sur la méthodologie développée dans :

- *Criblage virtuel et évaluation in silico d'antidépresseurs comme inhibiteurs de la pompe d'efflux MexB* — ChemRxiv (v3) : [https://chemrxiv.org/doi/full/10.26434/chemrxiv.15005724/v3](https://chemrxiv.org/doi/full/10.26434/chemrxiv.15005724/v3)
- *Un filtre computationnel à double critère pour l'identification d'inhibiteurs sélectifs de la pompe d'efflux MexAB-OprM* — ChemRxiv (v2) : [https://chemrxiv.org/doi/full/10.26434/chemrxiv.15007681/v2](https://chemrxiv.org/doi/full/10.26434/chemrxiv.15007681/v2)

## Auteur

Divin Stoni Mbanimi — Master 1 Biotechnologie et Santé, Université Mohammed VI des Sciences et de la Santé (UM6SS), Casablanca
[ORCID: 0009-0005-7460-9913](https://orcid.org/0009-0005-7460-9913)

## Licence

MIT
