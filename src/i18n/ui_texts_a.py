"""Lot A : grid box, molecules de reference, themes, export, demarrage. Ordre : en, de, zh, ja."""
TABLE = {
    # ---- export_everything ----
    "Aucun résultat de la session en cours à exporter pour le moment.": (
        "No results from the current session to export for now.",
        "Derzeit keine Ergebnisse der aktuellen Sitzung zum Exportieren.",
        "当前会话暂无可导出的结果。",
        "現在のセッションには、エクスポートできる結果がまだありません。"),
    "Exporte tout dans un dossier daté, rangé par catégories": (
        "Exports everything to a dated folder, organized by category",
        "Exportiert alles in einen datierten Ordner, nach Kategorien geordnet",
        "将所有内容导出到带日期的文件夹，并按类别整理",
        "すべてを日付付きフォルダにカテゴリ別にエクスポートします"),
    "Pipeline terminé : pensez à exporter": (
        "Pipeline finished: remember to export",
        "Pipeline abgeschlossen: Denken Sie an den Export",
        "流程已完成：请记得导出",
        "パイプラインが完了しました：エクスポートをお忘れなく"),
    "Le docking, l'analyse et le calcul des interactions sont terminés.\n\nLes résultats de cette session sont effacés à la fermeture du logiciel.\nVoulez-vous les exporter maintenant ? (vous choisissez le dossier)": (
        "Docking, analysis and interaction calculation are complete.\n\nThe results of this session are erased when the software is closed.\nDo you want to export them now? (you choose the folder)",
        "Docking, Analyse und Interaktionsberechnung sind abgeschlossen.\n\nDie Ergebnisse dieser Sitzung werden beim Schließen der Software gelöscht.\nMöchten Sie sie jetzt exportieren? (Sie wählen den Ordner)",
        "对接、分析和相互作用计算已完成。\n\n本次会话的结果将在关闭软件时清除。\n是否现在导出？（由您选择文件夹）",
        "ドッキング、解析、相互作用の計算が完了しました。\n\nこのセッションの結果は、ソフトウェアを閉じると消去されます。\n今すぐエクスポートしますか？（フォルダは選択できます）"),
    "Pensez à exporter": (
        "Remember to export",
        "Denken Sie an den Export",
        "请记得导出",
        "エクスポートをお忘れなく"),
    "Proposer l'export à la fin du pipeline complet": (
        "Offer to export at the end of the full pipeline",
        "Export am Ende der gesamten Pipeline anbieten",
        "完整流程结束时提示导出",
        "パイプライン全体の終了時にエクスポートを提案する"),
    "Rappel « Pensez à exporter » (étapes manquantes)": (
        "Reminder “Remember to export” (missing steps)",
        "Erinnerung „Denken Sie an den Export“ (fehlende Schritte)",
        "提醒“请记得导出”（缺少的步骤）",
        "リマインダー「エクスポートをお忘れなく」（未完了のステップ）"),
    "Exporte tout dans un dossier daté, rangé par catégories (clic droit : options des rappels)": (
        "Exports everything to a dated folder, organized by category (right-click: reminder options)",
        "Exportiert alles in einen datierten Ordner, nach Kategorien geordnet (Rechtsklick: Erinnerungsoptionen)",
        "将所有内容导出到带日期的文件夹，并按类别整理（右键：提醒选项）",
        "すべてを日付付きフォルダにカテゴリ別にエクスポートします（右クリック：リマインダーの設定）"),
    # ---- grid_precision ----
    "Ajustement précis de la grid box": (
        "Fine-tune the grid box",
        "Grid-Box präzise anpassen",
        "精确调整 grid box",
        "grid box の精密調整"),
    "Calcule le centre et la taille de la boîte à partir d'un ligand ou de résidus. Rien n'est enregistré tant que tu n'as pas cliqué sur Enregistrer. Maj + flèches dans un champ : pas fin (÷10).": (
        "Computes the center and size of the box from a ligand or from residues. Nothing is saved until you click Save. Shift + arrow keys in a field: fine step (÷10).",
        "Berechnet Mittelpunkt und Größe der Box anhand eines Liganden oder von Resten. Es wird nichts gespeichert, bis du auf Speichern klickst. Umschalt + Pfeiltasten in einem Feld: feiner Schritt (÷10).",
        "根据配体或残基计算盒子的中心和大小。点击“保存”之前不会保存任何内容。在输入框中按 Shift + 方向键：精细步长（÷10）。",
        "リガンドまたは残基からボックスの中心とサイズを計算します。「保存」をクリックするまで何も保存されません。入力欄で Shift + 矢印キー：細かいステップ（÷10）。"),
    "Distance ajoutée de chaque côté de la cible. 4 à 6 Å est la plage usuelle avec Vina.": (
        "Distance added on each side of the target. 4 to 6 Å is the usual range with Vina.",
        "Auf jeder Seite des Ziels hinzugefügter Abstand. 4 bis 6 Å ist der übliche Bereich bei Vina.",
        "在目标每一侧增加的距离。使用 Vina 时通常为 4 至 6 Å。",
        "ターゲットの各側に加える距離。Vina では 4〜6 Å が一般的な範囲です。"),
    "Autour du ligand du récepteur": (
        "Around the receptor's ligand",
        "Um den Liganden des Rezeptors",
        "围绕受体的配体",
        "受容体のリガンドの周囲"),
    "Utilise le ligand co-cristallisé (HETATM) présent dans le fichier du récepteur.": (
        "Uses the co-crystallized ligand (HETATM) present in the receptor file.",
        "Verwendet den kokristallisierten Liganden (HETATM) aus der Rezeptordatei.",
        "使用受体文件中的共结晶配体（HETATM）。",
        "受容体ファイルに含まれる共結晶リガンド（HETATM）を使用します。"),
    "Autour d'un fichier ligand…": (
        "Around a ligand file…",
        "Um eine Ligandendatei…",
        "围绕配体文件…",
        "リガンドファイルの周囲…"),
    "SDF, MOL, PDB ou PDBQT. Les coordonnées doivent être dans le même repère que le récepteur (ligand co-cristallisé ou pose de docking).": (
        "SDF, MOL, PDB or PDBQT. The coordinates must be in the same frame as the receptor (co-crystallized ligand or docking pose).",
        "SDF, MOL, PDB oder PDBQT. Die Koordinaten müssen im selben Bezugssystem wie der Rezeptor liegen (kokristallisierter Ligand oder Docking-Pose).",
        "SDF、MOL、PDB 或 PDBQT。坐标必须与受体处于同一坐标系（共结晶配体或对接构象）。",
        "SDF、MOL、PDB、または PDBQT。座標は受容体と同じ座標系である必要があります（共結晶リガンドまたはドッキングポーズ）。"),
    "Résidus : GLY22, F178, A:VAL139": (
        "Residues: GLY22, F178, A:VAL139",
        "Reste: GLY22, F178, A:VAL139",
        "残基：GLY22, F178, A:VAL139",
        "残基：GLY22, F178, A:VAL139"),
    "Entourer ces résidus": (
        "Surround these residues",
        "Diese Reste umschließen",
        "围绕这些残基",
        "これらの残基を囲む"),
    "Annuler le dernier ajustement": (
        "Undo last adjustment",
        "Anpassung rückgängig",
        "撤销上次调整",
        "直前の調整を元に戻す"),
    "Marge de chaque côté": (
        "Margin on each side",
        "Rand auf jeder Seite",
        "每侧边距",
        "各辺の余白"),
    "Enregistrer": (
        "Save",
        "Speichern",
        "保存",
        "保存"),
    # ---- molecules de reference ----
    "Molécules de référence": (
        "Reference molecules",
        "Referenzmoleküle",
        "参考分子",
        "参照分子"),
    "Références non converties": (
        "Unconverted references",
        "Nicht konvertierte Referenzen",
        "未转换的参考分子",
        "変換されなかった参照分子"),
    "Choisis la cible, puis ajoute ses molécules de référence : inhibiteurs, substrats ou dérépresseurs (la molécule qui libère le répresseur, par exemple la pyocyanine pour MexR). Le rôle choisi décide de son usage dans l'analyse.": (
        "Choose the target, then add its reference molecules: inhibitors, substrates or derepressors (the molecule that releases the repressor, for example pyocyanin for MexR). The chosen role determines how it is used in the analysis.",
        "Wähle das Ziel und füge dann seine Referenzmoleküle hinzu: Inhibitoren, Substrate oder Derepressoren (das Molekül, das den Repressor freisetzt, z. B. Pyocyanin für MexR). Die gewählte Rolle bestimmt ihre Verwendung in der Analyse.",
        "选择靶标，然后添加其参考分子：抑制剂、底物或去阻遏物（释放阻遏蛋白的分子，例如针对 MexR 的绿脓菌素）。所选角色决定该分子在分析中的用途。",
        "標的を選び、その参照分子（阻害剤、基質、またはリプレッサー解除分子＝リプレッサーを解離させる分子。例：MexR に対するピオシアニン）を追加します。選んだ役割によって、解析での使われ方が決まります。"),
    "Ajouter une molécule :": (
        "Add a molecule:",
        "Molekül hinzufügen:",
        "添加分子：",
        "分子を追加："),
    "Nom PubChem (ex. pyocyanin), ou nom à donner à ton fichier": (
        "PubChem name (e.g. pyocyanin), or a name for your file",
        "PubChem-Name (z. B. pyocyanin) oder ein Name für deine Datei",
        "PubChem 名称（例如 pyocyanin），或为您的文件指定的名称",
        "PubChem 名（例：pyocyanin）、またはファイルに付ける名前"),
    "Importer un fichier (SDF, MOL, MOL2, PDB)…": (
        "Import a file (SDF, MOL, MOL2, PDB)…",
        "Datei importieren (SDF, MOL, MOL2, PDB)…",
        "导入文件（SDF、MOL、MOL2、PDB）…",
        "ファイルをインポート（SDF、MOL、MOL2、PDB）…"),
    "Aucun fichier choisi": (
        "No file chosen",
        "Keine Datei ausgewählt",
        "未选择文件",
        "ファイルが選択されていません"),
    "Inhibiteurs documentés (liste vérifiée) :": (
        "Documented inhibitors (verified list):",
        "Dokumentierte Inhibitoren (geprüfte Liste):",
        "已记录的抑制剂（已核实列表）：",
        "文献で確認された阻害剤（検証済みリスト）："),
    "Pas de liste vérifiée pour cette cible : ajoute tes molécules ci-dessous.": (
        "No verified list for this target: add your molecules below.",
        "Keine geprüfte Liste für dieses Ziel: Füge unten deine Moleküle hinzu.",
        "此靶标没有已核实的列表：请在下方添加您的分子。",
        "この標的には検証済みリストがありません。下に分子を追加してください。"),
    # ---- themes ----
    "Préférences d'apparence": (
        "Appearance preferences",
        "Darstellungseinstellungen",
        "外观偏好设置",
        "外観の設定"),
    "Apparence liquide et transparence": (
        "Liquid look and transparency",
        "Flüssiges Erscheinungsbild und Transparenz",
        "液态外观与透明度",
        "リキッド外観と透明度"),
    "Formes et transparence": (
        "Shapes and transparency",
        "Formen und Transparenz",
        "形状与透明度",
        "形状と透明度"),
    "Optique du verre": (
        "Glass optics",
        "Glasoptik",
        "玻璃光学效果",
        "ガラスの光学効果"),
    "Vie du verre": (
        "Glass animation",
        "Glasanimation",
        "玻璃动态效果",
        "ガラスのアニメーション"),
    "Thèmes rapides :": (
        "Quick themes:",
        "Schnellthemen:",
        "快速主题：",
        "クイックテーマ："),
    "Aléatoire": (
        "Random",
        "Zufällig",
        "随机",
        "ランダム"),
    # ---- astuces, demarrage, phytomolecules ----
    "Passer les astuces": (
        "Skip tips",
        "Tipps überspringen",
        "跳过提示",
        "ヒントをスキップ"),
    "Démarrage en cours, veuillez patienter...": (
        "Starting up, please wait...",
        "Start läuft, bitte warten...",
        "正在启动，请稍候...",
        "起動中です。しばらくお待ちください..."),
    "Ne relancez pas le logiciel : il est en train de démarrer.": (
        "Do not relaunch the software: it is starting.",
        "Starten Sie die Software nicht erneut: Sie wird gerade gestartet.",
        "请勿重新启动软件：它正在启动。",
        "ソフトウェアを再起動しないでください。現在起動中です。"),
    "Cela peut durer de quelques secondes à quelques minutes. Ne fermez pas le logiciel.": (
        "This can take from a few seconds to a few minutes. Do not close the software.",
        "Das kann einige Sekunden bis einige Minuten dauern. Schließen Sie die Software nicht.",
        "这可能需要几秒到几分钟。请勿关闭软件。",
        "数秒から数分かかる場合があります。ソフトウェアを閉じないでください。"),
}
