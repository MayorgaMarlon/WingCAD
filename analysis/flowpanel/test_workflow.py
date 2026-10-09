"""Headless adapter routing and run-isolation regressions."""
import json
from pathlib import Path
import tempfile
import unittest

from core.flowpanel_workflow import ROOT, read_case, configure_run, solver_script, validate_weber_document


class WorkflowTests(unittest.TestCase):
    def make_case(self, folder, ordered):
        data=dict(units='m',panels=6144,speed_mps=30.,aoa_deg=4.2,density_kg_m3=1.225,sref_m2=1.239223328)
        if ordered:
            data.update(connected_root=True,triangulation='mirrored_shortest')
            data.pop('units')  # Existing historical Weber cases remain readable.
        names=('nodes_C.csv','cells_C.csv') if ordered else ('surface.msh','te_left.msh','te_right.msh')
        for name in names:(folder/name).write_text('fixture data')
        (folder/'case.toml').write_text(''.join(f'{k} = {json.dumps(v)}\n' for k,v in data.items()))
        return names

    def test_routing_and_isolated_runs(self):
        for ordered in (False,True):
            with self.subTest(ordered=ordered), tempfile.TemporaryDirectory() as tmp:
                folder=Path(tmp);names=self.make_case(folder,ordered)
                original=(folder/'case.toml').read_bytes()
                first=configure_run(folder,27.,3.,1.1)
                second=configure_run(folder,30.,4.2,1.225)
                self.assertNotEqual(first,second)
                self.assertEqual((folder/'case.toml').read_bytes(),original)
                cfg=read_case(first)
                self.assertEqual((cfg['speed_mps'],cfg['aoa_deg'],cfg['density_kg_m3']),(27.,3.,1.1))
                self.assertEqual(solver_script(cfg).name,'solve_ordered.jl' if ordered else 'solve.jl')
                for name in names:self.assertEqual((first/name).read_bytes(),(folder/name).read_bytes())

    def test_limits_and_missing_inputs(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp);self.make_case(folder,True)
            with self.assertRaises(ValueError):configure_run(folder,float('nan'),4.2,1.225)
            (folder/'cells_C.csv').unlink()
            with self.assertRaises(ValueError):read_case(folder)
        for ordered, panels in ((False,8001),(True,31105)):
            with self.subTest(ordered=ordered), tempfile.TemporaryDirectory() as tmp:
                folder=Path(tmp);self.make_case(folder,ordered)
                path=folder/'case.toml'
                path.write_text(path.read_text().replace('panels = 6144',f'panels = {panels}'))
                with self.assertRaisesRegex(ValueError,'panel limit'):
                    configure_run(folder,30.,4.2,1.225)

    def test_geometry_validation(self):
        doc=json.loads((ROOT/'examples/08_weber_swept_wing.wingcad').read_text())
        validate_weber_document(doc)
        doc['documento']['objetos'][0]['parametros']['cuerda_raiz_mm']=600
        with self.assertRaisesRegex(ValueError,'cuerda_raiz_mm'):validate_weber_document(doc)


if __name__=='__main__':unittest.main()
