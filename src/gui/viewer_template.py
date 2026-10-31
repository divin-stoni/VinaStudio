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
  <!-- Le premier domaine est historique ; le second évite une page blanche
       sur des réseaux Windows qui filtrent 3Dmol.org. Le chargement reste
       synchrone afin que $3Dmol existe avant le code du visualiseur. -->
  <script src="https://3Dmol.org/build/3Dmol-min.js"
          onerror="this.onerror=null;this.src='https://3dmol.csb.pitt.edu/build/3Dmol-min.js';"></script>
  <script src="qrc:///qtwebchannel/qwebchannel.js"></script>
  <style>
    html, body {
      margin: 0;
      background: #ffffff;
      width: 100%;
      height: 100%;
      min-height: 0;
      overflow: hidden;
    }
    #wrapper {
      position: relative;
      width: 100%;
      height: 100%;
      min-height: 0;
      overflow: hidden;
    }
    #container {
      width: 100%;
      height: 100%;
      min-height: 0;
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
    // Apparence : proteine d'une seule couleur, grid box epaisse.
    const PROTEIN_COLOR = "0x9aa4ae";
    const BOX_COLOR = "0xff0055";
    const BOX_EDGE_RADIUS = 0.22;
    let currentHighlight = null;
    let currentPockets = [];
    let pocketModels = {};   // pocket_id -> GLModel (ou null si pas de PQR)
    let pocketColors = {};   // pocket_id -> couleur
    let pocketFallback = {}; // pocket_id -> {center, radius} (repli bulle)
    let pocketVisible = {};  // pocket_id -> bool
    let pocketShapes = {};   // pocket_id -> shape (repli bulle affichee)
    let bridge = null;
    let manualControlsEnabled = false;
    let manualStep = 0;

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

    function refreshViewer(resizeFirst) {
      if (!viewer) return;
      if (resizeFirst !== false) {
        viewer.resize();
      }
      viewer.render();
    }

    function applyWheelZoom(factor) {
      if (!viewer || !factor) return;
      viewer.zoom(factor);
      viewer.render();
    }

    function setManualInteractionControls(enabled) {
      manualControlsEnabled = !!enabled;
      if (!manualControlsEnabled) {
        manualStep = 0;
      }
    }

    function loadReceptor(pdbData) {
      viewer.clear();
      currentBox = null;
      currentHighlight = null;

      viewer.addModel(pdbData, "pdb");

      // Ruban opaque, coloré par chaîne (pas de transparence globale --
      // seul le résidu survolé est mis en avant, voir plus bas).
      viewer.setStyle({}, {cartoon: {color: PROTEIN_COLOR, opacity: 1.0}});

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

    document.addEventListener("wheel", function(event) {
      if (!manualControlsEnabled) return;
      event.preventDefault();
      const delta = event.deltaY || event.wheelDelta || 0;
      if (!delta) return;
      const factor = delta > 0 ? 1.08 : 0.92;
      manualStep = Math.min(manualStep + 1, 10);
      applyWheelZoom(factor);
    }, {passive: false});

    function loadComplex(pdbData, interactionsInput) {
      viewer.clear();
      currentBox = null;
      currentHighlight = null;

      let interactions = [];
      try {
        if (Array.isArray(interactionsInput)) {
          interactions = interactionsInput;
        } else if (typeof interactionsInput === "string") {
          const parsed = JSON.parse(interactionsInput || "[]");
          interactions = Array.isArray(parsed) ? parsed : [];
        }
      } catch (error) {
        interactions = [];
      }

      const model = viewer.addModel(pdbData, "pdb");
      viewer.resize();
      viewer.setStyle({model: model, hetflag: false}, {
        cartoon: {
          color: (typeof PROTEIN_COLOR !== "undefined" ? PROTEIN_COLOR : "0xb4b9bf"),
          opacity: 1.0
        }
      });
      viewer.setStyle({model: model, hetflag: true}, {
        stick: {colorscheme: "Jmol", radius: 0.18}
      });

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

      viewer.resize();
      viewer.zoomTo({model: model});
      viewer.render();
      setTimeout(function() {
        viewer.resize();
        viewer.zoomTo({model: model});
        viewer.render();
      }, 50);
    }

    function updateBox(cx, cy, cz, sx, sy, sz) {
      if (currentBox) {
        currentBox.forEach(function(s) { viewer.removeShape(s); });
      }
      currentBox = [];
      const xs = [cx - sx / 2, cx + sx / 2];
      const ys = [cy - sy / 2, cy + sy / 2];
      const zs = [cz - sz / 2, cz + sz / 2];
      function edge(a, b) {
        currentBox.push(viewer.addCylinder({
          start: {x: a[0], y: a[1], z: a[2]},
          end: {x: b[0], y: b[1], z: b[2]},
          radius: BOX_EDGE_RADIUS,
          color: BOX_COLOR,
          fromCap: 1,
          toCap: 1
        }));
      }
      for (let j = 0; j < 2; j++) {
        for (let k = 0; k < 2; k++) {
          edge([xs[0], ys[j], zs[k]], [xs[1], ys[j], zs[k]]);
          edge([xs[j], ys[0], zs[k]], [xs[j], ys[1], zs[k]]);
          edge([xs[j], ys[k], zs[0]], [xs[j], ys[k], zs[1]]);
        }
      }
      viewer.render();
    }

    var _centerResShapes = [];
    var _centerResStyled = null;

    function clearCenterResidue() {
      try {
        _centerResShapes.forEach(function(s) {
          if (s && s.constructor && s.constructor.name === "Label") {
            viewer.removeLabel(s);
          } else {
            viewer.removeShape(s);
          }
        });
        if (_centerResStyled) {
          viewer.setStyle(_centerResStyled, {cartoon: {color: PROTEIN_COLOR, opacity: 1.0}});
        }
      } catch (e) {}
      _centerResShapes = [];
      _centerResStyled = null;
      viewer.render();
    }

    function highlightCenterResidue(chain, resi, resn) {
      clearCenterResidue();
      var sel = {resi: resi};
      if (chain && String(chain).trim() !== "") {
        sel.chain = String(chain).trim();
      }
      var atoms = viewer.selectedAtoms(sel);
      if (!atoms || atoms.length === 0) {
        return;
      }
      viewer.addStyle(sel, {
        stick: {color: "yellow", radius: 0.35},
        cartoon: {color: PROTEIN_COLOR, opacity: 1.0}
      });
      _centerResStyled = sel;

      var sx = 0, sy = 0, sz = 0;
      atoms.forEach(function(a) { sx += a.x; sy += a.y; sz += a.z; });
      var n = atoms.length;
      var pos = {x: sx / n, y: sy / n, z: sz / n};

      _centerResShapes.push(viewer.addSphere({
        center: pos,
        radius: 0.6,
        color: "yellow",
        opacity: 0.6
      }));
      var chainTxt = (sel.chain ? " (" + sel.chain + ")" : "");
      _centerResShapes.push(viewer.addLabel(
        (resn || atoms[0].resn || "") + " " + resi + chainTxt,
        {
          position: pos,
          backgroundColor: "black",
          backgroundOpacity: 0.75,
          fontColor: "white",
          fontSize: 14,
          showBackground: true,
          alignment: "bottomCenter"
        }
      ));
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
