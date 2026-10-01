# VinaStudio — analyse de docking moléculaire et filtrage dual MexB/MexR

VinaStudio est une application de bureau Python/PySide6 destinée au criblage virtuel moléculaire et à l’analyse de sélectivité sur des cibles biologiques liées au système efflux **MexAB-OprM** chez *Pseudomonas aeruginosa*. Le projet est centré sur l’idée que le docking ne doit pas être évalué seulement par son score sur la pompe efflux, mais aussi par son impact sur le régulateur de transcription associé.

Le cœur fonctionnel du logiciel est le concept de **double filtre** :

- le ligand est évalué par sa capacité à se lier à la pompe d’efflux (**MexB**, ou plus généralement un récepteur pompe)
- il est aussi évalué par sa capacité à interagir avec le régulateur / répresseur (**MexR**, ou autre cible associée)
- la candidature est retenue uniquement si elle est acceptable sur les deux axes, avec un indice de sélectivité calculé et une classification issue du pipeline scientifique de l’application

Le code présent dans le dépôt montre clairement que l’application n’est pas seulement un dockeur générique : elle contient des modules de gestion de profils de récepteurs, préparation de ligands, analyse statistique, visualisation de structures et intégration de données phytomoléculaires.

---

## 1. Vue d’ensemble du logiciel

Le dépôt contient une application GUI complète avec des workflows de type :

- préparation de fichiers SDF vers PDBQT
- sélection de ligands par famille
- gestion des profils de récepteurs
- docking AutoDock Vina sur une ou plusieurs cibles
- fusion des résultats de docking en un tableau scientifique
- calculs statistiques (corrélations, filtres, sélection de hits)
- visualisation des pois ou des interactions 3D / PLIP
- gestion de session et export des résultats
- onglet spécifique pour les phytomolécules et les données de structure / de famille

L’application est organisée autour de `src/gui/main_window.py` et de l’entrée `src/main.py`, avec la logique métier répartie dans `src/docking/`, `src/analysis/`, `src/visualization/`, `src/tools/` et `src/session_*`.

---

## 2. Fonctionnalités réellement présentes dans le code

### 2.1 Préparation des ligands

La page “Préparer les SDF” permet de :

- importer un ou plusieurs fichiers `.sdf`
- importer un dossier entier contenant des molécules SDF
- regrouper les ligands par familles
- renommer les molécules selon plusieurs modes : conserver le nom, nettoyer le nom, détecter les identifiants CID
- exporter les structures préparées en fichiers `.pdbqt` dans le dossier `docking/ligands/prepared`
- suivre l’état de préparation dans un journal

Le moteur de préparation est centré sur `src/docking/sdf_preparer.py` et les opérations sont orchestrées depuis la page de docking dans `src/gui/main_window.py`.

### 2.2 Gestion des ligands PDBQT

La page “Ligands PDBQT” permet :

- ajouter des fichiers `.pdbqt`
- ajouter des dossiers contenant plusieurs ligands PDBQT
- regrouper les ligands par famille
- sélectionner tous les ligands ou une partie de la sélection
- filtrer / organiser les fichiers dans une table de résultats
- passer directement à la phase de docking à partir de la sélection

Cette logique est implémentée dans la classe `DockingPage` de `src/gui/main_window.py`.

### 2.3 Cibles biologiques et récepteurs

Le logiciel ne se limite pas à une cible unique.

Le code prend en charge :

- récepteur historique `MexB`
- récepteur historique `MexR`
- mode “MexB + MexR” (campagne bi-cible)
- profils génériques d’autres récepteurs issus de `receptor_profiles/`
- import de nouveaux récepteurs PDB / PDBQT pendant la session
- gestion de `grid box` (centre et taille du site de docking)
- surcharges de paramètres de grid box par profil
- couple de cibles “pompe + répresseur” via des profils déclarés dans le système de profils

Les fichiers clés sont :

- `src/docking/receptor_profile.py`
- `src/docking/receptor_manager.py`
- `src/docking/config_manager.py`
- `src/docking/vina_engine.py`

### 2.4 Docking AutoDock Vina

Le moteur de docking est basé sur AutoDock Vina.

Les fonctions principales sont :

- résolution automatique de l’exécutable `vina`
- création d’une configuration de docking par cible
- lancement d’un docking ligand par ligand
- génération des fichiers de sortie PDBQT
- parsing des logs Vina
- gestion du résultat individuel pour chaque ligand
- récupération des meilleurs modes et des affinités calculées
- export des résultats CSV

