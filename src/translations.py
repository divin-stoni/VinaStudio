"""
translations.py
Dictionnaire de traduction pour l'interface de MexAB-OprM Analyzer.

Langues couvertes (5 langues majeures de la publication scientifique) :
  fr = français, en = anglais, de = allemand, zh = chinois, ja = japonais

Les termes techniques standards (dG, LogP, MW, R2, SI, CSV, bootstrap,
leave-one-out) sont conserves tels quels dans toutes les langues, comme
c'est l'usage dans la litterature scientifique internationale.
"""

SUPPORTED_LANGUAGES = ["en", "fr", "de", "zh", "ja"]

LANGUAGE_NAMES = {
    "en": "English",
    "fr": "Français",
    "de": "Deutsch",
    "zh": "中文",
    "ja": "日本語",
}

TR = {
    "window_title": {
        "fr": "MexAB-OprM Analyzer — Analyse statistique ΔG(MexB)/ΔG(MexR)",
        "en": "MexAB-OprM Analyzer — Statistical Analysis ΔG(MexB)/ΔG(MexR)",
        "de": "MexAB-OprM Analyzer — Statistische Analyse ΔG(MexB)/ΔG(MexR)",
        "zh": "MexAB-OprM 分析器 — ΔG(MexB)/ΔG(MexR) 统计分析",
        "ja": "MexAB-OprM アナライザー — ΔG(MexB)/ΔG(MexR) 統計解析",
    },
    "group_mode": {
        "fr": "Mode d'analyse", "en": "Analysis mode",
        "de": "Analysemodus", "zh": "分析模式", "ja": "解析モード",
    },
    "mode1_item": {
        "fr": "Mode 1 — Reproduction complète (ΔG MexB + ΔG MexR réels)",
        "en": "Mode 1 — Full reproduction (real ΔG MexB + ΔG MexR)",
        "de": "Modus 1 — Vollständige Reproduktion (reale ΔG MexB + ΔG MexR)",
        "zh": "模式 1 — 完整重现（真实 ΔG MexB + ΔG MexR）",
        "ja": "モード1 — 完全再現（実測 ΔG MexB + ΔG MexR）",
    },
    "mode2_item": {
        "fr": "Mode 2 — Prédictif (ΔG MexB seul → ΔG MexR prédit)",
        "en": "Mode 2 — Predictive (ΔG MexB only → ΔG MexR predicted)",
        "de": "Modus 2 — Prädiktiv (nur ΔG MexB → ΔG MexR vorhergesagt)",
        "zh": "模式 2 — 预测型（仅 ΔG MexB → 预测 ΔG MexR）",
        "ja": "モード2 — 予測型（ΔG MexBのみ → ΔG MexRを予測）",
    },
    "group_data": {
        "fr": "Données", "en": "Data", "de": "Daten", "zh": "数据", "ja": "データ",
    },
    "btn_load_ref": {
        "fr": "Charger le jeu de référence (139 composés)",
        "en": "Load reference dataset (139 compounds)",
        "de": "Referenzdatensatz laden (139 Verbindungen)",
        "zh": "加载参考数据集（139 个化合物）",
        "ja": "参照データセットを読み込む（139化合物）",
    },
    "ref_status_none": {
        "fr": "Référence : non chargée", "en": "Reference: not loaded",
        "de": "Referenz: nicht geladen", "zh": "参考数据：未加载", "ja": "参照データ：未読み込み",
    },
    "ref_status_loaded": {
        "fr": "Référence : {name} ({n} lignes)",
        "en": "Reference: {name} ({n} rows)",
        "de": "Referenz: {name} ({n} Zeilen)",
        "zh": "参考数据：{name}（{n} 行）",
        "ja": "参照データ：{name}（{n}行）",
    },
    "btn_load_new_mode1": {
        "fr": "Charger le fichier de données (molécule[, groupe], ΔG MexB, ΔG MexR)",
        "en": "Load data file (molecule[, group], ΔG MexB, ΔG MexR)",
        "de": "Datendatei laden (Molekül[, Gruppe], ΔG MexB, ΔG MexR)",
        "zh": "加载数据文件（分子[, 组], ΔG MexB, ΔG MexR）",
        "ja": "データファイルを読み込む（分子[, グループ], ΔG MexB, ΔG MexR）",
    },
    "btn_load_new_mode2": {
        "fr": "Charger le fichier à prédire (molécule, ΔG MexB[, groupe])",
        "en": "Load file to predict (molecule, ΔG MexB[, group])",
        "de": "Zu vorhersagende Datei laden (Molekül, ΔG MexB[, Gruppe])",
        "zh": "加载待预测文件（分子, ΔG MexB[, 组]）",
        "ja": "予測対象ファイルを読み込む（分子, ΔG MexB[, グループ]）",
    },
    "new_status_none": {
        "fr": "Fichier à analyser : non chargé", "en": "File to analyze: not loaded",
        "de": "Zu analysierende Datei: nicht geladen", "zh": "待分析文件：未加载",
        "ja": "解析対象ファイル：未読み込み",
    },
    "btn_scan_folder": {
        "fr": "Scanner un dossier…", "en": "Scan a folder…",
        "de": "Ordner durchsuchen…", "zh": "扫描文件夹…", "ja": "フォルダをスキャン…",
    },
    "log_mode1_no_groupe": {
        "fr": "Colonne 'groupe' absente : toutes les molécules regroupées sous 'SANS_GROUPE'. "
              "Les statistiques par groupe (corrélations, bootstrap) perdent leur sens avec un seul groupe.",
        "en": "'groupe' column missing: all molecules grouped under 'SANS_GROUPE'. "
              "Group-level statistics (correlations, bootstrap) are not meaningful with a single group.",
        "de": "Spalte 'groupe' fehlt: Alle Moleküle werden unter 'SANS_GROUPE' zusammengefasst. "
              "Gruppenbezogene Statistiken (Korrelationen, Bootstrap) sind mit nur einer Gruppe nicht aussagekräftig.",
        "zh": "缺少 'groupe' 列：所有分子都归入 'SANS_GROUPE'。"
              "仅有一个组时，按组统计（相关性、bootstrap）将失去意义。",
        "ja": "'groupe' 列がありません：すべての分子は 'SANS_GROUPE' としてまとめられます。"
              "グループが1つだけの場合、グループ別統計（相関、ブートストラップ）は意味を持ちません。",
    },
    "dlg_scan_title": {
        "fr": "Choisir un dossier à scanner", "en": "Choose a folder to scan",
        "de": "Zu durchsuchenden Ordner wählen", "zh": "选择要扫描的文件夹", "ja": "スキャンするフォルダを選択",
    },
    "msg_scan_no_csv": {
        "fr": "Aucun fichier CSV trouvé dans ce dossier (recherche récursive).",
        "en": "No CSV file found in this folder (recursive search).",
        "de": "Keine CSV-Datei in diesem Ordner gefunden (rekursive Suche).",
        "zh": "在此文件夹中未找到 CSV 文件（递归搜索）。",
        "ja": "このフォルダにCSVファイルが見つかりません（再帰検索）。",
    },
    "scan_dialog_title": {
        "fr": "Résultats du scan", "en": "Scan results",
        "de": "Scan-Ergebnisse", "zh": "扫描结果", "ja": "スキャン結果",
    },
    "scan_col_file": {"fr": "Fichier", "en": "File", "de": "Datei", "zh": "文件", "ja": "ファイル"},
    "scan_col_modes": {
        "fr": "Mode(s) compatible(s)", "en": "Compatible mode(s)",
        "de": "Kompatible(r) Modus(-i)", "zh": "兼容模式", "ja": "対応モード",
    },
    "scan_col_rows": {"fr": "Lignes", "en": "Rows", "de": "Zeilen", "zh": "行数", "ja": "行数"},
    "scan_btn_use": {
        "fr": "Utiliser ce fichier", "en": "Use this file",
        "de": "Diese Datei verwenden", "zh": "使用此文件", "ja": "このファイルを使用",
    },
    "scan_btn_close": {"fr": "Fermer", "en": "Close", "de": "Schließen", "zh": "关闭", "ja": "閉じる"},
    "scan_status_none": {
        "fr": "Non exploitable", "en": "Not usable",
        "de": "Nicht verwendbar", "zh": "不可用", "ja": "使用不可",
    },
    "scan_status_unreadable": {
        "fr": "Illisible", "en": "Unreadable",
        "de": "Nicht lesbar", "zh": "无法读取", "ja": "読み取り不可",
    },
    "scan_summary": {
        "fr": "{total} fichier(s) CSV trouvé(s) — {mode1} Mode 1, {mode2} Mode 2, {none} non exploitable(s), {err} illisible(s)",
        "en": "{total} CSV file(s) found — {mode1} Mode 1, {mode2} Mode 2, {none} not usable, {err} unreadable",
        "de": "{total} CSV-Datei(en) gefunden — {mode1} Modus 1, {mode2} Modus 2, {none} nicht verwendbar, {err} nicht lesbar",
        "zh": "找到 {total} 个 CSV 文件 — {mode1} 个模式1，{mode2} 个模式2，{none} 个不可用，{err} 个无法读取",
        "ja": "{total} 件のCSVファイルが見つかりました — モード1: {mode1}件、モード2: {mode2}件、使用不可: {none}件、読み取り不可: {err}件",
    },
    "new_status_loaded": {
        "fr": "Fichier : {name} ({n} lignes)",
        "en": "File: {name} ({n} rows)",
        "de": "Datei: {name} ({n} Zeilen)",
        "zh": "文件：{name}（{n} 行）",
        "ja": "ファイル：{name}（{n}行）",
    },
    "group_params": {
        "fr": "Paramètres", "en": "Parameters", "de": "Parameter", "zh": "参数", "ja": "パラメータ",
    },
    "label_seuil": {
        "fr": "Seuil de risque absolu\n(ΔG MexR, pyocyanine)",
        "en": "Absolute risk threshold\n(ΔG MexR, pyocyanin)",
        "de": "Absoluter Risikoschwellenwert\n(ΔG MexR, Pyocyanin)",
        "zh": "绝对风险阈值\n(ΔG MexR, 绿脓菌素)",
        "ja": "絶対リスク閾値\n(ΔG MexR、ピオシアニン)",
    },
    "label_percentile": {
        "fr": "Seuil percentile SI relatif\n(filtre à double critère)",
        "en": "Relative SI percentile threshold\n(dual filter)",
        "de": "Relativer SI-Perzentil-Schwellenwert\n(Doppelfilter)",
        "zh": "相对 SI 百分位阈值\n(双重筛选)",
        "ja": "相対SIパーセンタイル閾値\n(二重フィルタ)",
    },
    "label_nboot": {
        "fr": "Itérations bootstrap", "en": "Bootstrap iterations",
        "de": "Bootstrap-Iterationen", "zh": "Bootstrap 迭代次数", "ja": "ブートストラップ反復回数",
    },
    "btn_run": {
        "fr": "▶  Lancer l'analyse", "en": "▶  Run analysis",
        "de": "▶  Analyse starten", "zh": "▶  开始分析", "ja": "▶  解析を実行",
    },
    "btn_export": {
        "fr": "Exporter les résultats (Excel + graphiques)",
        "en": "Export results (Excel + charts)",
        "de": "Ergebnisse exportieren (Excel + Grafiken)",
        "zh": "导出结果（Excel + 图表）",
        "ja": "結果をエクスポート（Excel + グラフ）",
    },
    "log_placeholder": {
        "fr": "Journal d'exécution…", "en": "Execution log…",
        "de": "Ausführungsprotokoll…", "zh": "运行日志…", "ja": "実行ログ…",
    },
    "btn_lang": {
        "fr": "Français", "en": "English", "de": "Deutsch", "zh": "中文", "ja": "日本語",
    },
    "btn_help": {"fr": "Aide", "en": "Help", "de": "Hilfe", "zh": "帮助", "ja": "ヘルプ"},

    "log_ref_autoload": {
        "fr": "Jeu de référence chargé automatiquement : {path}",
        "en": "Reference dataset auto-loaded: {path}",
        "de": "Referenzdatensatz automatisch geladen: {path}",
        "zh": "参考数据集已自动加载：{path}",
        "ja": "参照データセットを自動読み込みしました：{path}",
    },
    "log_ref_loaded": {
        "fr": "Référence chargée : {path}", "en": "Reference loaded: {path}",
        "de": "Referenz geladen: {path}", "zh": "参考数据已加载：{path}",
        "ja": "参照データを読み込みました：{path}",
    },
    "log_new_loaded": {
        "fr": "Fichier chargé : {path} — colonnes : {cols}",
        "en": "File loaded: {path} — columns: {cols}",
        "de": "Datei geladen: {path} — Spalten: {cols}",
        "zh": "文件已加载：{path} — 列：{cols}",
        "ja": "ファイルを読み込みました：{path} — 列：{cols}",
    },
    "log_mode1_start": {
        "fr": "Mode 1 — analyse sur {n} composés (hors références/contrôles).",
        "en": "Mode 1 — analysis on {n} compounds (excluding references/controls).",
        "de": "Modus 1 — Analyse von {n} Verbindungen (ohne Referenzen/Kontrollen).",
        "zh": "模式 1 — 对 {n} 个化合物进行分析（不含参照/对照）。",
        "ja": "モード1 — {n}化合物を解析（参照・対照を除く）。",
    },
    "log_bootstrap_seed": {
        "fr": "Bootstrap : graine aléatoire fixe = {seed} (résultats reproductibles).",
        "en": "Bootstrap: fixed random seed = {seed} (reproducible results).",
        "de": "Bootstrap: fester Zufallswert (Seed) = {seed} (reproduzierbare Ergebnisse).",
        "zh": "Bootstrap：固定随机种子 = {seed}（结果可重复）。",
        "ja": "ブートストラップ：固定乱数シード = {seed}（再現可能な結果）。",
    },
    "log_mode1_multi_ok": {
        "fr": "Régression multiple calculée (MW, LogP disponibles).",
        "en": "Multiple regression computed (MW, LogP available).",
        "de": "Multiple Regression berechnet (MW, LogP verfügbar).",
        "zh": "已计算多元回归（MW、LogP 可用）。",
        "ja": "重回帰分析を計算しました（MW、LogPが利用可能）。",
    },
    "log_mode1_multi_skip": {
        "fr": "MW / LogP absents → régression multiple et corrélation partielle ignorées.",
        "en": "MW / LogP missing → multiple regression and partial correlation skipped.",
        "de": "MW / LogP fehlen → multiple Regression und partielle Korrelation übersprungen.",
        "zh": "缺少 MW / LogP → 跳过多元回归和偏相关分析。",
        "ja": "MW / LogPがありません → 重回帰分析と偏相関はスキップされました。",
    },
    "log_mode1_done": {
        "fr": "Analyse Mode 1 terminée.", "en": "Mode 1 analysis completed.",
        "de": "Analyse Modus 1 abgeschlossen.", "zh": "模式 1 分析完成。", "ja": "モード1の解析が完了しました。",
    },
    "log_mode2_multi_ok": {
        "fr": "Prédiction avec MW et LogP en covariables.",
        "en": "Prediction using MW and LogP as covariates.",
        "de": "Vorhersage mit MW und LogP als Kovariaten.",
        "zh": "使用 MW 和 LogP 作为协变量进行预测。",
        "ja": "MWとLogPを共変量として予測。",
    },
    "log_mode2_multi_skip": {
        "fr": "Prédiction sur ΔG(MexB) seul (MW/LogP absents d'un des deux fichiers).",
        "en": "Prediction on ΔG(MexB) only (MW/LogP missing from one of the files).",
        "de": "Vorhersage nur anhand von ΔG(MexB) (MW/LogP fehlen in einer der beiden Dateien).",
        "zh": "仅基于 ΔG(MexB) 进行预测（两个文件中有一个缺少 MW/LogP）。",
        "ja": "ΔG(MexB)のみによる予測（いずれかのファイルにMW/LogPがありません）。",
    },
    "log_mode2_model": {
        "fr": "Modèle calibré sur {n} composés de référence : R² = {r2}",
        "en": "Model calibrated on {n} reference compounds: R² = {r2}",
        "de": "Modell kalibriert an {n} Referenzverbindungen: R² = {r2}",
        "zh": "模型基于 {n} 个参考化合物校准：R² = {r2}",
        "ja": "{n}個の参照化合物でモデルを較正：R² = {r2}",
    },
    "log_mode2_done": {
        "fr": "Analyse Mode 2 (prédictive) terminée.", "en": "Mode 2 (predictive) analysis completed.",
        "de": "Analyse Modus 2 (prädiktiv) abgeschlossen.", "zh": "模式 2（预测型）分析完成。",
        "ja": "モード2（予測型）の解析が完了しました。",
    },
    "log_export_done": {
        "fr": "Export terminé → {dir}", "en": "Export completed → {dir}",
        "de": "Export abgeschlossen → {dir}", "zh": "导出完成 → {dir}", "ja": "エクスポート完了 → {dir}",
    },

    "err_ref_default_fail": {
        "fr": "Impossible de charger la référence par défaut : {e}",
        "en": "Unable to load default reference: {e}",
        "de": "Standardreferenz konnte nicht geladen werden: {e}",
        "zh": "无法加载默认参考数据：{e}",
        "ja": "デフォルトの参照データを読み込めません：{e}",
    },
    "err_dialog_title": {"fr": "Erreur", "en": "Error", "de": "Fehler", "zh": "错误", "ja": "エラー"},
    "err_analysis_title": {
        "fr": "Erreur pendant l'analyse", "en": "Error during analysis",
        "de": "Fehler während der Analyse", "zh": "分析过程中出错", "ja": "解析中にエラーが発生しました",
    },
    "err_export_title": {
        "fr": "Erreur export", "en": "Export error",
        "de": "Exportfehler", "zh": "导出错误", "ja": "エクスポートエラー",
    },
    "err_need_data_mode1": {
        "fr": "Charge d'abord un fichier de données (molécule[, groupe], ΔG MexB, ΔG MexR).",
        "en": "First load a data file (molecule[, group], ΔG MexB, ΔG MexR).",
        "de": "Lade zuerst eine Datendatei (Molekül[, Gruppe], ΔG MexB, ΔG MexR).",
        "zh": "请先加载数据文件（分子[, 组], ΔG MexB, ΔG MexR）。",
        "ja": "まずデータファイルを読み込んでください（分子[, グループ], ΔG MexB, ΔG MexR）。",
    },
    "err_missing_cols": {
        "fr": "Colonnes attendues manquantes : {needed}. Colonnes trouvées : {found}",
        "en": "Missing expected columns: {needed}. Columns found: {found}",
        "de": "Erwartete Spalten fehlen: {needed}. Gefundene Spalten: {found}",
        "zh": "缺少所需列：{needed}。找到的列：{found}",
        "ja": "必要な列が不足しています：{needed}。検出された列：{found}",
    },
    "err_need_ref_mode2": {
        "fr": "Charge d'abord le jeu de référence (139 composés) pour calibrer le modèle.",
        "en": "First load the reference dataset (139 compounds) to calibrate the model.",
        "de": "Lade zuerst den Referenzdatensatz (139 Verbindungen), um das Modell zu kalibrieren.",
        "zh": "请先加载参考数据集（139 个化合物）以校准模型。",
        "ja": "モデルを較正するには、まず参照データセット（139化合物）を読み込んでください。",
    },
    "err_need_new_mode2": {
        "fr": "Charge le fichier à prédire (molécule, ΔG MexB).",
        "en": "Load the file to predict (molecule, ΔG MexB).",
        "de": "Lade die zu vorhersagende Datei (Molekül, ΔG MexB).",
        "zh": "请加载待预测文件（分子, ΔG MexB）。",
        "ja": "予測対象ファイルを読み込んでください（分子, ΔG MexB）。",
    },
    "err_ref_missing_cols": {
        "fr": "Le jeu de référence doit contenir 'dg_mexb' et 'dg_mexr'.",
        "en": "The reference dataset must contain 'dg_mexb' and 'dg_mexr'.",
        "de": "Der Referenzdatensatz muss 'dg_mexb' und 'dg_mexr' enthalten.",
        "zh": "参考数据集必须包含 'dg_mexb' 和 'dg_mexr'。",
        "ja": "参照データセットには 'dg_mexb' と 'dg_mexr' が必要です。",
    },
    "err_new_missing_dgmexb": {
        "fr": "Le fichier à prédire doit contenir la colonne 'dg_mexb'.",
        "en": "The file to predict must contain the 'dg_mexb' column.",
        "de": "Die zu vorhersagende Datei muss die Spalte 'dg_mexb' enthalten.",
        "zh": "待预测文件必须包含 'dg_mexb' 列。",
        "ja": "予測対象ファイルには 'dg_mexb' 列が必要です。",
    },
    "export_success_title": {
        "fr": "Export réussi", "en": "Export successful",
        "de": "Export erfolgreich", "zh": "导出成功", "ja": "エクスポート成功",
    },
    "export_success_msg": {
        "fr": "Résultats exportés dans :\n{xlsx}\net {figdir}",
        "en": "Results exported to:\n{xlsx}\nand {figdir}",
        "de": "Ergebnisse exportiert nach:\n{xlsx}\nund {figdir}",
        "zh": "结果已导出至：\n{xlsx}\n和 {figdir}",
        "ja": "結果のエクスポート先：\n{xlsx}\nおよび {figdir}",
    },

    "dlg_load_ref_title": {
        "fr": "Charger le jeu de référence", "en": "Load reference dataset",
        "de": "Referenzdatensatz laden", "zh": "加载参考数据集", "ja": "参照データセットを読み込む",
    },
    "dlg_load_csv_title": {
        "fr": "Charger un fichier CSV", "en": "Load a CSV file",
        "de": "CSV-Datei laden", "zh": "加载 CSV 文件", "ja": "CSVファイルを読み込む",
    },
    "dlg_export_dir_title": {
        "fr": "Choisir le dossier d'export", "en": "Choose export folder",
        "de": "Exportordner wählen", "zh": "选择导出文件夹", "ja": "エクスポート先フォルダを選択",
    },

    "tab_data": {"fr": "Données", "en": "Data", "de": "Daten", "zh": "数据", "ja": "データ"},
    "tab_corr": {
        "fr": "Corrélations par groupe / analyse globale", "en": "Correlations by group / global analysis",
        "de": "Korrelationen nach Gruppe / Gesamtanalyse", "zh": "按组相关性 / 整体分析",
        "ja": "グループ別相関 / 全体解析",
    },
    "tab_boot": {
        "fr": "Robustesse (Bootstrap CI)", "en": "Robustness (Bootstrap CI)",
        "de": "Robustheit (Bootstrap-KI)", "zh": "稳健性（Bootstrap 置信区间）", "ja": "頑健性（ブートストラップCI）",
    },
    "tab_loo": {
        "fr": "Leave-one-out", "en": "Leave-one-out",
        "de": "Leave-one-out", "zh": "Leave-one-out", "ja": "Leave-one-out",
    },
    "tab_multireg": {
        "fr": "Régression multiple", "en": "Multiple regression",
        "de": "Multiple Regression", "zh": "多元回归", "ja": "重回帰分析",
    },
    "tab_si_class": {
        "fr": "SI & Classification", "en": "SI & Classification",
        "de": "SI & Klassifikation", "zh": "SI 与分类", "ja": "SI & 分類",
    },
    "tab_top": {
        "fr": "Top candidats", "en": "Top candidates",
        "de": "Top-Kandidaten", "zh": "顶级候选", "ja": "トップ候補",
    },
    "tab_candidats_valides": {
        "fr": "Candidats validés (double critère)", "en": "Validated candidates (dual filter)",
        "de": "Validierte Kandidaten (Doppelfilter)", "zh": "已验证候选（双重筛选）",
        "ja": "検証済み候補（二重フィルタ）",
    },
    "tab_exclus_seuil_absolu": {
        "fr": "Bon indice relatif mais exclus (seuil absolu)",
        "en": "Good relative SI but excluded (absolute threshold)",
        "de": "Guter relativer SI, aber ausgeschlossen (absoluter Schwellenwert)",
        "zh": "相对指数良好但被排除（绝对阈值）",
        "ja": "相対SIは良好だが除外（絶対閾値）",
    },
    "tab_fig_corr": {
        "fr": "Graphique — Corrélation", "en": "Chart — Correlation",
        "de": "Grafik — Korrelation", "zh": "图表 — 相关性", "ja": "グラフ — 相関",
    },
    "tab_fig_hist_si": {
        "fr": "Graphique — Histogramme SI", "en": "Chart — SI Histogram",
        "de": "Grafik — SI-Histogramm", "zh": "图表 — SI 直方图", "ja": "グラフ — SIヒストグラム",
    },
    "tab_fig_hist_si_group": {
        "fr": "Graphique — SI par famille", "en": "Chart — SI by family",
        "de": "Grafik — SI nach Familie", "zh": "图表 — 按族分类的 SI", "ja": "グラフ — ファミリー別SI",
    },
    "tab_fig_forest": {
        "fr": "Graphique — Forest plot corrélations", "en": "Chart — Correlation forest plot",
        "de": "Grafik — Forest-Plot der Korrelationen", "zh": "图表 — 相关性森林图",
        "ja": "グラフ — 相関フォレストプロット",
    },
    "tab_fig_percentile": {
        "fr": "Graphique — Percentile / statut", "en": "Chart — Percentile / status",
        "de": "Grafik — Perzentil / Status", "zh": "图表 — 百分位 / 状态", "ja": "グラフ — パーセンタイル / ステータス",
    },
    "tab_fig_loo": {
        "fr": "Graphique — Influence (leave-one-out)", "en": "Chart — Influence (leave-one-out)",
        "de": "Grafik — Einfluss (Leave-one-out)", "zh": "图表 — 影响力（Leave-one-out）",
        "ja": "グラフ — 影響度（Leave-one-out）",
    },
    "tab_pred_data": {
        "fr": "Données + Prédiction", "en": "Data + Prediction",
        "de": "Daten + Vorhersage", "zh": "数据 + 预测", "ja": "データ + 予測",
    },
    "tab_pred_si_class": {
        "fr": "SI & Classification (prédite)", "en": "SI & Classification (predicted)",
        "de": "SI & Klassifikation (vorhergesagt)", "zh": "SI 与分类（预测）", "ja": "SI & 分類（予測）",
    },
    "tab_pred_top": {
        "fr": "Top candidats prédits", "en": "Predicted top candidates",
        "de": "Vorhergesagte Top-Kandidaten", "zh": "预测的顶级候选", "ja": "予測トップ候補",
    },
    "tab_pred_candidats_valides": {
        "fr": "Candidats validés prédits (double critère)", "en": "Predicted validated candidates (dual filter)",
        "de": "Vorhergesagte validierte Kandidaten (Doppelfilter)", "zh": "预测已验证候选（双重筛选）",
        "ja": "予測検証済み候補（二重フィルタ）",
    },
    "tab_pred_exclus_seuil_absolu": {
        "fr": "Bon indice relatif prédit mais exclus", "en": "Predicted good relative SI but excluded",
        "de": "Vorhergesagter guter relativer SI, aber ausgeschlossen", "zh": "预测相对指数良好但被排除",
        "ja": "予測相対SIは良好だが除外",
    },
    "tab_model_summary": {
        "fr": "Résumé du modèle", "en": "Model summary",
        "de": "Modellzusammenfassung", "zh": "模型摘要", "ja": "モデルの概要",
    },

    "tab_results_category": {
        "fr": "📊 Résultats", "en": "📊 Results",
        "de": "📊 Ergebnisse", "zh": "📊 结果", "ja": "📊 結果",
    },
    "tab_statistics_category": {
        "fr": "📈 Statistiques", "en": "📈 Statistics",
        "de": "📈 Statistik", "zh": "📈 统计", "ja": "📈 統計",
    },
    "tab_figures_category": {
        "fr": "📉 Graphiques", "en": "📉 Charts",
        "de": "📉 Grafiken", "zh": "📉 图表", "ja": "📉 グラフ",
    },
    "tab_fig_pred": {
        "fr": "Graphique — Prédiction", "en": "Chart — Prediction",
        "de": "Grafik — Vorhersage", "zh": "图表 — 预测", "ja": "グラフ — 予測",
    },
    "tab_fig_hist_si_pred": {
        "fr": "Graphique — Histogramme SI (prédit)", "en": "Chart — SI Histogram (predicted)",
        "de": "Grafik — SI-Histogramm (vorhergesagt)", "zh": "图表 — SI 直方图（预测）",
        "ja": "グラフ — SIヒストグラム（予測）",
    },
    "tab_fig_percentile_pred": {
        "fr": "Graphique — Percentile / statut (prédit)", "en": "Chart — Percentile / status (predicted)",
        "de": "Grafik — Perzentil / Status (vorhergesagt)", "zh": "图表 — 百分位 / 状态（预测）",
        "ja": "グラフ — パーセンタイル / ステータス（予測）",
    },

    "vina_window_title": {
        "fr": "VINA Studio — Docking moléculaire & Analyse",
        "en": "VINA Studio — Molecular Docking & Analysis",
        "de": "VINA Studio — Molekulares Docking & Analyse",
        "zh": "VINA Studio — 分子对接与分析",
        "ja": "VINA Studio — 分子ドッキング＆解析",
    },
    "vina_app_name": {
        "fr": "VINA Studio", "en": "VINA Studio", "de": "VINA Studio",
        "zh": "VINA Studio", "ja": "VINA Studio",
    },
    "vina_app_subtitle": {
        "fr": "Docking moléculaire & analyse des interactions",
        "en": "Molecular Docking & Interaction Analysis",
        "de": "Molekulares Docking & Interaktionsanalyse",
        "zh": "分子对接与相互作用分析",
        "ja": "分子ドッキング＆相互作用解析",
    },
    "nav_prepare_ligands": {
        "fr": "Préparer les ligands", "en": "Prepare ligands",
        "de": "Liganden vorbereiten", "zh": "准备配体", "ja": "リガンド準備",
    },
    "nav_run_docking": {
        "fr": "Lancer le docking", "en": "Run docking",
        "de": "Docking starten", "zh": "开始对接", "ja": "ドッキング実行",
    },
    "nav_analysis": {
        "fr": "Analyse", "en": "Analysis", "de": "Analyse", "zh": "分析", "ja": "解析",
    },
    "nav_visualization": {
        "fr": "Visualisation", "en": "Visualization",
        "de": "Visualisierung", "zh": "可视化", "ja": "可視化",
    },
    "status_ready": {
        "fr": "Prêt — aucun calcul en cours",
        "en": "Ready — no computation running",
        "de": "Bereit — keine Berechnung läuft",
        "zh": "就绪 — 当前无计算任务",
        "ja": "準備完了 — 実行中の計算はありません",
    },
    "status_loading_hits": {
        "fr": "Chargement des hits de docking…",
        "en": "Loading docking hits…",
        "de": "Docking-Treffer werden geladen…",
        "zh": "正在加载对接命中结果…",
        "ja": "ドッキングヒットを読み込み中…",
    },
    "status_no_errors": {
        "fr": "Aucune erreur.", "en": "No errors.",
        "de": "Keine Fehler.", "zh": "无错误。", "ja": "エラーなし。",
    },
    "side_espace_travail": {
        "fr": "ESPACE DE TRAVAIL", "en": "WORKSPACE",
        "de": "ARBEITSBEREICH", "zh": "工作区", "ja": "ワークスペース",
    },
    "side_docking": {
        "fr": "Docking", "en": "Docking", "de": "Docking",
        "zh": "对接", "ja": "ドッキング",
    },
    "side_analysis": {
        "fr": "Analyse", "en": "Analysis", "de": "Analyse",
        "zh": "分析", "ja": "解析",
    },
    "side_visualization": {
        "fr": "Visualisation", "en": "Visualization", "de": "Visualisierung",
        "zh": "可视化", "ja": "可視化",
    },
    "dock_tab_prepare_sdf": {
        "fr": "Préparer les SDF", "en": "Prepare SDF",
        "de": "SDF vorbereiten", "zh": "准备 SDF", "ja": "SDF準備",
    },
    "dock_tab_load_pdbqt": {
        "fr": "Charger les PDBQT", "en": "Load PDBQT",
        "de": "PDBQT laden", "zh": "加载 PDBQT", "ja": "PDBQT読み込み",
    },
    "dock_tab_run_docking": {
        "fr": "Lancer le docking", "en": "Run docking",
        "de": "Docking starten", "zh": "开始对接", "ja": "ドッキング実行",
    },
    "analysis_tab_results": {
        "fr": "Résultats", "en": "Results", "de": "Ergebnisse",
        "zh": "结果", "ja": "結果",
    },
    "analysis_tab_type": {
        "fr": "Type d'analyse", "en": "Analysis type",
        "de": "Analysetyp", "zh": "分析类型", "ja": "解析タイプ",
    },
    "analysis_tab_results_analytics": {
        "fr": "Résultats analytiques", "en": "Analytical results",
        "de": "Analytische Ergebnisse", "zh": "分析结果", "ja": "分析結果",
    },
    "viz_tab_residues": {
        "fr": "Résidus de référence", "en": "Reference residues",
        "de": "Referenzreste", "zh": "参考残基", "ja": "参照残基",
    },
    "viz_tab_plip": {
        "fr": "Calcul PLIP", "en": "PLIP calculation",
        "de": "PLIP-Berechnung", "zh": "PLIP 计算", "ja": "PLIP計算",
    },
    "viz_tab_interaction2d": {
        "fr": "Interaction 2D", "en": "Interaction 2D", "de": "Interaction 2D",
        "zh": "2D 相互作用", "ja": "2D相互作用",
    },
    "viz_btn_recompute": {
        "fr": "Recalculer tout", "en": "Recompute all",
        "de": "Alles neu berechnen", "zh": "全部重新计算", "ja": "すべて再計算",
    },
    "viz_btn_export_all": {
        "fr": "Exporter tout", "en": "Export all",
        "de": "Alles exportieren", "zh": "全部导出", "ja": "すべてエクスポート",
    },
    "menu_file": {
        "fr": "Fichier", "en": "File", "de": "Datei", "zh": "文件", "ja": "ファイル",
    },
    "menu_tools": {
        "fr": "Outils", "en": "Tools", "de": "Werkzeuge", "zh": "工具", "ja": "ツール",
    },
    "menu_help": {
        "fr": "Aide", "en": "Help", "de": "Hilfe", "zh": "帮助", "ja": "ヘルプ",
    },
    "sdf_section_title": {
        "fr": "Préparation des ligands", "en": "Ligand preparation",
        "de": "Ligandenvorbereitung", "zh": "配体制备", "ja": "リガンド調製",
    },
    "sdf_section_desc": {
        "fr": "Importez un ou plusieurs fichiers SDF, ou un dossier contenant des fichiers SDF, puis convertissez les molécules en fichiers PDBQT utilisables par AutoDock Vina.",
        "en": "Import one or more SDF files, or a folder containing SDF files, then convert the molecules into PDBQT files usable by AutoDock Vina.",
        "de": "Importieren Sie eine oder mehrere SDF-Dateien oder einen Ordner mit SDF-Dateien und konvertieren Sie die Moleküle anschließend in PDBQT-Dateien, die von AutoDock Vina verwendet werden können.",
        "zh": "导入一个或多个 SDF 文件，或包含 SDF 文件的文件夹，然后将分子转换为 AutoDock Vina 可用的 PDBQT 文件。",
        "ja": "1つ以上のSDFファイル、またはSDFファイルを含むフォルダをインポートし、分子をAutoDock Vinaで使用できるPDBQTファイルに変換します。",
    },
    "sdf_panel_title": {
        "fr": "Bibliothèque SDF", "en": "SDF library",
        "de": "SDF-Bibliothek", "zh": "SDF 库", "ja": "SDFライブラリ",
    },
    "sdf_btn_add_files": {
        "fr": "Ajouter des fichiers SDF", "en": "Add SDF files",
        "de": "SDF-Dateien hinzufügen", "zh": "添加 SDF 文件", "ja": "SDFファイルを追加",
    },
    "sdf_btn_add_folder": {
        "fr": "Ajouter un dossier", "en": "Add a folder",
        "de": "Ordner hinzufügen", "zh": "添加文件夹", "ja": "フォルダを追加",
    },
    "sdf_btn_clear_selection": {
        "fr": "Vider la sélection", "en": "Clear selection",
        "de": "Auswahl leeren", "zh": "清空选择", "ja": "選択をクリア",
    },
    "sdf_output_folder_label": {
        "fr": "Dossier de sortie", "en": "Output folder",
        "de": "Ausgabeordner", "zh": "输出文件夹", "ja": "出力フォルダ",
    },
    "sdf_btn_prepare_molecules": {
        "fr": "Préparer les molécules", "en": "Prepare molecules",
        "de": "Moleküle vorbereiten", "zh": "准备分子", "ja": "分子を準備",
    },
    "sdf_state_panel_title": {
        "fr": "État de préparation", "en": "Preparation status",
        "de": "Vorbereitungsstatus", "zh": "准备状态", "ja": "準備状況",
    },
    "pdbqt_section_title": {
        "fr": "Ligands PDBQT", "en": "PDBQT ligands", "de": "PDBQT-Liganden",
        "zh": "PDBQT 配体", "ja": "PDBQTリガンド",
    },
    "pdbqt_section_desc": {
        "fr": "Contrôlez les ligands disponibles avant leur utilisation dans la campagne de docking.",
        "en": "Review the available ligands before using them in the docking campaign.",
        "de": "Überprüfen Sie die verfügbaren Liganden, bevor Sie sie in der Docking-Kampagne verwenden.",
        "zh": "在对接活动中使用配体之前，请检查可用的配体。",
        "ja": "ドッキングキャンペーンで使用する前に、利用可能なリガンドを確認してください。",
    },
    "pdbqt_btn_add_files": {
        "fr": "Ajouter des fichiers", "en": "Add files",
        "de": "Dateien hinzufügen", "zh": "添加文件", "ja": "ファイルを追加",
    },
    "pdbqt_btn_refresh": {
        "fr": "Actualiser", "en": "Refresh", "de": "Aktualisieren",
        "zh": "刷新", "ja": "更新",
    },
    "pdbqt_btn_select_all": {
        "fr": "Tout sélectionner", "en": "Select all", "de": "Alles auswählen",
        "zh": "全选", "ja": "すべて選択",
    },
    "pdbqt_btn_clear_selection": {
        "fr": "Effacer sélection", "en": "Clear selection", "de": "Auswahl löschen",
        "zh": "清除选择", "ja": "選択を消去",
    },
    "pdbqt_btn_use_selection": {
        "fr": "Utiliser la sélection", "en": "Use selection", "de": "Auswahl verwenden",
        "zh": "使用所选", "ja": "選択を使用",
    },
    "pdbqt_col_index": {
        "fr": "#", "en": "#", "de": "#", "zh": "#", "ja": "#",
    },
    "pdbqt_col_molecule": {
        "fr": "Molécule", "en": "Molecule", "de": "Molekül", "zh": "分子", "ja": "分子",
    },
    "pdbqt_col_file": {
        "fr": "Fichier", "en": "File", "de": "Datei", "zh": "文件", "ja": "ファイル",
    },
    "pdbqt_col_status": {
        "fr": "Statut", "en": "Status", "de": "Status", "zh": "状态", "ja": "ステータス",
    },
    "dock_config_section_title": {
        "fr": "Configuration du docking", "en": "Docking configuration",
        "de": "Docking-Konfiguration", "zh": "对接配置", "ja": "ドッキング設定",
    },
    "dock_config_section_desc": {
        "fr": "Sélectionnez la cible et vérifiez les paramètres de calcul avant de lancer la campagne.",
        "en": "Select the target and check the calculation parameters before launching the campaign.",
        "de": "Wählen Sie das Ziel aus und überprüfen Sie die Berechnungsparameter, bevor Sie die Kampagne starten.",
        "zh": "在启动计算活动之前，请选择目标并检查计算参数。",
        "ja": "キャンペーンを開始する前に、ターゲットを選択し、計算パラメータを確認してください。",
    },
    "dock_target_panel_title": {
        "fr": "Cible biologique", "en": "Biological target",
        "de": "Biologisches Ziel", "zh": "生物靶标", "ja": "生物学的標的",
    },
    "dock_receptor_label": {
        "fr": "Récepteur", "en": "Receptor", "de": "Rezeptor",
        "zh": "受体", "ja": "レセプター",
    },
    "dock_gridbox_panel_title": {
        "fr": "Grid box", "en": "Grid box", "de": "Grid Box",
        "zh": "格点框 (Grid Box)", "ja": "グリッドボックス",
    },
    "grid_center_x": {
        "fr": "Centre X", "en": "Center X", "de": "Zentrum X",
        "zh": "中心 X", "ja": "中心X",
    },
    "grid_center_y": {
        "fr": "Centre Y", "en": "Center Y", "de": "Zentrum Y",
        "zh": "中心 Y", "ja": "中心Y",
    },
    "grid_center_z": {
        "fr": "Centre Z", "en": "Center Z", "de": "Zentrum Z",
        "zh": "中心 Z", "ja": "中心Z",
    },
    "grid_size_x": {
        "fr": "Taille X", "en": "Size X", "de": "Größe X",
        "zh": "尺寸 X", "ja": "サイズX",
    },
    "grid_size_y": {
        "fr": "Taille Y", "en": "Size Y", "de": "Größe Y",
        "zh": "尺寸 Y", "ja": "サイズY",
    },
    "grid_size_z": {
        "fr": "Taille Z", "en": "Size Z", "de": "Größe Z",
        "zh": "尺寸 Z", "ja": "サイズZ",
    },
    "dock_vina_params_panel_title": {
        "fr": "Paramètres Vina", "en": "Vina parameters",
        "de": "Vina-Parameter", "zh": "Vina 参数", "ja": "Vinaパラメータ",
    },
    "dock_num_modes_label": {
        "fr": "Nombre de modes", "en": "Number of modes",
        "de": "Anzahl der Modi", "zh": "模式数量", "ja": "モード数",
    },
    "dock_mexr_config_panel_title": {
        "fr": "Configuration MexR", "en": "MexR configuration",
        "de": "MexR-Konfiguration", "zh": "MexR 配置", "ja": "MexR設定",
    },
    "dock_execution_panel_title": {
        "fr": "Exécution", "en": "Execution", "de": "Ausführung",
        "zh": "执行", "ja": "実行",
    },
    "dock_btn_cancel": {
        "fr": "Annuler", "en": "Cancel", "de": "Abbrechen",
        "zh": "取消", "ja": "キャンセル",
    },
    "dock_execution_log_panel_title": {
        "fr": "Journal d'exécution", "en": "Execution log",
        "de": "Ausführungsprotokoll", "zh": "执行日志", "ja": "実行ログ",
    },
    "analysis_results_section_title": {
        "fr": "Résultats du docking", "en": "Docking results",
        "de": "Docking-Ergebnisse", "zh": "对接结果", "ja": "ドッキング結果",
    },
    "analysis_results_section_desc": {
        "fr": "Classement des molécules selon leur meilleure affinité de liaison.",
        "en": "Ranking of molecules by their best binding affinity.",
        "de": "Rangliste der Moleküle nach ihrer besten Bindungsaffinität.",
        "zh": "根据最佳结合亲和力对分子进行排名。",
        "ja": "最良の結合親和性による分子のランキング。",
    },
    "analysis_campaign_label": {
        "fr": "Campagne", "en": "Campaign", "de": "Kampagne",
        "zh": "活动", "ja": "キャンペーン",
    },
    "analysis_btn_run": {
        "fr": "Lancer l'analyse", "en": "Run analysis", "de": "Analyse starten",
        "zh": "运行分析", "ja": "分析を実行",
    },
    "analysis_col_rank": {
        "fr": "Rang", "en": "Rank", "de": "Rang", "zh": "排名", "ja": "順位",
    },
    "analysis_col_molecule": {
        "fr": "Molécule", "en": "Molecule", "de": "Molekül", "zh": "分子", "ja": "分子",
    },
    "analysis_col_group": {
        "fr": "Groupe", "en": "Group", "de": "Gruppe", "zh": "分组", "ja": "グループ",
    },
    "analysis_col_mexb": {
        "fr": "MexB (kcal/mol)", "en": "MexB (kcal/mol)", "de": "MexB (kcal/mol)",
        "zh": "MexB (kcal/mol)", "ja": "MexB (kcal/mol)",
    },
    "analysis_col_mexr": {
        "fr": "MexR (kcal/mol)", "en": "MexR (kcal/mol)", "de": "MexR (kcal/mol)",
        "zh": "MexR (kcal/mol)", "ja": "MexR (kcal/mol)",
    },
    "analysis_col_status": {
        "fr": "Statut", "en": "Status", "de": "Status", "zh": "状态", "ja": "ステータス",
    },
    "analysis_type_section_title": {
        "fr": "Analyse scientifique MexB / MexR", "en": "MexB / MexR scientific analysis",
        "de": "Wissenschaftliche Analyse MexB / MexR", "zh": "MexB / MexR 科学分析",
        "ja": "MexB / MexR 科学分析",
    },
    "analysis_type_section_desc": {
        "fr": "Chargez un fichier CSV scientifique produit par la fusion docking.",
        "en": "Load a scientific CSV file produced by the docking fusion.",
        "de": "Laden Sie eine wissenschaftliche CSV-Datei, die durch die Docking-Fusion erzeugt wurde.",
        "zh": "加载由对接融合生成的科学 CSV 文件。",
        "ja": "ドッキング統合によって生成された科学的CSVファイルを読み込みます。",
    },
    "analysis_internal_csv_label": {
        "fr": "CSV scientifique interne : scores_fusionnes.csv",
        "en": "Internal scientific CSV: scores_fusionnes.csv",
        "de": "Interne wissenschaftliche CSV: scores_fusionnes.csv",
        "zh": "内部科学 CSV：scores_fusionnes.csv",
        "ja": "内部科学CSV：scores_fusionnes.csv",
    },
    "analysis_btn_run_scientific": {
        "fr": "Lancer analyse scientifique", "en": "Run scientific analysis",
        "de": "Wissenschaftliche Analyse starten", "zh": "运行科学分析", "ja": "科学分析を実行",
    },
    "analysis_btn_load_csv": {
        "fr": "Charger un CSV externe", "en": "Load an external CSV",
        "de": "Externe CSV laden", "zh": "加载外部 CSV", "ja": "外部CSVを読み込む",
    },
    "analysis_results_analytics_desc": {
        "fr": "Les résultats sont générés automatiquement par le moteur statistique.",
        "en": "Results are generated automatically by the statistics engine.",
        "de": "Die Ergebnisse werden automatisch von der Statistik-Engine erzeugt.",
        "zh": "结果由统计引擎自动生成。",
        "ja": "結果は統計エンジンによって自動的に生成されます。",
    },
    "viz_residues_desc": {
        "fr": "Résidus du récepteur impliqués dans les interactions, calculés automatiquement pour tous les hits.",
        "en": "Receptor residues involved in the interactions, computed automatically for all hits.",
        "de": "Rezeptorreste, die an den Wechselwirkungen beteiligt sind, automatisch für alle Treffer berechnet.",
        "zh": "参与相互作用的受体残基，针对所有命中自动计算。",
        "ja": "相互作用に関与するレセプター残基。すべてのヒットについて自動的に計算されます。",
    },
    "viz_col_residue": {
        "fr": "Résidu", "en": "Residue", "de": "Rest", "zh": "残基", "ja": "残基",
    },
    "viz_col_chain": {
        "fr": "Chaîne", "en": "Chain", "de": "Kette", "zh": "链", "ja": "鎖",
    },
    "viz_col_position": {
        "fr": "Position", "en": "Position", "de": "Position", "zh": "位置", "ja": "位置",
    },
    "viz_col_type": {
        "fr": "Type", "en": "Type", "de": "Typ", "zh": "类型", "ja": "タイプ",
    },
    "viz_col_molecules": {
        "fr": "Molécules", "en": "Molecules", "de": "Moleküle", "zh": "分子", "ja": "分子",
    },
    "viz_plip_desc": {
        "fr": "Le calcul PLIP (extraction de pose, conversion PDB, interactions) est lancé automatiquement pour tous les hits — rien à configurer ici.",
        "en": "The PLIP calculation (pose extraction, PDB conversion, interactions) is run automatically for all hits — nothing to configure here.",
        "de": "Die PLIP-Berechnung (Pose-Extraktion, PDB-Konvertierung, Interaktionen) wird automatisch für alle Treffer ausgeführt — hier ist nichts zu konfigurieren.",
        "zh": "PLIP 计算（姿势提取、PDB 转换、相互作用）会自动针对所有命中运行 — 此处无需配置。",
        "ja": "PLIP計算（ポーズ抽出、PDB変換、相互作用）はすべてのヒットに対して自動的に実行されます。ここで設定する項目はありません。",
    },
    "viz_plip_state_panel_title": {
        "fr": "État du calcul", "en": "Calculation status",
        "de": "Berechnungsstatus", "zh": "计算状态", "ja": "計算状況",
    },
    "viz_plip_no_errors_yet": {
        "fr": "Aucune erreur pour le moment.", "en": "No errors so far.",
        "de": "Bisher keine Fehler.", "zh": "目前没有错误。", "ja": "現時点でエラーはありません。",
    },
    "viz_btn_export_image": {
        "fr": "Exporter l'image", "en": "Export image",
        "de": "Bild exportieren", "zh": "导出图像", "ja": "画像をエクスポート",
    },
    "viz_interaction_placeholder": {
        "fr": "VISUALISATION DES INTERACTIONS\n\nLes diagrammes sont générés automatiquement pour toutes les molécules ; choisis-en une ci-dessus pour l'afficher.",
        "en": "INTERACTION VISUALIZATION\n\nDiagrams are generated automatically for every molecule; pick one above to display it.",
        "de": "VISUALISIERUNG DER INTERAKTIONEN\n\nDiagramme werden automatisch für jedes Molekül erzeugt; wähle oben eines aus, um es anzuzeigen.",
        "zh": "相互作用可视化\n\n系统会自动为每个分子生成图表；请在上方选择一个以显示。",
        "ja": "相互作用の可視化\n\n各分子の図は自動的に生成されます。上で分子を選択すると表示されます。",
    },
}


def tr(key, lang="fr", **kwargs):
    """Retourne le texte traduit pour `key` dans la langue `lang`.
    Repli sur 'en' puis 'fr' si la langue ou la clé manquent."""
    entry = TR.get(key)
    if entry is None:
        return key
    text = entry.get(lang) or entry.get("en") or entry.get("fr", key)
    if kwargs:
        try:
            return text.format(**kwargs)
        except Exception:
            return text
    return text
