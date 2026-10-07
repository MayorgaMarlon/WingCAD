"""Headless regression checks: no QApplication or VTK initialization."""
import sys
import unittest
from pathlib import Path

import numpy as np
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from core.reference_airfoil import reference_sections, reference_contour, spacing
from core.parameters import WingParameters
from core.wing import WingBuilder
from OCP.BRepCheck import BRepCheck_Analyzer


class MatchedBenchmarkTests(unittest.TestCase):
    def test_sampling(self):
        upper, lower = reference_sections()
        self.assertEqual(reference_contour().shape, (48, 2))
        np.testing.assert_array_equal(upper[[0, -1]], lower[[0, -1]])
        self.assertTrue(np.all(np.diff(upper[:, 0]) > 0))
        self.assertTrue(np.all(np.diff(lower[:, 0]) > 0))
        widths = np.diff(spacing(1, 15, 10))
        self.assertAlmostEqual(widths[-1]/widths[0], 10)
        self.assertAlmostEqual(widths.sum(), 1)

    def test_fixed_profile_contract(self):
        with self.assertRaises(ValueError):
            WingParameters(perfil_raiz='RAE101F').validar()
        with self.assertRaises(ValueError):
            WingParameters(perfil_raiz='RAE101F', perfil_punta='RAE101F', numero_puntos=60).validar()

    def test_examples_build_without_graphics(self):
        from app.application import AeroApplication
        self.assertTrue(BRepCheck_Analyzer(WingBuilder(WingParameters()).construir()).IsValid())
        for filename in ('08_weber_swept_wing.wingcad', '09_weber_matched_reference.wingcad'):
            app = AeroApplication()
            app.abrir_proyecto(ROOT/'examples'/filename)
            self.assertTrue(BRepCheck_Analyzer(app.documento.objetos[0].shape).IsValid())
        self.assertFalse(any(m.startswith(('vtk', 'PySide6.QtWidgets', 'PyQt5.QtWidgets')) for m in sys.modules))


if __name__ == '__main__':
    unittest.main()
