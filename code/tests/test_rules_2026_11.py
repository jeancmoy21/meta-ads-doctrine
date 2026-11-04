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


class TestSurfEtFenetreObjet(unittest.TestCase):
    def setUp(self):
        import importlib.util
        # budget_drop s'execute a l'import seulement sous --surf ; on isole surf_delta.
        src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "budget_drop.py")).read()
        a = src.index("def surf_delta"); b = src.index("def _arg")
        ns = {}
        exec(src[a:b], ns)
        self.sd = ns["surf_delta"]

    def test_grille_cinq_cases_et_bornes(self):
        c = 100.0
        self.assertEqual(self.sd(c, 131), (-0.20, -0.10))   # > 1,30
        self.assertEqual(self.sd(c, 130), (0.0, 0.0))       # 1,30 inclus = tenir
        self.assertEqual(self.sd(c, 110), (0.0, 0.0))       # 1,10 inclus = tenir
        self.assertEqual(self.sd(c, 109), (0.10, 0.20))
        self.assertEqual(self.sd(c, 70), (0.10, 0.20))      # 0,70 inclus
        self.assertEqual(self.sd(c, 69), (0.20, 0.40))
        self.assertEqual(self.sd(c, 50), (0.20, 0.40))      # 0,50 inclus
        self.assertEqual(self.sd(c, 49), (0.50, 1.00))

    def test_pack_neuf_dans_campagne_qui_roule_aucun_kill(self):
        now = datetime.datetime(2026, 11, 21)
        lancement = datetime.datetime(2026, 11, 1)           # campagne a 20 jours
        neuf = now - datetime.timedelta(days=1)              # ad set cree il y a 1 jour
        fen = lambda c: m.fenetre_ecoulee(c, 50, 400, now=now)
        self.assertTrue(fen(lancement))
        self.assertFalse(fen(neuf))
        camp = {"sp": 920, "ic": 23}
        adsets = {"ANCIEN": {"sp": 700, "ic": 23}, "NEUF": {"sp": 120, "ic": 0}}
        ads = {"a1": {"sp": 100, "ic": 0}, "n1": {"sp": 120, "ic": 0}}
        fok = {("adset", "ANCIEN"): True, ("adset", "NEUF"): fen(neuf),
               ("ad", "a1"): True, ("ad", "n1"): fen(neuf)}
        dec = {(d["niveau"], d["nom"]): d["action"] for d in
               m.evaluer_cascade(50, camp, adsets, ads, {"a1": "ANCIEN", "n1": "NEUF"}, fenetre_ok=fok)}
        self.assertEqual(dec[("adset", "NEUF")], "TENIR")
        self.assertEqual(dec[("ad", "n1")], "TENIR")
        self.assertEqual(dec[("ad", "a1")], "KILL")

    def test_post_id_sans_go_aucun_post(self):
        r = m.create_ad_from_post("x", "1", "p_q")
        self.assertTrue(r["dry_run"])
        self.assertTrue(m.make_creative_from_post("x", "p_q")["dry_run"])

    def test_refus_enhancement_visuel(self):
        with self.assertRaises(ValueError):
            m.refuse_visual_enhancements({"creative_features_spec": {"image_touchups": {"enroll_status": "OPT_IN"}}})

    def test_optout_defaut_false_aucune_injection(self):
        self.assertEqual(m._dof_optout(False), {})
        self.assertIn("degrees_of_freedom_spec", m._dof_optout(True))


    def test_date_naive_et_created_time_aware_sans_typeerror(self):
        aware = datetime.datetime.fromisoformat("2026-11-04T21:30:00-05:00")
        now = datetime.datetime.fromisoformat("2026-11-05T21:30:00-05:00")
        self.assertFalse(m.fenetre_ecoulee("2026-11-04T21:30:00", 50, 400, now=now))   # naïve, 1 j
        self.assertTrue(m.fenetre_ecoulee("2026-11-01", 50, 400, now=now))
        self.assertFalse(m.fenetre_ecoulee(aware, 50, 400, now=datetime.datetime(2026, 11, 5, 21, 30)))


if __name__ == "__main__":
    unittest.main()
