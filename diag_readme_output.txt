======================================================================
1) Toute reference a ChimeraX dans le code source (hors venv/.git)
======================================================================
./src/analysis/structural_validator.py:18:avec ChimeraX ou Discovery Studio.
./src/environment/environment_manager.py:61:                name="ChimeraX",
./src/environment/environment_manager.py:62:                key="chimerax",
./src/environment/environment_manager.py:63:                commands=["chimerax"],
./src/environment/environment_manager.py:410:    # CHIMERAX
./src/environment/environment_manager.py:413:    def detect_chimerax(self, dependency):
./src/environment/environment_manager.py:416:            self.get_saved_path("chimerax")
./src/environment/environment_manager.py:418:                ["chimerax"]
./src/environment/environment_manager.py:444:                    "ChimeraX version"
./src/environment/environment_manager.py:486:        elif dependency.key == "chimerax":
./src/environment/environment_manager.py:488:            self.detect_chimerax(
./src/diagnostic_analyse.txt:778:  def launch_chimerax(commands)   (l.287)
./src/diagnostic_analyse.txt:784:      def _load_chimerax_path(self)   (l.64)
./src/diagnostic_analyse.txt:788:      def build_chimerax_commands(self)   (l.192)
./src/diagnostic_analyse.txt:809:      def _load_chimerax_path(self)   (l.41)
./src/tools/tool_manager.py:65:            "chimerax": {
./src/tools/tool_manager.py:66:                "name": "ChimeraX",
./src/tools/tool_manager.py:68:                "executables": ["chimerax", "ChimeraX"],
./src/tools/tool_manager.py:340:    # CHIMERAX
./src/tools/tool_manager.py:343:    def check_chimerax(self):
./src/tools/tool_manager.py:344:        definition = self.definitions["chimerax"]
./src/tools/tool_manager.py:352:            "/usr/lib/ucsf-chimerax/bin/ChimeraX",
./src/tools/tool_manager.py:353:            "/usr/bin/chimerax",
./src/tools/tool_manager.py:354:            "/usr/local/bin/chimerax",
./src/tools/tool_manager.py:365:                key="chimerax",
./src/tools/tool_manager.py:368:                message="ChimeraX introuvable."
./src/tools/tool_manager.py:378:                key="chimerax",
./src/tools/tool_manager.py:386:            key="chimerax",
./src/tools/tool_manager.py:402:            "chimerax": self.check_chimerax(),
./src/diagnose_docking_ui.py:53:    "pdb", "pdbqt", "vina", "fpocket", "csv", "gui", "sdf", "chimerax",
./src/visualization/pose_manager.py:34:        self.chimerax_path = self._load_chimerax_path()
./src/visualization/pose_manager.py:38:    # CHIMERAX
./src/visualization/pose_manager.py:41:    def _load_chimerax_path(self):
./src/visualization/pose_manager.py:56:        chimerax = config.get(
./src/visualization/pose_manager.py:60:            "chimerax",
./src/visualization/pose_manager.py:64:        if chimerax.get("status") != "READY":
./src/visualization/pose_manager.py:66:                "ChimeraX n'est pas disponible."
./src/visualization/pose_manager.py:69:        path = chimerax.get("path")
./src/visualization/pose_manager.py:73:                "Chemin ChimeraX absent."
./src/visualization/pose_manager.py:78:                f"ChimeraX introuvable : {path}"
./src/visualization/pose_manager.py:336:            self.chimerax_path,
./src/visualization/pose_manager.py:467:            "[OK] ChimeraX lancé."
./src/visualization/interaction_visualizer.py:47:        - prépare les sélections ChimeraX ;
./src/visualization/interaction_visualizer.py:57:        self.chimerax_path = self._load_chimerax_path()
./src/visualization/interaction_visualizer.py:61:    # CHIMERAX
./src/visualization/interaction_visualizer.py:64:    def _load_chimerax_path(self):
./src/visualization/interaction_visualizer.py:74:        chimerax = config.get("tools", {}).get("chimerax", {})
./src/visualization/interaction_visualizer.py:76:        if chimerax.get("status") != "READY":
./src/visualization/interaction_visualizer.py:78:                "ChimeraX n'est pas disponible."
./src/visualization/interaction_visualizer.py:81:        path = chimerax.get("path")
./src/visualization/interaction_visualizer.py:85:                "Chemin ChimeraX absent de environment.json."
./src/visualization/interaction_visualizer.py:90:                f"ChimeraX introuvable : {path}"
./src/visualization/interaction_visualizer.py:189:    # CONSTRUCTION DES COMMANDES CHIMERAX
./src/visualization/interaction_visualizer.py:192:    def build_chimerax_commands(self):
./src/visualization/interaction_visualizer.py:235:    # LANCEMENT CHIMERAX
./src/visualization/interaction_visualizer.py:240:        commands = self.build_chimerax_commands()
./src/visualization/interaction_visualizer.py:243:            self.chimerax_path,
./src/visualization/interaction_visualizer.py:370:            print("[OK] ChimeraX lancé.")
./src/visualization/interaction_visualizer.py:386:                    "[ATTENTION] ChimeraX s'est fermé rapidement."
./src/visualization/interaction_3d.py:10:CHIMERAX = "/usr/lib/ucsf-chimerax/bin/ChimeraX"
./src/visualization/interaction_3d.py:287:def launch_chimerax(commands):
./src/visualization/interaction_3d.py:293:            CHIMERAX,
./src/visualization/interaction_3d.py:408:        f"[OK] {len(commands)} commandes ChimeraX préparées."
./src/visualization/interaction_3d.py:421:        process = launch_chimerax(
./src/visualization/interaction_3d.py:426:            f"[OK] ChimeraX lancé."
./README.md:59:UCSF ChimeraX est détecté comme dépendance externe par le logiciel, mais son intégration (visualisation 3D des poses) est fournie sous forme de scripts autonomes, non encore branchés à l'interface graphique actuelle. L'espace **Visualisation** de l'application s'appuie exclusivement sur le pipeline PLIP + diagrammes d'interaction 2D.
--- Fin de la recherche (rien au-dessus = aucune reference restante) ---

======================================================================
2) Tags git existants (versions reperees dans l'historique)
======================================================================
v1.0.1
v1.1.0
v1.0.0

======================================================================
3) Derniers 40 commits (pour reperer ce qui a change recemment)
======================================================================
ad9c83d Fix: credit_du_logiciel etait exclu par erreur du .gitignore
da2c51b Fix build Windows: reference_data deplace sous src/ (chemin racine casse depuis le refactor)
5c50317 Retire un fichier au nom invalide sous Windows (contenait ':'), bloquait le checkout CI
533d428 Ajout Credits (dock vertical, lien depuis A propos, coupure video), fix multi-recepteurs (visualisation), packaging .deb/tar.gz + build Windows a jour (i18n, credit_du_logiciel)
13aec0a trigger build
aca6e0e Add missing viewer_template module
1d83c26 trigger build
3c5586c Add missing pocket_detector module
160cf32 Add missing receptor_profile module
bc1e576 Sync GUI and docking engine updates to main
f456afb Add image_theme and receptor_profiles assets for Windows build
f1b5d4f fix: add image_theme and receptor_profiles to Windows build
bc005b9 Installeur sans droits admin (installation dans le dossier utilisateur)
744f3b8 Ajout installeur Windows via Inno Setup (CI)
4252c8e Embarquer la police DejaVuSans dans le build Windows CI
e343068 Fix police embarquee (DejaVuSans) et zones de texte extensibles avec defilement
7dcb79e Fix build Windows: contourne l'absence du format inchikey dans openbabel-wheel (metadonnee non critique pour PLIP)
3b2ceef Ajout diagnostic emplacement plugin inchi Open Babel
713937a Fix build Windows: positionne BABEL_DATADIR avant l'import Python de pybel (bindings openbabel embarques completement)
d0a7603 Fix build Windows: transmet BABEL_DATADIR au worker PLIP interne (evite l'echec de parsing des formats pybel)
ccada6c Fix build Windows: execute PLIP via worker interne (evite la dependance a une commande externe introuvable)
c7478f1 Fix build Windows: verification/installation silencieuse du Visual C++ Redistributable au demarrage
b47d1d4 Fix build Windows: embarque obabel.exe + DLLs + donnees, resolution dynamique du chemin (Vina + Open Babel)
8cb1c27 Ajout diagnostic emplacement obabel.exe pour build Windows
ad07ab1 Fix build Windows: correction du nom de fichier vina_1.2.5_win.exe (URL precedente en 404)
cd919bd Diagnostic build Windows: verification stricte du telechargement et de l'execution de vina.exe
a0591cd Merge branch 'main' of https://github.com/divin-stoni/VinaStudio
6c93a6b Fix Windows: résolution automatique de vina.exe embarqué (PyInstaller)
dcbeaa9 Fix build Windows: embarque receptor, reference_data et vina.exe
919c393 Update README.md
c67c16c Update README.md
8b3a36f Create README.md
12b4bee Fix versions requirements Windows (bornes minimales)
0154c5c Fix build Windows: numpy corrige, openbabel-wheel, arret sur erreur
dd32739 Fix build Windows: numpy corrige, openbabel-wheel, arret sur erreur
233aa6c Ajout workflow build Windows
33fc754 Version stable VINA Studio - avant packaging Windows

======================================================================
4) Fichiers sources modifies depuis le dernier tag (si un tag existe)
======================================================================
Dernier tag : v1.0.1
 docking/bin/vina                                   |  Bin 0 -> 572112 bytes
 docking/receptor/AcrB/1T9X.pdbqt                   | 9317 +++++++++++++++++++
 docking/receptor/AcrR/2QOP.pdbqt                   | 2034 +++++
 docking/receptor/AdeB/7KGG.pdbqt                   | 9405 +++++++++++++++++++
 docking/receptor/CmeB/8GJK.pdbqt                   | 9647 ++++++++++++++++++++
 docking/receptor/CmeR/3QPS.pdbqt                   | 2019 ++++
 docking/receptor/CmeR/3QQA.pdbqt                   | 1999 ++++
 docking/receptor/MexY/9E9F.pdbqt                   | 9476 +++++++++++++++++++
 src/a.zip                                          |  Bin 0 -> 1733976 bytes
 src/analysis/pocket_detector.py                    |  195 +
 src/analysis/statistics_pipeline.py                |   66 +-
 src/assets/fonts/DejaVuSans-Bold.ttf               |  Bin 0 -> 704128 bytes
 src/assets/fonts/DejaVuSans.ttf                    |  Bin 0 -> 756072 bytes
 src/campaign_table.py                              |  503 +
 src/crash_trace.txt                                |  855 ++
 src/diag18_segfault.sh                             |   87 +
 src/diag_3d_crash_20260920_162311.log              |  161 +
 src/diag_3d_freeze_20260920_163847.log             |   65 +
 src/diag_dark_zones.py                             |  117 +
 src/diag_dark_zones_20260920_165035.log            |  818 ++
 src/diag_segfault2_20260920_161443.log             |  316 +
 src/diag_segfault3_20260920_161558.log             |  260 +
 src/diag_segfault_20260920_161301.log              |  178 +
 src/diagnose_docking_ui.py                         |  412 +
 src/diagnose_generic_docking.py                    |  288 +
 src/diagnose_generic_docking_2.py                  |  208 +
 src/diagnostic_analyse.py                          |  419 +
 src/diagnostic_analyse.txt                         | 1078 +++
 src/docking/__init__.py                            |    6 +
 src/docking/config_manager.py                      |   77 +-
 src/docking/receptor_manager.py                    |  101 +
 src/docking/receptor_profile.py                    |  611 ++
 src/docking/receptor_viewer_pdb_prep.py            |  205 +
 .../batch_vina_engine/acrb_site2_ecoli/config.txt  |   16 +
 .../acrb_site2_ecoli/docking_results.csv           |    2 +
 .../acrb_site2_ecoli/logs/aspirin_test.log         |   33 +
 src/docking/sdf_preparer.py                        |   72 +-
 src/docking/vina_engine.py                         |  255 +-
 src/docking/vina_worker.py                         |  332 +-
 src/fix_receptor_pdbqt.py                          |  425 +
 src/gui/credits_page.py                            | 1240 +++
 src/gui/files.zip                                  |  Bin 0 -> 81244 bytes
 src/gui/main.zip                                   |  Bin 0 -> 288994 bytes
 src/gui/main_window.py                             | 7006 ++++++++++++--
 src/gui/main_window.zip                            |  Bin 0 -> 73330 bytes
 src/gui/patch_phyto_table_ux.py                    |  381 +
 .../phyto_page.before_table_ux_20260921_225031.py  | 1063 +++
 src/gui/phyto_page.py                              | 1157 +++
 src/gui/theme_manager.py                           |  490 +
 src/gui/viewer_template.py                         |  383 +
 src/gui/visualization_bridge.py                    |  122 +-
 src/main.py                                        |   65 +-
 src/patch_dark_zones.py                            |  285 +
 src/patch_fix_lang_mgr_visualization_page.py       |  130 -
 src/patch_glass_no_app_filter.py                   |  180 +
 src/patch_i18n_analysis_page.py                    |  528 --
 src/patch_i18n_and_imports.py                      |  381 -
 src/patch_i18n_docking_launch_tab.py               |  388 -
 src/patch_i18n_docking_pdbqt_tab.py                |  277 -
 src/patch_i18n_docking_sdf_tab.py                  |  383 -
 src/patch_i18n_extend_navigation.py                |  374 -
 src/patch_i18n_visualization_subtabs.py            |  409 -
 src/patch_interaction3d.py                         |  179 +
 src/patch_poller_and_watch.sh                      |   70 +
 src/patch_theme_blur.py                            | 1820 ++++
 src/phyto_api.py                                   |  791 ++
 src/plip_2d_diagram.py                             |    9 +-
 src/plotting.py                                    |   27 +-
 src/reference_data/scores_fusionnes.csv            |    5 +
 src/reference_data/scores_fusionnes_global.csv     |    5 +
 src/sauvegarde_projet.sh                           |   72 +
 src/scientific_fusion.py                           |  144 +-
 src/statistics_pipeline.py                         |   51 +-
 src/stats_engine.py                                |  103 +-
 src/tools/obabel_locator.py                        |   22 +-
 src/tools/runtime_env.py                           |   55 +
 src/tools/vcredist_check.py                        |    5 +-
 src/translations.py                                |   20 +
 src/vinastudio_icon.ico                            |  Bin 0 -> 7768 bytes
 src/visualization/chimerax_manager.py              |  418 -
 src/visualization/plip_runner.py                   |  132 +-
 81 files changed, 66857 insertions(+), 4371 deletions(-)

======================================================================
5) Liste des modules Python actuels par domaine (etat reel du code)
======================================================================
--- src/analysis/ ---
__init__.py
analysis_controller.py
comparative_analysis.py
hit_selector.py
integrated_hit_report.py
interaction_analyzer.py
interaction_summary.py
pocket_detector.py
pose_convergence.py
pose_validator.py
statistics_pipeline.py
structural_validator.py

--- src/docking/ ---
__init__.py
config_manager.py
docking_results.py
fusion_results.py
ligand_manager.py
receptor_manager.py
receptor_profile.py
receptor_viewer_pdb_prep.py
sdf_preparer.py
vina_engine.py
vina_worker.py

--- src/visualization/ ---
__init__.py
interaction_3d.py
interaction_visualizer.py
plip_runner.py
pose_manager.py
visualization_manager.py

--- src/gui/ (fichiers .py uniquement, pas les .bak) ---
__init__.py
credits_page.py
main_window.py
patch_phyto_table_ux.py
phyto_page.before_table_ux_20260921_225031.py
phyto_page.py
theme_manager.py
viewer_template.py
visualization_bridge.py

======================================================================
6) Profils recepteurs actuellement definis (fonctionnalite multi-cible)
======================================================================
2v50_clean_acd.json
2v50_clean_b.json
2v50_clean_b_2.json
2v50_clean_b_3.json
7o9w_clean_a.json
7o9w_clean_b.json
acrb_site2_ecoli.json
acrr_e67_ecoli.json
adeb_ethidium_abaumannii.json
cmeb_ampicillin_cjejuni.json
cmer_cholate_cjejuni.json
cmer_taurocholate_cjejuni.json
mexb_paeruginosa.json
mexr_paeruginosa.json
mexy_entrance_paeruginosa.json

======================================================================
FIN DU DIAGNOSTIC
======================================================================
