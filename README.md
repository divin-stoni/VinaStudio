# VinaStudio — Molecular Docking & Analysis

**VinaStudio** est une application de bureau pour le criblage virtuel (docking moléculaire) et l'analyse statistique de candidats inhibiteurs de la pompe d'efflux **MexAB-OprM** chez *Pseudomonas aeruginosa*.

Le logiciel automatise une chaîne complète : préparation des ligands → docking (AutoDock Vina) → analyse des interactions (PLIP) → visualisation 3D, puis enchaîne directement vers un module d'analyse statistique dédié (corrélation MexB/MexR, indice de sélectivité, filtre à double critère, seuil de risque de dérépression via MexR).

## Pourquoi cet outil

De nombreux étudiants réalisent du docking moléculaire mais restent limités à la paillasse faute d'accès simple à la ligne de commande. VinaStudio vise à rendre le criblage in silico sur la pompe MexAB-OprM accessible via une interface graphique, sans connaissance préalable en bioinformatique.

## Fonctionnalités

- **Docking** : récepteurs MexB (PDB 3W9J) et MexR (PDB 1LNW) pré-configurés
- **Analyse des interactions** : intégration PLIP, visualisation 3D (ChimeraX)
- **Module statistique** : corrélations Pearson/Spearman, régression, bootstrap, corrélation partielle, indice de sélectivité, filtre à double critère
- **Import externe** : possibilité d'importer des résultats de docking déjà réalisés ailleurs (CSV) pour l'analyse statistique seule
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

Python / PySide6 · AutoDock Vina · Open Babel · PLIP · RDKit · pandas, NumPy, SciPy, statsmodels · Matplotlib · UCSF ChimeraX

## Contexte scientifique

Ce logiciel s'appuie sur la méthodologie développée dans :

- *Criblage virtuel et évaluation in silico d'antidépresseurs comme inhibiteurs de la pompe d'efflux MexB* — ChemRxiv, DOI: [10.26434/chemrxiv.15005724](https://doi.org/10.26434/chemrxiv.15005724)
- *Un filtre computationnel à double critère pour l'identification d'inhibiteurs sélectifs de la pompe d'efflux MexAB-OprM* — ChemRxiv, DOI: [10.26434/chemrxiv.15007681](https://doi.org/10.26434/chemrxiv.15007681)

## Auteur

Divin Stoni Mbanimi — Master 1 Biotechnologie et Santé, Université Mohammed VI des Sciences et de la Santé (UM6SS), Casablanca
[ORCID: 0009-0005-7460-9913](https://orcid.org/0009-0005-7460-9913)

## Licence

À définir.
