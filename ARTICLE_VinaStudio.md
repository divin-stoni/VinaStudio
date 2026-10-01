# VinaStudio : application de criblage virtuel moléculaire et d’analyse de sélectivité pour les cibles MexAB/MexR

**Divin Stoni MBANIMI**, **Cyr Abraham YONDZA KOUMBA** et **N’TOLLAUD Challenge Providence**  
UM6SS, Master 2 Biotechnologie et Santé

## Résumé

VinaStudio est une application de bureau développée en Python avec PySide6 pour le criblage virtuel moléculaire, l’analyse de sélectivité et la gestion de workflows scientifiques dans le contexte des cibles efflux MexAB/MexR chez Pseudomonas aeruginosa. L’outil combine la préparation de ligands, le docking moléculaire via AutoDock Vina, la fusion des résultats de docking en tableaux scientifiques, la détection de poches, la visualisation 3D et l’analyse des interactions. Il permet également de gérer les sessions de travail, de conserver les données intermédiaires et d’exporter les résultats complets pour la suite d’un pipeline d’analyse.

Le logiciel ne se limite pas à un simple dockeur générique. Il a été conçu pour répondre à un besoin biologique concret : évaluer un composé non seulement selon son affinité pour une cible de pompe d’efflux, mais aussi selon sa sélectivité par rapport à une cible associée. Cette logique de double filtre est au cœur de l’architecture du projet et constitue un élément central de la démarche scientifique. L’application soutient donc la décision de priorisation de molécules à partir d’un ensemble de critères structuraux, biophysiques et scientifiques.

Le présent article décrit les fonctionnalités du logiciel, son architecture, ses flux de travail scientifiques et son intérêt dans le cadre d’une démarche de bioinformatique appliquée à la découverte de molécules actives et sélectives. Il présente également les éléments de validation logicielle déjà mis en place, ainsi que la préparation du projet pour une soumission scientifique dans un cadre de publication de logiciel de recherche.

## Abstract

VinaStudio is a Python/PySide6 desktop application for virtual molecular screening, dual-target selectivity analysis, interaction profiling and session-based scientific workflow management. The software was developed for MexAB/MexR-related studies in *Pseudomonas aeruginosa*, while its modular design also supports other receptor and ligand collections. It integrates ligand preparation, AutoDock Vina docking, scientific fusion of docking outputs, statistical analysis, pocket and interaction inspection, three-dimensional visualization and complete session export.

The main methodological contribution of VinaStudio is the integration of docking scores from more than one biological target into a workflow designed for candidate prioritization. Instead of relying on a single affinity value, the user can examine target-specific scores, selectivity indices, group-level analyses and structural interaction patterns. The application therefore connects computational execution with scientific interpretation in a single desktop environment.

The project includes automated tests for session export, scientific result generation, signed selectivity calculations and viewer compatibility. This article presents the motivation, architecture, workflow, functionality, validation strategy and current limitations of VinaStudio. The software is intended to support reproducible computational research and to provide a practical foundation for subsequent experimental validation of prioritized compounds.

**Keywords:** molecular docking; virtual screening; AutoDock Vina; MexAB/MexR; selectivity analysis; PySide6; bioinformatics.

## Mots-clés

- docking moléculaire
- AutoDock Vina
- sélectivité MexAB/MexR
- logiciel de criblage virtuel
- analyse scientifique
- visualisation 3D
- PySide6
- bioinformatique

## 1. Introduction

Le développement de nouveaux composés bioactifs dans le domaine de la santé publique et de la biotechnologie repose souvent sur des étapes de criblage virtuel avant toute expérimentation de validation. Les outils de docking moléculaire sont devenus indispensables parce qu’ils permettent d’explorer rapidement des bibliothèques de molécules, d’estimer des affinités de liaison et de sélectionner des candidats potentiellement prometteurs. Toutefois, les études les plus utiles ne se limitent pas à la simple estimation d’une seule valeur d’affinité. Dans de nombreux cas biologiques, une molécule doit démontrer non seulement une bonne affinité pour une cible principale, mais aussi un comportement sélectif à l’égard d’un système de régulation ou d’un mécanisme biologique associé.

