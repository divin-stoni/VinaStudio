# -*- coding: utf-8 -*-
"""
viewer_template.py

Template HTML autonome pour le visualiseur 3Dmol.js embarqué dans
QWebEngineView. Fonctions JS exposées, appelées depuis Python via
page().runJavaScript() :

    loadReceptor(pdbData)                       -> charge un récepteur
    updateBox(cx, cy, cz, sx, sy, sz)            -> dessine/repositionne
                                                     la grid box

Style visuel : fond blanc, cartoon opaque, avec mise en surbrillance
légère (sphère fine) du résidu survolé. Le panneau d'info du résidu
survolé est une bande verticale semi-transparente superposée
directement dans le viewport (pas un widget Qt séparé) — mise à jour
en JavaScript pur au survol, sans aller-retour vers Python.

Nécessite un accès réseau au runtime pour charger 3Dmol.js depuis son
CDN (https://3Dmol.org) — à bundler localement pour le packaging Windows
hors-ligne (chantier séparé, voir build_windows.yml).
"""

VIEWER_HTML = """<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <script src="https://3Dmol.org/build/3Dmol-min.js"></script>
  <script src="qrc:///qtwebchannel/qwebchannel.js"></script>
  <style>
    html, body {
      margin: 0;
      background: #ffffff;
      height: 100%;
    }
    #wrapper {
      position: relative;
      width: 100%;
      height: 100vh;
    }
    #container {
      width: 100%;
      height: 100%;
    }
    #residue-panel {
      position: absolute;
      top: 12px;
      right: 12px;
      width: 190px;
      max-height: calc(100% - 24px);
      overflow-y: auto;
      background: rgba(255, 255, 255, 0.82);
      border: 1px solid #cfd5dc;
      border-radius: 6px;
      padding: 10px 12px;
      font-family: "Noto Sans", "Segoe UI", sans-serif;
      font-size: 12px;
      color: #26323d;
      box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
      pointer-events: none;
    }
    #residue-panel .title {
      font-weight: 650;
      font-size: 11px;
      color: #65717d;
      text-transform: uppercase;
      letter-spacing: 0.03em;
      margin-bottom: 6px;
    }
    #residue-panel .value {
      font-size: 14px;
      font-weight: 600;
      color: #246b8f;
    }
    #residue-panel .empty {
      font-size: 12px;
      color: #89939d;
      font-style: italic;
    }
  </style>
</head>
<body>
  <div id="wrapper">
    <div id="container"></div>
    <div id="residue-panel">
      <div class="title">Résidu survolé</div>
      <div id="residue-panel-content" class="empty">Survolez la protéine...</div>
    </div>
  </div>
  <script>
    let viewer = $3Dmol.createViewer("container", {backgroundColor: "0xffffff"});
    let currentBox = null;
    let currentHighlight = null;
    let currentPockets = [];
    let pocketModels = {};   // pocket_id -> GLModel (ou null si pas de PQR)
    let pocketColors = {};   // pocket_id -> couleur
    let pocketFallback = {}; // pocket_id -> {center, radius} (repli bulle)
    let pocketVisible = {};  // pocket_id -> bool
    let pocketShapes = {};   // pocket_id -> shape (repli bulle affichee)
    let bridge = null;

    if (typeof qt !== "undefined" && qt.webChannelTransport) {
      new QWebChannel(qt.webChannelTransport, function(channel) {
        bridge = channel.objects.bridge;
      });
    }

    function updateResiduePanel(chain, resn, resi) {
      const content = document.getElementById("residue-panel-content");
      if (!chain && !resn && !resi) {
        content.className = "empty";
        content.textContent = "Survolez la protéine...";
        return;
      }
      content.className = "value";
      content.textContent = "Chaîne " + (chain || "?") + "  —  " +
        (resn || "?") + " " + (resi || "?");
    }

    function loadReceptor(pdbData) {
      viewer.clear();
      currentBox = null;
      currentHighlight = null;

      viewer.addModel(pdbData, "pdb");

      // Ruban opaque, coloré par chaîne (pas de transparence globale --
      // seul le résidu survolé est mis en avant, voir plus bas).
      viewer.setStyle({}, {cartoon: {color: "spectrum", opacity: 1.0}});

      viewer.setHoverable(
        {},
        true,
        function(atom, viewer, event, container) {
          if (currentHighlight) {
            viewer.removeShape(currentHighlight);
            currentHighlight = null;
          }

          // Légère mise en surbrillance : une fine sphère semi-
          // transparente sur l'atome survolé, pas un changement de
          // style de tout le résidu (reste discret, pas envahissant).
          currentHighlight = viewer.addSphere({
            center: {x: atom.x, y: atom.y, z: atom.z},
            radius: 1.0,
            color: "orange",
            opacity: 0.55
          });
          viewer.render();

          updateResiduePanel(
            atom.chain || "",
            atom.resn || "",
            atom.resi != null ? String(atom.resi) : ""
          );

          if (bridge) {
            bridge.onResidueHover(
              atom.chain || "",
              atom.resn || "",
              atom.resi != null ? String(atom.resi) : ""
            );
          }
        },
        function(atom, viewer, event, container) {
          if (currentHighlight) {
            viewer.removeShape(currentHighlight);
            currentHighlight = null;
            viewer.render();
          }
          updateResiduePanel("", "", "");
          if (bridge) {
            bridge.onResidueHover("", "", "");
          }
        }
      );

      viewer.zoomTo();
      viewer.render();
    }

    function loadComplex(pdbData, interactionsJson) {
      viewer.clear();
      currentBox = null;
      currentHighlight = null;

      const model = viewer.addModel(pdbData, "pdb");
      viewer.setStyle({model: model, hetflag: false}, {
        cartoon: {color: "spectrum", opacity: 1.0}
      });
      viewer.setStyle({model: model, hetflag: true}, {
        stick: {colorscheme: "Jmol", radius: 0.18}
      });

      let interactions = [];
      try { interactions = JSON.parse(interactionsJson || "[]"); }
      catch (error) { interactions = []; }

      const highlighted = {};
      interactions.forEach(function(item) {
        const chain = item.chain || "";
        const residue = item.residue_id;
        const selector = {model: model, resi: String(residue)};
        if (chain) selector.chain = chain;
        highlighted[chain + ":" + residue] = selector;
        viewer.setStyle(selector, {
          cartoon: {color: "0xff8c00", opacity: 1.0},
          stick: {color: "0xff8c00", radius: 0.22}
        });
        viewer.addLabel(
          String(item.residue || "RES") + " " + String(residue),
          {
            backgroundColor: "0xff8c00",
            backgroundOpacity: 0.78,
            fontColor: "0xffffff",
            fontSize: 12,
            borderThickness: 0.5,
            inFront: true
          },
          selector
        );
      });

      viewer.zoomTo({model: model});
      viewer.render();
    }

    function updateBox(cx, cy, cz, sx, sy, sz) {
      if (currentBox) { viewer.removeShape(currentBox); currentBox = null; }
      // Une seule forme filaire evite de recreer 12 cylindres WebGL a
      // chaque mouvement de slider ou de camera.
      currentBox = viewer.addBox({
        center: {x: cx, y: cy, z: cz},
        dimensions: {w: sx, h: sy, d: sz},
        color: "0xff0055",
        wireframe: true,
        lineWidth: 2.5,
        opacity: 1.0
      });

      viewer.render();
    }

    const POCKET_PALETTE = [
      "0x00bcd4", "0xe91e63", "0xff9800", "0x8bc34a",
      "0x9c27b0", "0xffc107", "0x00e676", "0xff5252",
      "0x536dfe", "0xffd740"
    ];

    function _addPocketVisual(pocketId) {
      // Cree effectivement la surface (ou la bulle de repli) pour une
      // poche marquee visible. N'agit pas sur pocketVisible lui-meme.
      const model = pocketModels[pocketId];
      const color = pocketColors[pocketId];
      if (model) {
        viewer.addSurface($3Dmol.SurfaceType.VDW, {
          opacity: 0.85,
          color: color
        }, {model: model});
      } else if (!pocketShapes[pocketId]) {
        const fb = pocketFallback[pocketId];
        pocketShapes[pocketId] = viewer.addSphere({
          center: {x: fb.center[0], y: fb.center[1], z: fb.center[2]},
          radius: fb.radius,
          color: color,
          opacity: 0.5
        });
      }
    }

    function _rebuildVisiblePockets() {
      // Toutes les surfaces sont recalculees d'un coup (plus simple et
      // plus fiable que de suivre un identifiant de surface individuel
      // au fil des affichages/masquages successifs).
      viewer.removeAllSurfaces();
      Object.keys(pocketVisible).forEach(function(pid) {
        if (pocketVisible[pid]) { _addPocketVisual(pid); }
      });
      viewer.render();
    }

    function clearPockets() {
      currentPockets.forEach(function(shape) { viewer.removeShape(shape); });
      currentPockets = [];
      Object.values(pocketModels).forEach(function(m) { if (m) viewer.removeModel(m); });
      Object.values(pocketShapes).forEach(function(s) { if (s) viewer.removeShape(s); });
      viewer.removeAllSurfaces();
      pocketModels = {};
      pocketColors = {};
      pocketFallback = {};
      pocketVisible = {};
      pocketShapes = {};
      viewer.render();
    }

    function updatePockets(pocketsJson) {
      clearPockets();
      const pockets = JSON.parse(pocketsJson);
      pockets.forEach(function(p, idx) {
        const color = POCKET_PALETTE[idx % POCKET_PALETTE.length];
        pocketColors[p.pocket_id] = color;
        pocketFallback[p.pocket_id] = {center: p.center, radius: p.radius};
        pocketModels[p.pocket_id] = p.alpha_spheres_pqr
          ? viewer.addModel(p.alpha_spheres_pqr, "pqr")
          : null;
        if (pocketModels[p.pocket_id]) {
          viewer.setStyle({model: pocketModels[p.pocket_id]}, {});
        }
        pocketVisible[p.pocket_id] = false;
      });
      // Par defaut, seule la meilleure poche (premiere de la liste,
      // deja triee par druggabilite) est affichee, pour ne pas
      // surcharger la vue -- les autres se cochent une par une
      // depuis le panneau de gauche.
      if (pockets.length > 0) {
        pocketVisible[pockets[0].pocket_id] = true;
      }
      _rebuildVisiblePockets();
    }

    function setPocketVisible(pocketId, visible) {
      if (!(pocketId in pocketVisible)) return;
      pocketVisible[pocketId] = visible;
      if (!visible && pocketShapes[pocketId]) {
        viewer.removeShape(pocketShapes[pocketId]);
        pocketShapes[pocketId] = null;
      }
      _rebuildVisiblePockets();
    }

    function showAllPockets() {
      Object.keys(pocketVisible).forEach(function(pid) { pocketVisible[pid] = true; });
      _rebuildVisiblePockets();
    }

    function hideAllPockets() {
      Object.keys(pocketVisible).forEach(function(pid) { pocketVisible[pid] = false; });
      Object.values(pocketShapes).forEach(function(s) { if (s) viewer.removeShape(s); });
      pocketShapes = {};
      _rebuildVisiblePockets();
    }

    function isolatePocket(pocketId) {
      // N'affiche que cette poche, masque toutes les autres, et
      // recadre la camera dessus : ideal pour une capture d'ecran
      // propre d'une seule cavite.
      Object.keys(pocketVisible).forEach(function(pid) {
        pocketVisible[pid] = (String(pid) === String(pocketId));
      });
      Object.values(pocketShapes).forEach(function(s) { if (s) viewer.removeShape(s); });
      pocketShapes = {};
      _rebuildVisiblePockets();
      const model = pocketModels[pocketId];
      if (model) {
        viewer.zoomTo({model: model});
        viewer.render();
      }
    }
  </script>
</body>
</html>
"""
