import unittest

from PySide6.QtWidgets import QApplication, QWidget

from src.gui.main_window import VisualizationPage, _ViewerDragRepaintPoller


class ViewerDragRepaintPollerTests(unittest.TestCase):
    def test_poller_exists_and_targets_widget(self):
        app = QApplication.instance() or QApplication([])
        widget = QWidget()
        widget.resize(300, 200)
        widget.show()

        poller = _ViewerDragRepaintPoller(widget)

        self.assertIs(poller.viewer, widget)
        self.assertIsNotNone(poller.timer)
        self.assertTrue(poller.timer.isActive())

        app.processEvents()

    def test_viewer_template_exposes_refresh_function(self):
        from src.gui.viewer_template import VIEWER_HTML

        self.assertIn("function refreshViewer(resizeFirst)", VIEWER_HTML)
        self.assertIn("viewer.resize();", VIEWER_HTML)
        self.assertIn("viewer.render();", VIEWER_HTML)
        self.assertIn("function applyWheelZoom(factor)", VIEWER_HTML)
        self.assertIn("viewer.zoom(factor);", VIEWER_HTML)
        self.assertIn("function setManualInteractionControls(enabled)", VIEWER_HTML)
        self.assertIn("manualStep = Math.min(manualStep + 1, 10)", VIEWER_HTML)
        self.assertIn("manualControlsEnabled", VIEWER_HTML)
        self.assertIn("function setManualInteractionControls(enabled)", VIEWER_HTML)
        self.assertIn("manualStep = Math.min(manualStep + 1, 10)", VIEWER_HTML)
        self.assertIn("manualControlsEnabled", VIEWER_HTML)
        self.assertIn('event.preventDefault();', VIEWER_HTML)


class Interaction3DViewerScriptTests(unittest.TestCase):
    def test_interaction_3d_script_keeps_interactions_as_array(self):
        app = QApplication.instance() or QApplication([])
        page = VisualizationPage.__new__(VisualizationPage)

        script = page._interaction_3d_script("ATOM", [{"chain": "A", "residue_id": 10}])

        self.assertIn('loadComplex("ATOM", [{"chain": "A", "residue_id": 10}])', script)
        self.assertNotIn('"[{\\"chain\\": \\"A\\"', script)

        app.processEvents()


if __name__ == "__main__":
    unittest.main()