C’est précisément le contexte visé par VinaStudio. Initialement conçu pour la problématique MexAB/MexR liée à la résistance bactérienne chez Pseudomonas aeruginosa, le logiciel propose un environnement unifié permettant de préparer des ligands, lancer des dockings, fusionner les résultats scientifiques, analyser les interactions et comparer les performances entre plusieurs cibles biologiques. L’architecture du logiciel est conçue pour faire émerger un raisonnement de sélectivité double, en contrastant le score d’interaction sur un récepteur de pompe d’efflux avec celui sur une cible régulatrice ou associée.

Le projet ne se résume pas à une simple boîte à outils de docking ; il constitue un environnement de travail complet destiné à la recherche appliquée. Il accompagne la chaîne de traitement depuis l’import d’une librairie moléculaire jusqu’à l’export final des résultats, en passant par la préparation des structures, la gestion des profils de récepteurs, le calcul de scores et l’exploration visuelle des poses.

## 2. Contexte scientifique et motivation

Le système MexAB/MexR est associé à un réseau d’efflux chez Pseudomonas aeruginosa, une bactérie largement étudiée pour sa résistance aux antibiotiques. Dans ce contexte, les molécules candidates doivent être interprétées selon plusieurs dimensions : affinité de liaison, sélectivité, type de site de liaison, probabilité d’interaction sur cible principale et stabilité de la pose. Un docking conventionnel appliqué uniquement à une cible unique peut mener à des sélections trompeuses, surtout lorsque le mécanisme biologique implique un équilibre entre plusieurs composants d’un réseau.

La logique de VinaStudio s’inscrit dans cette réalité : le logiciel cherche à formaliser une approche de double sélectivité, à savoir la comparaison du comportement d’un ligand vis-à-vis d’une cible “pompe” et vis-à-vis d’une cible “régulatrice”. L’indice de sélectivité, calculé dans le pipeline scientifique du logiciel, permet d’ordonner les molécules en fonction de leur potentiel d’action sélective et de distinguer les candidats favorables de ceux qui présentent un risque de non-spécificité ou de mauvais profil d’interaction.

Cette approche scientifique répond à une nécessité qui est bien concrète en bioinformatique : un bon candidat n’est pas seulement une molécule qui se fixe fortement à une cible ; c’est aussi une molécule qui présente un profil compatible avec le mécanisme biologique recherché.

## 3. État de l’art et positionnement du logiciel

De nombreux outils de docking existent pour l’analyse de complexes ligand-protéine, mais ils sont souvent spécialisés dans des étapes isolées : préparation des ligands, docking, analyse visuelle ou export de résultats. Il est moins fréquent de trouver un environnement complet qui intègre simultanément :

- préparation de bibliothèques multi-molécules,
- gestion de profils de récepteurs,
- analyse de sélectivité double,
- visualisation structurale,
- export de résultats scientifiques,
- organisation de session de travail.

VinaStudio se positionne comme un logiciel de travail de laboratoire numérique, avec une logique orientée vers la recherche appliquée et la prise de décision expérimentale. L’objectif n’est pas simplement de calculer des scores, mais d’offrir un environnement de travail exploitable pour l’analyse scientifique, la comparaison de ligands et l’étude de cibles biologiques complexes.

## 4. Architecture logicielle

Le projet est structuré en modules cohérents et hiérarchisés, chacun correspondant à une étape du workflow. L’architecture logique est la suivante :

### 4.1 Interface utilisateur

Le cœur de l’application est l’interface graphique PySide6. Elle permet à l’utilisateur d’interagir avec les différentes phases du pipeline sans passer par des scripts shell ou des traitements fragmentés. La fenêtre principale comporte plusieurs zones de navigation et d’action : préparation des ligands, docking, analyse scientifique, visualisation et gestion de session.

La conception de l’interface met l’accent sur la simplicité et la guidabilité de l’utilisateur. Les actions sont organisées selon le besoin biologique : import de fichiers, préparation de ligands, lancement de docking, consultation des résultats, export de données et interprétation visuelle des structures.