Le point d’entrée du moteur est `src/docking/vina_engine.py`, et les exécutions asynchrones passent par `src/docking/vina_worker.py`.

### 2.5 Visualisation 3D et détection de poches

La page de docking contient un panneau de visualisation 3D avec :

- vue du récepteur sous forme HTML / WebEngine
- contrôle de la boîte de docking
- détection des poches via `fpocket`
- sélection d’une poche dans une liste déroulante
- navigation précédente / suivante
- mode aperçu global ou vue détaillée d’une poche
- visualisation des résidus et du contexte de liaison

La logique est fortement liée à :

- `src/gui/viewer_template.py`
- `src/gui/visualization_bridge.py`
- `src/visualization/visualization_manager.py`
- `src/visualization/plip_runner.py`
- `src/visualization/interaction_3d.py`

Le code montre également la présence d’un pipeline PLIP et de diagrammes d’interaction 2D.

### 2.6 Analyse scientifique et scores intégrés

Le dépôt contient un moteur de fusion scientifique de résultats de docking.

Le fichier `src/scientific_fusion.py` :

- lit un CSV de docking
- détecte les colonnes d’affinité pour les cibles
- normalise automatiquement les colonnes scientifiques
- construit des colonnes comme `dg_mexb`, `dg_mexr`, `indice_selectivite`
- fusionne les résultats dans des fichiers “scientifiques” exploitable pour le moteur statistique
- produit aussi une méta-fichier JSON pour les libellés de récepteurs

La logique de statistiques est dans :

- `src/analysis/statistics_pipeline.py`
- `src/stats_engine.py`

Les analyses implémentées incluent :

- détection automatique du mode d’analyse (global / par groupes)
- corrélation Pearson et Spearman
- bootstrap CI sur la corrélation
- permutation test
- leave-one-out
- homogénéité des pentes
- calcul de l’indice de sélectivité et classification des candidats
- filtre dual sur les candidats retenus / exclus
- top candidates

Le moteur de calcul scientifique est donc bien présent et non seulement descriptif.

### 2.7 Analyse des interactions hôtes / ligands

Le dépôt contient plusieurs modules d’analyse structurale et d’interaction :

- `src/analysis/interaction_analyzer.py`
- `src/analysis/interaction_summary.py`
- `src/analysis/pose_validator.py`
- `src/analysis/pose_convergence.py`
- `src/analysis/pocket_detector.py`
- `src/analysis/structural_validator.py`
- `src/analysis/hit_selector.py`
- `src/analysis/integrated_hit_report.py`

Ils permettent de :

- tester la convergence des poses
- valider les poses
- détecter les poches
- synthétiser les interactions
- produire des rapports de hits intégrés

### 2.8 Onglet phytomolécules

Le dépôt contient un onglet spécifique “Phytomolécules” dans `src/gui/phyto_page.py`.

Cette partie du logiciel comprend :

- recherche de molécules / plantes
- cartes d’espèce
- image de la plante ou structure 2D de la molécule
- suggestions de molécules si le nom est ambigu
- arbre des familles chimiques
- navigation de résultats PubChem / structure associée
- extraction de structures en SDF avec préfixe
- affichage d’informations de type propriété de molécule
- retour vers le tableau de résultats sans perdre le contexte

Cette fonctionnalité est bien concrète dans le code et représente un module d’exploration des molécules d’intérêt, distinct du docking classique.

### 2.9 Gestion de session et export

Dans le code, la session est gérée par :

- `src/session_manager.py`
- `src/session_runtime.py`

Le logiciel met en place un espace de travail de session qui :

- stocke les fichiers importés ou générés pendant la session
- évite la pollution des fichiers de référence tant que l’utilisateur n’exporte pas explicitement
- permet le nettoyage à la fermeture de session
- propose un bouton “Tout exporter la session” dans l’interface

### 2.10 Interface et personnalisation

La GUI est développée avec PySide6 et contient :

- navigation secondaire par sous-pages
- onglets de configuration
- style “verre liquide” et thème personnalisé
- gestion des langues / i18n
- écrans de paramètres d’apparence et de libellés
- thèmes / palettes / widgets visuels spécifiques

Le fichier `src/gui/main_window.py` contient des éléments de design et de personnalisation structuraux importants.

---

## 3. Stack technique

Le dépôt utilise principalement :

