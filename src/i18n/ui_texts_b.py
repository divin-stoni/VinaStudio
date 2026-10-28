"""Lot B : textes releves au diagnostic (docking, import de recepteur, analyse, visualisation). Ordre : en, de, zh, ja."""
TABLE = {
    "Aucun fichier ou dossier SDF sélectionné.": (
        "No SDF file or folder selected.",
        "Keine SDF-Datei und kein Ordner ausgewählt.",
        "未选择 SDF 文件或文件夹。",
        "SDF ファイルまたはフォルダが選択されていません。"),
    "Texte(s) à supprimer, séparés par des virgules": (
        "Text(s) to remove, separated by commas",
        "Zu entfernende Texte, durch Kommas getrennt",
        "要删除的文本，以逗号分隔",
        "削除するテキスト（カンマ区切り）"),
    "Supprime un récepteur que tu as importé. Les récepteurs intégrés au logiciel ne peuvent jamais être supprimés.": (
        "Deletes a receptor you imported. The receptors built into the software can never be deleted.",
        "Löscht einen von dir importierten Rezeptor. Die in die Software integrierten Rezeptoren können nie gelöscht werden.",
        "删除您导入的受体。软件内置的受体永远无法删除。",
        "インポートした受容体を削除します。ソフトウェアに内蔵されている受容体は削除できません。"),
    "Identifie le rôle du ligand du cristal et télécharge les inhibiteurs de référence documentés pour cette pompe, avec leurs sources.": (
        "Identifies the role of the crystal ligand and downloads the documented reference inhibitors for this pump, with their sources.",
        "Ermittelt die Rolle des Kristallliganden und lädt die dokumentierten Referenzinhibitoren für diese Pumpe samt Quellen herunter.",
        "识别晶体配体的角色，并下载此外排泵已记录的参考抑制剂及其来源。",
        "結晶リガンドの役割を特定し、このポンプについて文献に記載された参照阻害剤を出典とともにダウンロードします。"),
    "Assemble une pompe d'efflux et son dérépresseur à partir de récepteurs déjà importés. Chaque récepteur garde sa configuration.": (
        "Assembles an efflux pump and its derepressor from receptors already imported. Each receptor keeps its configuration.",
        "Stellt aus bereits importierten Rezeptoren eine Effluxpumpe und ihren Derepressor zusammen. Jeder Rezeptor behält seine Konfiguration.",
        "用已导入的受体组合一个外排泵及其去阻遏蛋白。每个受体保留各自的配置。",
        "インポート済みの受容体から、排出ポンプとそのデリプレッサーの組を作ります。各受容体は自分の設定を保持します。"),
    "Enregistre la position/taille actuelle de la grid box : elle sera reprise à chaque démarrage pour ce récepteur.": (
        "Saves the current position/size of the grid box: it will be reloaded at each startup for this receptor.",
        "Speichert die aktuelle Position/Größe der Grid-Box: Sie wird bei jedem Start für diesen Rezeptor wieder geladen.",
        "保存 grid box 当前的位置/大小：每次启动时都会为该受体重新载入。",
        "grid box の現在の位置とサイズを保存します。この受容体では起動のたびに読み込まれます。"),
    "Revient à la configuration d'origine de ce récepteur, celle fournie avec le logiciel.": (
        "Returns to this receptor's original configuration, the one shipped with the software.",
        "Kehrt zur ursprünglichen Konfiguration dieses Rezeptors zurück, der mit der Software gelieferten.",
        "恢复到该受体的原始配置，即软件自带的配置。",
        "この受容体の元の設定（ソフトウェア付属のもの）に戻します。"),
    "Résidu de référence : GLU22, E22, A:22": (
        "Reference residue: GLU22, E22, A:22",
        "Referenzrest: GLU22, E22, A:22",
        "参考残基：GLU22, E22, A:22",
        "参照残基：GLU22, E22, A:22"),
    "Numéro seul (22), avec le nom (GLU22, Glu-22, E22, glutamate 22) et éventuellement la chaîne (A:GLU22, GLU22:B).": (
        "Number only (22), with the name (GLU22, Glu-22, E22, glutamate 22) and optionally the chain (A:GLU22, GLU22:B).",
        "Nur die Nummer (22), mit dem Namen (GLU22, Glu-22, E22, Glutamat 22) und optional der Kette (A:GLU22, GLU22:B).",
        "仅编号（22），或带名称（GLU22、Glu-22、E22、谷氨酸 22），可选择性附带链（A:GLU22、GLU22:B）。",
        "番号のみ（22）、名前付き（GLU22、Glu-22、E22、グルタミン酸 22）、必要に応じてチェーン付き（A:GLU22、GLU22:B）。"),
    "Place le centre de la grid box sur ce résidu. La taille et les curseurs restent réglables ensuite ; Enregistrer conserve le résultat.": (
        "Places the center of the grid box on this residue. The size and sliders remain adjustable afterwards; Save keeps the result.",
        "Setzt den Mittelpunkt der Grid-Box auf diesen Rest. Größe und Regler bleiben danach einstellbar; Speichern behält das Ergebnis.",
        "将 grid box 的中心放在该残基上。之后仍可调整大小和滑块；点击“保存”以保留结果。",
        "grid box の中心をこの残基に置きます。サイズとスライダーはその後も調整できます。「保存」で結果を保持します。"),
    "Tape le numéro du résidu (celui du fichier de la protéine), avec ou sans son nom, puis clique sur « Centrer ». Pas de virgule ni de point. Exemples : 22 · GLY22 · Gly-22 · G22 · glycine 22 · A:GLY22 (chaîne A). Si le nom ne correspond pas au numéro, le logiciel te prévient sans rien déplacer. Ensuite, ajuste les valeurs dans les champs puis clique sur « ✓ Enregistrer ».": (
        "Type the residue number (the one in the protein file), with or without its name, then click “Center”. No comma or period. Examples: 22 · GLY22 · Gly-22 · G22 · glycine 22 · A:GLY22 (chain A). If the name does not match the number, the software warns you without moving anything. Then adjust the values in the fields and click “✓ Save”.",
        "Gib die Nummer des Rests ein (die aus der Proteindatei), mit oder ohne Namen, und klicke dann auf „Zentrieren“. Kein Komma und kein Punkt. Beispiele: 22 · GLY22 · Gly-22 · G22 · Glycin 22 · A:GLY22 (Kette A). Stimmt der Name nicht mit der Nummer überein, warnt dich die Software, ohne etwas zu verschieben. Passe danach die Werte in den Feldern an und klicke auf „✓ Speichern“.",
        "输入残基编号（蛋白质文件中的编号），可带或不带名称，然后点击“居中”。不要使用逗号或句点。示例：22 · GLY22 · Gly-22 · G22 · 甘氨酸 22 · A:GLY22（A 链）。如果名称与编号不符，软件会提示您，且不会移动任何内容。然后在各字段中调整数值，并点击“✓ 保存”。",
        "残基番号（タンパク質ファイル内の番号）を、名前あり／なしで入力し、「中心に配置」をクリックします。カンマやピリオドは使わないでください。例：22 · GLY22 · Gly-22 · G22 · グリシン 22 · A:GLY22（チェーン A）。名前と番号が一致しない場合は、何も動かさずに警告します。その後、各欄の値を調整し、「✓ 保存」をクリックします。"),
    "Re-docke le ligand du cristal avec ta grid box et tes paramètres, puis compare avec sa vraie position. Sous 2 Å : configuration valide.": (
        "Re-docks the crystal ligand with your grid box and your parameters, then compares it with its true position. Below 2 Å: valid configuration.",
        "Dockt den Kristallliganden mit deiner Grid-Box und deinen Parametern erneut und vergleicht ihn mit seiner tatsächlichen Position. Unter 2 Å: gültige Konfiguration.",
        "使用您的 grid box 和参数重新对接晶体配体，并与其真实位置比较。低于 2 Å：配置有效。",
        "結晶リガンドを、あなたの grid box とパラメータで再ドッキングし、本来の位置と比較します。2 Å 未満：設定は有効です。"),
    "Cliquer pour agrandir, enregistrer ou copier la figure": (
        "Click to enlarge, save or copy the figure",
        "Klicken, um die Abbildung zu vergrößern, zu speichern oder zu kopieren",
        "点击以放大、保存或复制图片",
        "クリックして図を拡大・保存・コピーできます"),
    "◐ Noyau reproduit, queues variables : pose n°{} à {} Å, noyau {} Å ({}/{} atomes), queues flexibles {} Å ({} atomes) Critère noyau/queues : descripteur secondaire. Seule la reproduction globale sous 2 Å valide la configuration.": (
        "◐ Core reproduced, tails variable: pose #{} at {} Å, core {} Å ({}/{} atoms), flexible tails {} Å ({} atoms) Core/tail criterion: secondary descriptor. Only the overall reproduction below 2 Å validates the configuration.",
        "◐ Kern reproduziert, Enden variabel: Pose Nr. {} bei {} Å, Kern {} Å ({}/{} Atome), flexible Enden {} Å ({} Atome) Kern-/Endenkriterium: sekundärer Deskriptor. Nur die Gesamtreproduktion unter 2 Å validiert die Konfiguration.",
        "◐ 核心已复现，尾部可变：构象 {} 位于 {} Å，核心 {} Å（{}/{} 个原子），柔性尾部 {} Å（{} 个原子）核心/尾部标准：次要描述符。只有整体复现低于 2 Å 才能验证配置。",
        "◐ コアは再現、末端は変動：ポーズ {} は {} Å、コア {} Å（{}/{} 原子）、柔軟な末端 {} Å（{} 原子）コア／末端基準：二次的な記述子。全体の再現が 2 Å 未満の場合にのみ設定が有効と判断されます。"),
    "Filtrer les ligands par nom": (
        "Filter ligands by name",
        "Liganden nach Namen filtern",
        "按名称筛选配体",
        "名前でリガンドを絞り込む"),
    "Réinitialiser": (
        "Reset",
        "Zurücksetzen",
        "重置",
        "リセット"),
    "Temps écoulé : {} s   |   durée habituelle : environ {} s": (
        "Elapsed time: {} s   |   usual duration: about {} s",
        "Verstrichene Zeit: {} s   |   übliche Dauer: etwa {} s",
        "已用时间：{} 秒   |   通常耗时：约 {} 秒",
        "経過時間：{} 秒   |   通常の所要時間：約 {} 秒"),
    "Nommage des ligands": (
        "Ligand naming",
        "Benennung der Liganden",
        "配体命名",
        "リガンドの命名"),
    "Tout exporter la session": (
        "Export entire session",
        "Gesamte Sitzung exportieren",
        "导出整个会话",
        "セッション全体をエクスポート"),
    "Centrer la grid box sur un résidu de référence": (
        "Center the grid box on a reference residue",
        "Grid-Box auf einen Referenzrest zentrieren",
        "将 grid box 居中到参考残基上",
        "grid box を参照残基に中心合わせする"),
    "Centrer sur le résidu": (
        "Center on residue",
        "Auf Rest zentrieren",
        "居中到残基",
        "残基に中心合わせ"),
    "Revenir à une poche": (
        "Back to a pocket",
        "Zurück zu einer Tasche",
        "返回单个口袋",
        "ポケット表示に戻る"),
    "Aucun ligand sélectionné pour le docking.": (
        "No ligand selected for docking.",
        "Kein Ligand für das Docking ausgewählt.",
        "未选择用于对接的配体。",
        "ドッキング用のリガンドが選択されていません。"),
    "Tolérance pompe / inhibiteurs (kcal/mol) :": (
        "Pump / inhibitor tolerance (kcal/mol):",
        "Toleranz Pumpe / Inhibitoren (kcal/mol):",
        "外排泵/抑制剂容差（kcal/mol）：",
        "ポンプ／阻害剤の許容差（kcal/mol）："),
    "Aperçu global (tout afficher)": (
        "Global overview (show all)",
        "Gesamtansicht (alles anzeigen)",
        "全局预览（显示全部）",
        "全体表示（すべて表示）"),
    "Exhaustivité": (
        "Exhaustiveness",
        "Exhaustivität",
        "搜索详尽度",
        "探索の徹底度"),
    "Aucun fichier SDF sélectionné": (
        "No SDF file selected",
        "Keine SDF-Datei ausgewählt",
        "未选择 SDF 文件",
        "SDF ファイルが選択されていません"),
    "{} ligand": (
        "{} ligand",
        "{} Ligand",
        "{} 个配体",
        "{} 個のリガンド"),
    "{} ligand(s)": (
        "{} ligand(s)",
        "{} Ligand(en)",
        "{} 个配体",
        "{} 個のリガンド"),
    "Détecter les poches (fpocket)": (
        "Detect pockets (fpocket)",
        "Taschen erkennen (fpocket)",
        "检测口袋（fpocket）",
        "ポケットを検出（fpocket）"),
    "Récepteur : {}": (
        "Receptor: {}",
        "Rezeptor: {}",
        "受体：{}",
        "受容体：{}"),
    "Prêt": (
        "Ready",
        "Bereit",
        "就绪",
        "準備完了"),
    "Seuil de risque (référence) :": (
        "Risk threshold (reference):",
        "Risikoschwelle (Referenz):",
        "风险阈值（参考）：",
        "リスクしきい値（参照）："),
    "Aucun calcul en cours": (
        "No calculation running",
        "Keine Berechnung läuft",
        "没有正在进行的计算",
        "実行中の計算はありません"),
    "Vérifier ma configuration": (
        "Check my configuration",
        "Konfiguration prüfen",
        "检查我的配置",
        "設定を確認する"),
    "Choisis une poche (ou navigue avec les flèches) : elle s'affiche seule, caméra recadrée — pratique pour une capture d'écran nette.": (
        "Choose a pocket (or navigate with the arrow keys): it is displayed alone, camera reframed — handy for a clean screenshot.",
        "Wähle eine Tasche (oder navigiere mit den Pfeiltasten): Sie wird allein angezeigt, die Kamera neu ausgerichtet – praktisch für einen sauberen Screenshot.",
        "选择一个口袋（或用方向键切换）：它将单独显示，相机会重新取景——便于截取清晰的截图。",
        "ポケットを選ぶ（または矢印キーで移動）と、そのポケットだけが表示されカメラも調整されます。きれいなスクリーンショットに便利です。"),
    "En attente du premier passage sur cet onglet…": (
        "Waiting for the first visit to this tab…",
        "Warte auf den ersten Besuch dieses Tabs…",
        "正在等待首次访问此标签页…",
        "このタブが最初に開かれるのを待っています…"),
    "Aucune plante confirmée.": (
        "No confirmed plant.",
        "Keine bestätigte Pflanze.",
        "没有已确认的植物。",
        "確認された植物はありません。"),
    "Aucune analyse chargée.": (
        "No analysis loaded.",
        "Keine Analyse geladen.",
        "未加载分析。",
        "解析は読み込まれていません。"),
    "Visualisation désactivée en mode double cible.": (
        "Visualization disabled in dual-target mode.",
        "Visualisierung im Doppelziel-Modus deaktiviert.",
        "双靶标模式下已禁用可视化。",
        "デュアルターゲットモードでは可視化は無効です。"),
    "État": (
        "Status",
        "Status",
        "状态",
        "状態"),
    "Ouvrir le dossier des PDBQT": (
        "Open the PDBQT folder",
        "PDBQT-Ordner öffnen",
        "打开 PDBQT 文件夹",
        "PDBQT フォルダを開く"),
    "Ouvrir le dossier de sortie": (
        "Open the output folder",
        "Ausgabeordner öffnen",
        "打开输出文件夹",
        "出力フォルダを開く"),
    "Construction de l'interface principale (dernière étape)": (
        "Building the main interface (last step)",
        "Hauptoberfläche wird aufgebaut (letzter Schritt)",
        "正在构建主界面（最后一步）",
        "メインインターフェースを構築中（最終ステップ）"),
    "Aucune campagne": (
        "No campaign",
        "Keine Kampagne",
        "没有批次",
        "キャンペーンなし"),
    "Aucun hit exploitable trouvé (dossier cherché : {}).": (
        "No usable hit found (folder searched: {}).",
        "Kein verwertbarer Treffer gefunden (durchsuchter Ordner: {}).",
        "未找到可用的命中结果（已搜索的文件夹：{}）。",
        "利用可能なヒットが見つかりませんでした（検索したフォルダ：{}）。"),
    "Choisir le dossier où créer l'export": (
        "Choose the folder where the export will be created",
        "Ordner wählen, in dem der Export erstellt wird",
        "选择创建导出的文件夹",
        "エクスポートを作成するフォルダを選択"),
    "Paramètres d'apparence": (
        "Appearance settings",
        "Darstellungsparameter",
        "外观参数",
        "外観パラメータ"),
    "Revenir à la couleur automatique": (
        "Revert to automatic color",
        "Zur automatischen Farbe zurückkehren",
        "恢复自动颜色",
        "自動色に戻す"),
    "Filtrer les textes…": (
        "Filter texts…",
        "Texte filtern…",
        "筛选文本…",
        "テキストを絞り込む…"),
    "Annuler": (
        "Cancel",
        "Abbrechen",
        "取消",
        "キャンセル"),
    "Choisir un fichier CSV scientifique": (
        "Choose a scientific CSV file",
        "Wissenschaftliche CSV-Datei auswählen",
        "选择科学 CSV 文件",
        "科学用 CSV ファイルを選択"),
    "Boîte {} × {} × {} Å, volume {} Å³ · {} résidus dans la boîte, dont {} coupés en bordure": (
        "Box {} × {} × {} Å, volume {} Å³ · {} residues in the box, {} of which cut at the edge",
        "Box {} × {} × {} Å, Volumen {} Å³ · {} Reste in der Box, davon {} am Rand angeschnitten",
        "盒子 {} × {} × {} Å，体积 {} Å³ · 盒内 {} 个残基，其中 {} 个在边缘被截断",
        "ボックス {} × {} × {} Å、体積 {} Å³ · ボックス内の残基 {} 個、うち {} 個が境界で切断"),
    "Importer un récepteur": (
        "Import a receptor",
        "Rezeptor importieren",
        "导入受体",
        "受容体をインポート"),
    "Importer un récepteur (PDB / PDBQT)": (
        "Import a receptor (PDB / PDBQT)",
        "Rezeptor importieren (PDB / PDBQT)",
        "导入受体（PDB / PDBQT）",
        "受容体をインポート（PDB / PDBQT）"),
    "Supprimer un récepteur importé": (
        "Delete an imported receptor",
        "Importierten Rezeptor löschen",
        "删除已导入的受体",
        "インポート済み受容体を削除"),
    "Télécharger depuis le RCSB (code à 4 caractères) :": (
        "Download from RCSB (4-character code):",
        "Vom RCSB herunterladen (4-stelliger Code):",
        "从 RCSB 下载（4 位代码）：",
        "RCSB からダウンロード（4 文字のコード）："),
    "Télécharger": (
        "Download",
        "Herunterladen",
        "下载",
        "ダウンロード"),
    "Choisir un fichier PDB ou PDBQT…": (
        "Choose a PDB or PDBQT file…",
        "PDB- oder PDBQT-Datei auswählen…",
        "选择 PDB 或 PDBQT 文件…",
        "PDB または PDBQT ファイルを選択…"),
    "Importer un récepteur : fiche de la structure": (
        "Import a receptor: structure sheet",
        "Rezeptor importieren: Strukturübersicht",
        "导入受体：结构信息",
        "受容体のインポート：構造の概要"),
    "Distance ajoutée de chaque côté du ligand. Les ligands à cribler sont souvent plus gros que celui du cristal : garde de la marge.": (
        "Distance added on each side of the ligand. The ligands to screen are often larger than the crystal one: keep some margin.",
        "Auf jeder Seite des Liganden hinzugefügter Abstand. Die zu screenenden Liganden sind oft größer als der im Kristall: Lass etwas Spielraum.",
        "在配体每一侧增加的距离。待筛选的配体通常比晶体中的配体更大：请留出余量。",
        "リガンドの各側に加える距離。スクリーニング対象のリガンドは結晶中のものより大きいことが多いため、余裕を持たせてください。"),
    "Coché par défaut : sans hydrogènes polaires, Vina ne voit pas les liaisons hydrogène. Décoché si le fichier en contient déjà.": (
        "Checked by default: without polar hydrogens, Vina cannot see hydrogen bonds. Uncheck if the file already contains them.",
        "Standardmäßig aktiviert: Ohne polare Wasserstoffe erkennt Vina keine Wasserstoffbrücken. Deaktivieren, wenn die Datei sie bereits enthält.",
        "默认勾选：没有极性氢，Vina 无法识别氢键。如果文件已包含氢原子，请取消勾选。",
        "既定でオンです。極性水素がないと Vina は水素結合を認識できません。ファイルにすでに含まれている場合はオフにしてください。"),
    "Chaîne liante, ligand de référence le plus fiable, marge de 8 Å, hydrogènes ajoutés, nettoyage conseillé.": (
        "Binding chain, most reliable reference ligand, 8 Å margin, hydrogens added, cleanup recommended.",
        "Bindende Kette, zuverlässigster Referenzligand, 8 Å Rand, Wasserstoffe hinzugefügt, Bereinigung empfohlen.",
        "结合链、最可靠的参考配体、8 Å 边距、添加氢原子、建议清理。",
        "結合チェーン、最も信頼できる参照リガンド、余白 8 Å、水素を追加、クリーンアップを推奨。"),
    "Chaîne": (
        "Chain",
        "Kette",
        "链",
        "チェーン"),
    "Molécule": (
        "Molecule",
        "Molekül",
        "分子",
        "分子"),
    "Résidus": (
        "Residues",
        "Reste",
        "残基",
        "残基"),
    "Chaînes à conserver pour le docking": (
        "Chains to keep for docking",
        "Für das Docking beizubehaltende Ketten",
        "对接时保留的链",
        "ドッキングに残すチェーン"),
    "Une chaîne par groupe": (
        "One chain per group",
        "Eine Kette pro Gruppe",
        "每组一条链",
        "グループごとに 1 チェーン"),
    "Aucune": (
        "None",
        "Keine",
        "无",
        "なし"),
    "Placer la grid box autour du ligand :": (
        "Place the grid box around the ligand:",
        "Grid-Box um den Liganden platzieren:",
        "将 grid box 放置在配体周围：",
        "grid box をリガンドの周囲に配置："),
    "Ajouter les hydrogènes à la conversion (pH 7,4)": (
        "Add hydrogens during conversion (pH 7.4)",
        "Wasserstoffe bei der Konvertierung hinzufügen (pH 7,4)",
        "转换时添加氢原子（pH 7.4）",
        "変換時に水素を追加（pH 7.4）"),
    "Retirés du fichier : eaux, ions, additifs et ligands (le ligand choisi sert uniquement à placer la grid box). Un rapport détaillé est écrit à côté du fichier nettoyé.": (
        "Removed from the file: water, ions, additives and ligands (the chosen ligand is only used to place the grid box). A detailed report is written next to the cleaned file.",
        "Aus der Datei entfernt: Wasser, Ionen, Zusätze und Liganden (der gewählte Ligand dient nur zum Platzieren der Grid-Box). Ein ausführlicher Bericht wird neben der bereinigten Datei gespeichert.",
        "从文件中移除：水、离子、添加剂和配体（所选配体仅用于放置 grid box）。详细报告会写在清理后文件的旁边。",
        "ファイルから除去されるもの：水、イオン、添加物、リガンド（選択したリガンドは grid box の配置にのみ使用）。詳細なレポートはクリーンアップ後のファイルの隣に書き出されます。"),
    "Appliquer les réglages recommandés": (
        "Apply recommended settings",
        "Empfohlene Einstellungen anwenden",
        "应用推荐设置",
        "推奨設定を適用"),
    "Supprimer des récepteurs importés": (
        "Delete imported receptors",
        "Importierte Rezeptoren löschen",
        "删除已导入的受体",
        "インポート済み受容体を削除"),
    "Sélectionne le ou les récepteurs importés à supprimer\n(Ctrl ou Maj pour en choisir plusieurs). Les récepteurs intégrés\nne figurent pas dans cette liste.": (
        "Select the imported receptor(s) to delete\n(Ctrl or Shift to choose several). The built-in receptors\nare not in this list.",
        "Wähle die zu löschenden importierten Rezeptoren aus\n(Strg oder Umschalt für mehrere). Die integrierten Rezeptoren\nstehen nicht in dieser Liste.",
        "选择要删除的已导入受体\n（按 Ctrl 或 Shift 可多选）。内置受体\n不在此列表中。",
        "削除するインポート済み受容体を選択してください\n（Ctrl または Shift で複数選択）。内蔵の受容体は\nこの一覧には表示されません。"),
}
