"""Numerical and missing-field checks without creating a GUI."""
import unittest
from core.analysis_results import result_tables


class ResultTableTests(unittest.TestCase):
    def test_force_units_and_signed_coefficients(self):
        results, conditions = result_tables(dict(speed_mps=10., density_kg_m3=2.,
            sref_m2=3., CL=-.5, CD_inviscid=.1, panels=42))
        values = {label: (value, unit) for label, value, unit in results}
        self.assertEqual(values['Dynamic pressure'], (100., 'Pa'))
        self.assertEqual(values['Lift (CL × q × S)'], (-150., 'N'))
        self.assertEqual(values['Inviscid drag (CD × q × S)'], (30., 'N'))
        self.assertNotIn('Moment coefficient Cm', values)
        self.assertIn(('Surface panels', 42, ''), conditions)

    def test_missing_conditions_do_not_invent_forces(self):
        results, _ = result_tables({'CL': .2, 'Cm': -.01})
        self.assertEqual(results, [('Lift coefficient CL', .2, ''), ('Moment coefficient Cm', -.01, '')])


if __name__ == '__main__':
    unittest.main()
