"""Tests des règles de fenêtre, de seuil relatif et de cascade [rev. 2026-11]. Aucun réseau.

Lancer : python3 -m unittest discover -s code/tests (depuis la racine du dépôt)."""
import os, sys, unittest, datetime
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import meta_lib as m

class TestRegles2026_11(unittest.TestCase):
    def test_fenetre_min_plancher_3_jours(self):
        # 10 IC x 50$ / 400$/j = 1,25 j -> plancher de 3 jours
        self.assertEqual(m.fenetre_min("2026-11-01", 50, 400), 3.0)

    def test_fenetre_min_temps_pour_10_ic(self):
        # 10 x 50 / 100 = 5 j > 3
        self.assertEqual(m.fenetre_min("2026-11-01", 50, 100), 5.0)

    def test_fenetre_ecoulee(self):
        d = datetime.datetime(2026, 11, 1)
        self.assertFalse(m.fenetre_ecoulee(d, 50, 400, now=datetime.datetime(2026, 11, 3)))
        self.assertTrue(m.fenetre_ecoulee(d, 50, 400, now=datetime.datetime(2026, 11, 4)))

    def test_seuil_sous_2x_jamais(self):
        self.assertFalse(m.seuil_kill_relatif(50, 99, 0)[0])

    def test_seuil_palier1_zero_ic(self):
        self.assertTrue(m.seuil_kill_relatif(50, 100, 0)[0])

    def test_seuil_palier2(self):
        self.assertTrue(m.seuil_kill_relatif(50, 300, 3)[0])    # 100$/IC > 75, 300 >= 150
        self.assertFalse(m.seuil_kill_relatif(50, 140, 1)[0])   # < 3x cible depenses
        self.assertFalse(m.seuil_kill_relatif(50, 300, 5)[0])   # 60$/IC <= 75

    def test_cascade_plafond_pas_kill_quand_campagne_tient(self):
        camp = {"sp": 920, "ic": 23}
        adsets = {"S1": {"sp": 800, "ic": 23}}
        ads = {"A": {"sp": 300, "ic": 20}, "E": {"sp": 400, "ic": 3}}
        dec = {d["nom"]: d["action"] for d in m.evaluer_cascade(50, camp, adsets, ads, {"A": "S1", "E": "S1"})}
        self.assertEqual(dec["E"], "PLAFOND")

    def test_cascade_kill_si_campagne_rate(self):
        camp = {"sp": 1000, "ic": 4}   # 250$/IC
        ads = {"E": {"sp": 400, "ic": 3}, "B": {"sp": 120, "ic": 0}}
        dec = {d["nom"]: d["action"] for d in m.evaluer_cascade(50, camp, {}, ads, {})}
        self.assertEqual(dec["E"], "KILL")
        self.assertEqual(dec["B"], "KILL")

if __name__ == "__main__":
    unittest.main()