- Python 3
- PySide6 pour l’interface graphique
- AutoDock Vina pour le docking moléculaire
- Open Babel pour les transformations chimiques / préparation de ligands
- PLIP pour l’analyse des interactions ligand-récepteur
- RDKit / structure 2D / visualisation moléculaire
- pandas, NumPy, SciPy, statsmodels pour le moteur scientifique
- matplotlib et autres utilitaires de visualisation

---

## 4. Point d’entrée et lancement

Pour lancer l’application depuis le dépôt :

```bash
cd /home/stoni/MexAB_MexR_Analyzer_BETA
python src/main.py
```

Ou, si l’environnement virtuel du projet est utilisé :

```bash
cd /home/stoni/MexAB_MexR_Analyzer_BETA
./venv/bin/python src/main.py
```

---

## 5. Organisation du projet

```text
MexAB_MexR_Analyzer_BETA/
├── src/
│   ├── analysis/          # pipeline scientifique et analyse des interactions
│   ├── docking/           # moteur de docking, récepteurs, profils, Vina
│   ├── gui/               # interface utilisateur PySide6
│   ├── visualization/     # visualisation 3D / PLIP / poses
│   ├── tools/             # outils runtime et utilitaires
│   ├── main.py            # point d’entrée principal
│   ├── scientific_fusion.py
│   ├── stats_engine.py
│   ├── session_manager.py
│   ├── session_runtime.py
│   └── phyto_api.py
├── docking/               # résultats, ligands préparés, profils
├── receptor_profiles/     # fichiers de profils de récepteurs
├── docs/
├── requirements.txt
├── README.md
├── build_and_package.sh
├── build_deb_final.sh
└── run_gui.py
```

---

## 6. Ce que le projet fait concrètement

En pratique, le logiciel permet de :

1. préparer une bibliothèque de ligands depuis des fichiers SDF
2. sélectionner une ou plusieurs cibles biologiques
3. préparer les paramètres de docking (grid box, nombre de modes, exhaustivité)
4. exécuter un criblage sur plusieurs ligands avec Vina
5. corriger / normaliser / fusionner les sorties de docking
6. calculer les scores de sélectivité et les indices associés
7. détecter les meilleurs hits par filtre dual
8. analyser les interactions et la validité des poses
9. visualiser les structures et poches
10. explorer des phytomolécules et les intégrer à un workflow d’analyse
11. exporter ou conserver les résultats pour une session de travail

---

## 7. Limites / point de vigilance

Le dépôt montre un projet actif avec plusieurs modules fonctionnels, mais il reste un logiciel de recherche et d’évolution. Quelques éléments du code indiquent qu’une partie de l’intégration 3D, la dépendance vis-à-vis des outils externes, ou les workflows de packaging sont encore en phase de stabilisation :

- certains modules de visualisation 3D sont gardés pour des intégrations ou développement ultérieurs
- la dépendance à fpocket, PLIP, Open Babel et AutoDock Vina demeure explicite
- des scripts de diagnostic et de correctif sont présents au niveau du dépôt, ce qui indique une phase de développement / débogage intensive

Ces éléments ne retirent pas la présence réelle des fonctionnalités principales, mais ils doivent être considérés comme des indications de contexte de développement.

---

## 8. Licence et citation

Le projet est distribué sous licence MIT, selon le fichier de licence du dépôt.

La métadonnée de citation est disponible dans [CITATION.cff](CITATION.cff), et une checklist de préparation pour une soumission JOSS est fournie dans [JOSS_CHECKLIST.md](JOSS_CHECKLIST.md).

Pour citer ce logiciel dans un article scientifique ou un rapport de recherche, utilisez les informations de [CITATION.cff](CITATION.cff). L’archive de dépôt doit ensuite être associée à un URL publique et à une liste finale d’auteurs avant soumission formelle à JOSS.

---

## 9. Résumé court

VinaStudio est un logiciel de criblage virtuel moléculaire basé sur AutoDock Vina, conçu pour analyser des molécules selon un critère double cible. Il regroupe :

- préparation de ligands,
- docking sur plusieurs cibles,
- gestion de profils de récepteurs,
- fusion scientifique des résultats,
- analyse statistique de corrélation et de sélectivité,
- visualisation de structures / poches,
- contrôle de session,
- exploration de phytomolécules et de familles chimiques.

C’est donc un outil de recherche et de décision en bioinformatique moléculaire, avec une forte orientation “dockage + analyse + sélectivité” plutôt qu’un simple dockeur générique.