### 4.2 Gestion des ligands

La phase de préparation des ligands prend en charge les fichiers SDF et les structures moléculaires en entrée. Le logiciel peut organiser les molécules selon différent modes de tri, intégrer des familles de composés, identifier les identifiants de structure et préparer les structures de manière cohérente pour le docking. Cette étape est essentielle car la qualité de la préparation des ligands impacte directement la fiabilité des résultats de docking.

### 4.3 Gestion des récepteurs et profils de docking

Le logiciel dispose d’un système de profils de récepteurs et de configuration du docking. Il permet de choisir les cibles biologiques, de définir les paramètres de grille de docking et d’adapter la mise en place du complexe ligand-récepteur. Cette couche de logique est cruciale pour les études multi-cibles, car les paramètres de docking doivent être cohérents avec la structure et le site d’interaction recherché.

### 4.4 Moteur de docking AutoDock Vina

Le moteur de docking est fondé sur AutoDock Vina, un outil largement utilisé pour le criblage virtuel. VinaStudio automatise la génération des configurations, le lancement du calcul, la récupération des meilleures poses et l’analyse des scores d’affinité. Les résultats sont ensuite fusionnés dans des formats exploitables scientifiquement, ce qui permet de passer d’un ensemble de sorties techniques à une table de données interprétable.

### 4.5 Analyse scientifique et statistiques

Une composante importante du projet est son moteur scientifique. Le code contient des fonctions de :

- détection de mode d’analyse,
- préparation des groupes de données,
- corrélation Pearson et Spearman,
- bootstrap et intervalles de confiance,
- tests de permutation,
- calcul de l’indice de sélectivité,
- classification de risque,
- filtrage dual et sélection des meilleurs candidats.

Cette partie du logiciel fournit un cadre d’analyse qui dépasse la simple comparaison de scores et permet de jauger les relations entre les affinités sur plusieurs cibles de manière robuste.

### 4.6 Visualisation et interactions

La visualisation du système est intégrée au workflow. Le logiciel propose du contenu 3D, la détection de poches et l’analyse des interactions via des modules de PLIP et des visualisations de complexes. Il permet ainsi de passer de la donnée quantitative à l’interprétation structurale, ce qui est essentiel pour traiter les résultats de docking avec un sens biologique.

### 4.7 Gestion de sessions et export

Le logiciel gère également un espace de travail de session, permet de stocker les données intermédiaires et d’exporter les résultats de manière structurée. Cette dimension n’est pas anecdotique : elle correspond à une bonne pratique de reproductibilité scientifique et de gestion de projet en recherche appliquée.

## 5. Fonctionnalités du logiciel

### 5.1 Préparation des ligands

VinaStudio permet d’importer des fichiers SDF ou des bibliothèques de ligands et de les préparer à des fins de docking. La préparation comprend :

- identification des molécules,
- gestion des familles et regroupements,
- nettoyage des identifiants,
- préparation de structures compatibles avec les workflows du moteur de docking.

### 5.2 Docking sur plusieurs cibles

Le logiciel prend en charge plusieurs profils biologiques et est pensé pour des situations multi-cibles. L’intérêt de cette conception est de permettre la comparaison d’une même molécule sur plusieurs contextes biologiques ou sites. La notion de profil de récepteur est centrale pour cette gestion.

### 5.3 Analyse de sélectivité

Le module scientifique du logiciel calcule un indice de sélectivité permettant de comparer le profil d’interaction sur plusieurs cibles. L’idée est d’évaluer si une molécule est seulement forte sur une cible ou si elle présente un comportement plus équilibré et potentiellement plus utile biologiquement. Cette approche est particulièrement pertinente pour la biologie des systèmes d’efflux et des modules de résistance.

### 5.4 Visualisation 3D et étude des interactions

La visualisation fournit une couche de compréhension nécessaire à toute décision scientifique. Elle permet de :

- afficher la structure d’un complexe,
- surligner les résidus ou les interactions majeures,
- inspecter les sites de liaison,
- comparer les poses potentielles,
- interpréter les résultats de manière intuitive.

### 5.5 Export et reproductibilité

