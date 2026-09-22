# MexAB-OprM Analyzer : un outil statistique dédié à l'étude de la résistance bactérienne aux antibiotiques

## Contexte scientifique

La résistance aux antibiotiques par efflux actif est l'un des mécanismes les plus étudiés en microbiologie moléculaire, en particulier chez les bactéries à Gram négatif comme *Pseudomonas aeruginosa*. Le système de pompe à efflux **MexAB-OprM**, régulé par le répresseur transcriptionnel **MexR**, joue un rôle central dans l'expulsion de composés toxiques hors de la cellule bactérienne — dont de nombreux antibiotiques.

L'étude *in silico* de ce système passe souvent par des campagnes de **docking moléculaire**, qui estiment l'énergie de liaison (ΔG) de composés candidats à la fois sur la protéine de transport **MexB** et sur le répresseur **MexR**. Croiser ces deux valeurs permet d'identifier des molécules à fort potentiel : celles qui interagissent efficacement avec MexB sans dérépresser le système via MexR, ou inversement, celles présentant un profil de sélectivité favorable.

C'est précisément ce travail de croisement, de validation statistique et de classification que **MexAB-OprM Analyzer** automatise.

## Qu'est-ce que MexAB-OprM Analyzer ?

MexAB-OprM Analyzer est une application de bureau développée en **Python** (interface PySide6, calculs statistiques via SciPy/statsmodels, visualisations via Matplotlib), conçue pour reproduire et industrialiser les analyses statistiques associées aux données de docking ΔG(MexB)/ΔG(MexR).

Le logiciel fonctionne selon deux modes complémentaires.

### Mode 1 — Reproduction complète

Ce mode s'utilise lorsque l'on dispose déjà des valeurs réelles ΔG(MexB) **et** ΔG(MexR) pour un jeu de composés. Il permet de :

- calculer les corrélations de Pearson et de Spearman, globalement et par famille chimique, avec correction pour tests multiples (FDR, méthode de Benjamini-Hochberg) ;
- estimer la robustesse statistique de ces corrélations via un **bootstrap** (intervalles de confiance à 95 %, nombre d'itérations paramétrable) ;
- effectuer une analyse **leave-one-out**, afin d'identifier les composés qui influencent le plus fortement la corrélation observée ;
- calculer un **indice de sélectivité (SI)**, avec classement percentile et classification de risque selon un seuil de référence (par défaut calibré sur la pyocyanine) ;
- lorsque la masse moléculaire (MW) et le coefficient de partition (LogP) sont disponibles, réaliser une **régression multiple** et une **corrélation partielle**, afin de vérifier que la corrélation ΔG(MexB)/ΔG(MexR) n'est pas un artefact des propriétés physico-chimiques des composés.

### Mode 2 — Prédictif

Ce mode s'adresse aux situations où seul ΔG(MexB) est connu pour de nouveaux composés — un cas fréquent lorsqu'une campagne de docking cible uniquement le transporteur MexB. À partir d'un **jeu de référence de 139 composés** (pour lesquels ΔG(MexB) et ΔG(MexR) sont tous deux connus), le logiciel calibre un modèle de régression, puis prédit ΔG(MexR) pour les nouveaux composés, avec intervalle de confiance associé. Si MW et LogP sont disponibles à la fois dans le jeu de référence et dans le jeu à prédire, ils sont intégrés comme covariables pour affiner la prédiction.

## Une détection intelligente des données d'entrée

L'un des points forts du logiciel est sa capacité à s'adapter à des fichiers CSV hétérogènes. Plutôt que d'exiger un format de colonnes rigide, MexAB-OprM Analyzer **détecte automatiquement** les colonnes pertinentes — ΔG(MexB), ΔG(MexR), groupe/famille, nom de molécule, MW, LogP — quelle que soit leur orthographe exacte : casse, séparateurs (`_`, `-`, espace), préfixes ou suffixes (`delta_MexB`, `DG-MEXB`, `MexB_score`, etc. sont tous reconnus). Les colonnes non reconnues sont simplement ignorées, sans perturber l'analyse.

## Une interface bilingue et accessible

L'interface propose une bascule instantanée entre le français et l'anglais, ainsi qu'une fenêtre d'aide intégrée détaillant le fonctionnement du logiciel, les motifs de colonnes reconnus et ses limites connues — une attention particulière portée à l'accessibilité et à la transparence méthodologique, essentielle dans un contexte de recherche scientifique.

## Export et reproductibilité

Chaque analyse peut être exportée en un clic : un classeur Excel regroupant l'ensemble des tables de résultats, accompagné d'un dossier de figures haute résolution (300 dpi équivalent, format PNG), prêtes à être intégrées dans une publication ou un rapport.

## Distribution

Le logiciel est distribué sous forme d'exécutable autonome (packagé avec PyInstaller), installable sur Linux via un paquet `.deb` natif qui l'intègre proprement au menu d'applications du système, sans nécessiter d'environnement Python préconfiguré côté utilisateur final.

## Conclusion

En automatisant un pipeline d'analyse statistique auparavant réalisé manuellement — corrélations, robustesse, régression, classification — MexAB-OprM Analyzer réduit le temps de traitement des campagnes de docking moléculaire tout en garantissant une méthodologie statistique rigoureuse et reproductible, directement accessible aux chercheurs sans expertise en programmation.
