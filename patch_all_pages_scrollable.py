# -*- coding: utf-8 -*-
from pathlib import Path
import shutil
import datetime

TARGET = Path("src/gui/main_window.py")
backup = TARGET.with_suffix(TARGET.suffix + f".bak_{datetime.datetime.now():%Y%m%d_%H%M%S}")
shutil.copy2(TARGET, backup)
print(f"✓ Sauvegarde créée : {backup}")

content = TARGET.read_text(encoding="utf-8")
original = content

def apply(old, new, label):
    global content
    count = content.count(old)
    if count != 1:
        raise SystemExit(f"✗ [{label}] trouvé {count} fois (attendu 1), patch annulé.")
    content = content.replace(old, new, 1)
    print(f"✓ [{label}] patché")

def scroll_wrap(object_name, indent="        "):
    return (
        f"\n{indent}scroll = QScrollArea()\n"
        f"{indent}scroll.setObjectName(\"{object_name}\")\n"
        f"{indent}scroll.setWidgetResizable(True)\n"
        f"{indent}scroll.setFrameShape(QFrame.NoFrame)\n"
        f"{indent}scroll.setWidget(page)\n\n"
        f"{indent}return scroll"
    )

# 1. sdf_page (ligne ~1031)
apply(
    '''        layout.addWidget(
            log_panel
        )

        layout.addStretch()

        return page''',
    '''        layout.addWidget(
            log_panel
        )

        layout.addStretch()
''' + scroll_wrap("SdfScrollArea"),
    "sdf_page",
)

# 2. pdbqt_page (ligne ~1416)
apply(
    '''
        layout.addWidget(
            self.pdbqt_table,
            1,
        )

        return page''',
    '''
        layout.addWidget(
            self.pdbqt_table,
            1,
        )
''' + scroll_wrap("PdbqtScrollArea"),
    "pdbqt_page",
)

# 3. results_page - retour anticipé (ligne ~3245, indentation 12 espaces)
apply(
    '''
            layout.addWidget(
                table,
                1
            )

            return page''',
    '''
            layout.addWidget(
                table,
                1
            )
''' + scroll_wrap("ResultsEmptyScrollArea", indent="            "),
    "results_page (retour anticipé)",
)

# 4. results_page - retour final (ligne ~3308)
apply(
    '''                        col,
                        QTableWidgetItem(str(value)),
                    )

        layout.addWidget(table, 1)

        return page''',
    '''                        col,
                        QTableWidgetItem(str(value)),
                    )

        layout.addWidget(table, 1)
''' + scroll_wrap("ResultsScrollArea"),
    "results_page (retour final)",
)

# 5. analysis_type_page (ligne ~3560)
apply(
    '''        layout.addWidget(
            panel
        )

        layout.addStretch()

        return page''',
    '''        layout.addWidget(
            panel
        )

        layout.addStretch()
''' + scroll_wrap("AnalysisTypeScrollArea"),
    "analysis_type_page",
)

# 6. analysis_results_page (ligne ~4081)
apply(
    '''        layout.addWidget(
            self.results_tabs,
            1
        )


        return page''',
    '''        layout.addWidget(
            self.results_tabs,
            1
        )
''' + scroll_wrap("AnalysisResultsScrollArea"),
    "analysis_results_page",
)

# 7. residues_page (ligne ~4351)
apply(
    '''            table.horizontalHeader().setSectionResizeMode(col, QHeaderView.Stretch)

        self.residues_table = table

        layout.addWidget(table, 1)

        return page''',
    '''            table.horizontalHeader().setSectionResizeMode(col, QHeaderView.Stretch)

        self.residues_table = table

        layout.addWidget(table, 1)
''' + scroll_wrap("ResiduesScrollArea"),
    "residues_page",
)

# 8. plip_page (ligne ~4426)
apply(
    '''
        panel_layout.addWidget(plip_errors_scroll)

        layout.addWidget(panel)
        layout.addStretch()

        return page''',
    '''
        panel_layout.addWidget(plip_errors_scroll)

        layout.addWidget(panel)
        layout.addStretch()
''' + scroll_wrap("PlipScrollArea"),
    "plip_page",
)

# 9. interaction_page (ligne ~4486)
apply(
    '''        self.diagram_label = message

        viewer_layout.addWidget(message)

        layout.addWidget(viewer, 1)

        return page''',
    '''        self.diagram_label = message

        viewer_layout.addWidget(message)

        layout.addWidget(viewer, 1)
''' + scroll_wrap("InteractionScrollArea"),
    "interaction_page",
)

if content == original:
    raise SystemExit("✗ Aucune modification appliquée au total.")

TARGET.write_text(content, encoding="utf-8")
print()
print(f"✓ TERMINE : {TARGET} patché, {content.count('QScrollArea()') } zones QScrollArea au total dans le fichier")