Le logiciel exporte les données dans des formats structurés, et l’ensemble des résultats est conservé dans un contexte de session cohérent. Cette caractéristique répond à une exigence moderne de reproductibilité et de traçabilité scientifique.

## 6. Workflow logiciel

Le workflow typique de VinaStudio suit une logique intégrée et progressive :

1. Import des molécules et des structures d’entrée.
2. Préparation des ligands et validation des fichiers.
3. Sélection d’un ou plusieurs profils de récepteurs.
4. Définition des paramètres de docking.
5. Lancement du calcul avec AutoDock Vina.
6. Récupération des scores et des poses.
7. Conversion des sorties en tableaux scientifiques.
8. Analyse de corrélation, de sélectivité et de risque.
9. Visualisation 3D et interprétation des interactions.
10. Export de la session et conservation des données.

Ce workflow confère au logiciel une logique de chaîne de valeur complète, plutôt qu’une série d’étapes isolées et non connectées.

## 7. Validation et tests

Le projet a été consolidé par une suite de tests automatisés. Les tests couvrent notamment :

- export de session complet,
- import de fichiers dans le workspace session,
- création des fichiers de sortie scientifique,
- vérification des indices de selectivite,
- gestion des familles / groupes manquants,
- validation des pipelines statistiques,
- vérification du bon comportement du visualiseur 3D.

Les tests ont été exécutés avec la commande suivante :

```bash
cd /home/stoni/MexAB_MexR_Analyzer_BETA
./venv/bin/python -m pytest tests -q
```

La validation a abouti à un résultat stable : 15 tests passent, avec quelques avertissements non bloquants liés à la robustesse du bootstrap sur des jeux de données constants en statistique. Cette couche de validation est importante pour la préparation d’une publication scientifique, car elle permet de documenter la stabilité du logiciel et la reproductibilité de ses fonctions centrales. Elle ne remplace toutefois pas une validation expérimentale des molécules sélectionnées.

## 8. État de préparation pour une publication scientifique

Le projet est déjà dans une phase avancée de préparation pour une publication de logiciel scientifique. Plusieurs éléments de qualité sont présents :

- description précise des fonctionnalités,
- architecture logicielle claire,
- workflow scientifique explicite,
- tests automatisés,
- documentation de l’application,
- métadonnées de citation et checklist de soumission.

Les fichiers de publication ont été préparés dans le dépôt pour accompagner cette démarche, notamment le fichier de citation et la checklist JOSS. Cela montre que le projet est bien plus qu’un prototype : il s’inscrit dans une logique de logiciel scientifique exploitable, documenté, robuste et prêt à être partagé à la communauté.

## 9. Analyse critique et limites

Aucune application scientifique n’est parfaite, et VinaStudio ne fait pas exception. Plusieurs limites sont à souligner :

- le logiciel dépend de plusieurs outils externes comme AutoDock Vina, PLIP et d’autres composants de références biologiques,
- la visualisation 3D et le packaging sont soumis à des contraintes de dépendances système,
- certains aspects de l’interface ou de la personnalisation demeurent en constante évolution,
- le projet est encore en phase de maturation scientifique et doit faire l’objet d’un travail de validation sur des cas d’usage plus larges.

Ces limites ne remettent pas en cause la valeur scientifique du projet. Elles signalent plutôt qu’il s’agit d’un logiciel vivant et évolutif, conçu pour une utilisation de recherche appliquée et pour une amélioration continue.

## 10. Conclusion

VinaStudio constitue un logiciel de criblage virtuel moléculaire centré sur la question du ciblage et de la sélectivité dans un contexte biologique complexe. En réunissant les fonctions de préparation de ligands, docking, analyse scientifique, visualisation 3D et export de session, il répond à un besoin réel en bioinformatique et en biotechnologie. La double logique d’évaluation de cibles, qui est au cœur du logiciel, fait de VinaStudio un outil particulièrement utile pour les études orientées vers la sélection de molécules potentiellement actives et sélectives.

Le projet est donc à la fois un outil de travail scientifique concret et une base solide pour une publication de logiciel de recherche. Il est désormais bien documenté, testé et structuré pour une démarche de validation scientifique plus avancée. Son potentiel résident dans sa capacité à rapprocher le calcul de docking, la logique de sélection de molécules et l’interprétation biologique dans un environnement unique et utilisable.

## 11. Captures d’écran et légendes

Les captures d’écran de l’application ne sont pas incluses dans ce document généré en environnement sans interface graphique, mais les éléments suivants peuvent être utilisés comme légendes de figures lors de la préparation d’une version plus complète du manuscrit.

### Figure 1. Interface principale de VinaStudio.
L’écran d’accueil présente la navigation principale du logiciel, les modules de préparation, de docking, d’analyse scientifique et de visualisation. Cette interface centralise le workflow complet et permet à l’utilisateur de suivre le pipeline sans quitter la plateforme.

### Figure 2. Préparation des ligands et gestion des fichiers SDF.
La vue de préparation permet l’import de bibliothèques de composés, la gestion des familles de molécules et la création de structures prêtes à être évaluées par le moteur de docking.

### Figure 3. Paramétrage du docking et sélection des cibles.
La fenêtre de configuration comprend les paramètres du dockeur, les profils de récepteurs et les options associées à la grille de docking et aux sites biologiques d’intérêt.

### Figure 4. Résultats de docking et vue scientifique.
Les sorties du dockage sont fusionnées dans des tableaux scientifiques avec des colonnes d’affinité, d’indice de sélectivité et d’analyse de groupes. Cette vue permet d’identifier les meilleurs candidats selon des critères scientifiques.

### Figure 5. Analyse de visualisation 3D et interactions.
La vue de visualisation permet d’inspecter les complexes, les poches et les interactions clés afin d’interpréter les poses et les résultats d’affinité dans leur contexte structural.

### Figure 6. Export de session et reproductibilité.
Le module d’export permet de conserver l’ensemble du contexte de calcul, ce qui est essentiel pour la traçabilité, la reproductibilité et l’exploitation des résultats dans une démarche de recherche.

## 12. Références

1. Trott, O., & Olson, A. J. (2010). AutoDock Vina: improving the speed and accuracy of docking with a new scoring function, efficient optimization, and multithreading. Journal of Computational Chemistry.
2. O’Boyle, N. M., et al. (2011). Open Babel: An open chemical toolbox. Journal of Cheminformatics.
3. Salentin, S., et al. (2015). PLIP: fully automated protein-ligand interaction profiler. Nucleic Acids Research.
4. Morris, G. M., et al. (2009). AutoDock4 and AutoDockTools4: automated docking with selective receptor flexibility. Journal of Computational Chemistry.
5. Stover, C. K., et al. (2000). Complete genome sequence of Pseudomonas aeruginosa PAO1, an opportunistic pathogen. Nature.
6. Poole, K. (2001). Multidrug resistance in Gram-negative bacteria. Current Opinion in Microbiology.
7. World Health Organization (2024). Bacterial priority pathogens list, 2024: bacterial pathogens of public health importance to guide research, development and strategies to prevent and control antimicrobial resistance.

## 13. Remerciements

Les auteurs remercient l’environnement académique et scientifique dans lequel le projet a été développé, ainsi que les personnes ayant contribué aux tests sur les systèmes Windows 11 et Windows 10. Le projet s’inscrit également dans le cadre académique du Master 2 de Biotechnologie et Santé à l’UM6SS.

## 14. Déclaration de contribution

- Divin Stoni MBANIMI : auteur principal, conception du logiciel, architecture, développement et intégration scientifique.
- Cyr Abraham YONDZA KOUMBA : contribution au test et à la validation sur Windows 11.
- N’TOLLAUD Challenge Providence : contribution au test et à la validation sur Windows 10.

## 15. Conclusion finale

VinaStudio représente une proposition logicielle complète et scientifiquement orientée pour le criblage virtuel moléculaire appliqué à des systèmes biologiques complexes. Sa valeur réside dans son intégration fonctionnelle, sa capacité à soutenir la décision scientifique et sa préparation avancée pour une publication de logiciel en bioinformatique.
