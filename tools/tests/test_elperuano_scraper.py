"""Unit tests for the El Peruano scraper's deterministic stages (no network)."""

import io
import sys
import unittest
import urllib.error
from pathlib import Path


from tools.scrapers import elperuano_scraper as er  # noqa: E402
from tools.scrapers.common import elperuano_client as ec  # noqa: E402

FIXTURES = Path(__file__).resolve().parent / "fixtures"


class ParseSearchCardsTest(unittest.TestCase):
    """Against a real 2026-07-25 Normas Legales search page (first 4 result cards)."""

    def setUp(self):
        page = (FIXTURES / "elperuano_search_nl.html").read_text(encoding="utf-8")
        self.records = ec.parse_search_cards(page, "NL", "2026-07-25")

    def test_parses_every_card_with_all_fields(self):
        self.assertEqual(len(self.records), 4)
        for r in self.records:
            self.assertEqual(
                set(r),
                {"tipo", "numero", "sector", "rubro", "sumilla", "url", "fecha", "op", "tipo_pub"},
            )
            self.assertTrue(r["tipo"] and r["numero"] and r["sumilla"] and r["op"])
            self.assertRegex(r["op"], r"^\d+-\d+$")  # visor/dispositivo id
            self.assertEqual(r["fecha"], "2026-07-25")
            self.assertEqual(r["url"], f"https://busquedas.elperuano.pe/dispositivo/NL/{r['op']}")

    def test_reads_real_norma_fields(self):
        ley = next(r for r in self.records if r["tipo"] == "LEY")
        self.assertEqual(ley["numero"], "N° 32739")
        self.assertIn("escala remunerativa", ley["sumilla"])

    def test_empty_page_is_safe(self):
        self.assertEqual(
            ec.parse_search_cards("<html><body>sin resultados</body></html>", "NL", "2026-07-25"), [])


class MatcherIntegrationTest(unittest.TestCase):
    """The scraper matches norma text against the real committed commitment index."""

    def test_matched_ids_are_well_formed_commitments(self):
        from tools.scrapers.common import matcher
        ids = matcher.load_matcher().match("Autorizan la creación de unidades de flagrancia")
        self.assertTrue(ids, "a distinctive plan phrase should match at least one commitment")
        self.assertTrue(all(i.count(".") == 1 for i in ids))  # e.g. t1-1.C02

    def test_unrelated_norma_matches_nothing(self):
        from tools.scrapers.common import matcher
        self.assertEqual(
            matcher.load_matcher().match("Designan fedatarios institucionales de la intendencia regional"), [])


class NationalScopeTest(unittest.TestCase):
    """Subnational publishers (municipal/regional own-acts) are out of the review queue."""

    def test_municipal_and_regional_sectors_are_out_of_scope(self):
        for sector in ("MUNICIPALIDAD DE SAN LUIS", "Municipalidad de Ancón",
                       "GOBIERNO REGIONAL DE AMAZONAS", "gobierno regional del cusco"):
            self.assertFalse(er.in_national_scope({"sector": sector}), sector)

    def test_national_sectors_stay_in_scope(self):
        for sector in ("EDUCACIÓN", "COMERCIO EXTERIOR Y TURISMO", "AMBIENTE",
                       "", "SUPERINTENDENCIA NACIONAL DE SERVICIOS DE SANEAMIENTO"):
            self.assertTrue(er.in_national_scope({"sector": sector}), sector)


class ExecutiveScopeTest(unittest.TestCase):
    """Control and judicial own-acts can't evidence the executive's own plan."""

    def test_control_and_judicial_sectors_are_out_of_scope(self):
        # The publishers behind issues #231-#235: appointments, disciplinary
        # rulings and registry annexes, none of which the government executes.
        for sector in ("CONTRALORÍA GENERAL", "PODER JUDICIAL", "MINISTERIO PÚBLICO",
                       "CORTES SUPERIORES DE JUSTICIA", "CONSEJO EJECUTIVO DEL PODER JUDICIAL"):
            self.assertFalse(er.in_national_scope({"sector": sector}), sector)

    def test_an_autonomous_bodys_own_organs_are_out_of_scope(self):
        # Issue #271: the sector is the publisher's name, and an organ publishes
        # under its own, so an anchored match missed the Ministerio Público's
        # internal control authority — whose budget acts the gate exists to drop.
        self.assertFalse(er.in_national_scope(
            {"sector": "AUTORIDAD NACIONAL DE CONTROL DEL MINISTERIO PUBLICO"}))

    def test_statistical_and_electoral_bodies_stay_in_scope(self):
        # INEI publishes the statistics that measure the 65 metas 2031, so it has
        # to stay reachable; its monthly-index noise dies on the phrase gate instead.
        for sector in ("INSTITUTO NACIONAL DE ESTADÍSTICA E INFORMÁTICA",
                       "BANCO CENTRAL DE RESERVA", "JURADO NACIONAL DE ELECCIONES",
                       "REGISTRO NACIONAL DE IDENTIFICACIÓN Y ESTADO CIVIL"):
            self.assertTrue(er.in_national_scope({"sector": sector}), sector)


class RoutineActTest(unittest.TestCase):
    """Routine administration can't evidence a commitment, whoever publishes it."""

    # Verbatim sumillas from issues #246-#265: two consecutive queues that were
    # 20/20 false positives, which is what motivated the gate.
    PERSONNEL = (
        "Designan Presidente Ejecutivo del Organismo Técnico de la Administración "
        "de los Servicios de Saneamiento - OTASS",
        "Designan Jefe del Fondo Nacional de Desarrollo Pesquero - FONDEPES",
        "Aceptan renuncia de Jefa del Fondo Nacional de Desarrollo Pesquero - FONDEPES",
        "Designan Gerente General de la Autoridad Nacional del Agua",
        "Designan Subsecretaria I de la Subsecretaría de Simplificación y Análisis "
        "Regulatorio de la Secretaría de Gestión Pública de la PCM",
        "Designan Asesor II de la Dirección Ejecutiva del Programa Nacional de "
        "Infraestructura Educativa - PRONIED",
        "Designan Viceministro de Prestaciones y Aseguramiento en Salud",
        "Aceptan renuncia de Viceministro de Poblaciones Vulnerables",
        "Designan Presidente Ejecutivo de la Comisión de Promoción del Perú para la "
        "Exportación y el Turismo – PROMPERÚ",
        "Encargan funciones de Director de la Oficina General de Administración",
        "Dan por concluida la designación del Director de la Dirección General de Salud",
    )

    def test_individual_appointments_are_gated(self):
        for sumilla in self.PERSONNEL:
            self.assertTrue(er.is_routine_act({"sumilla": sumilla}), sumilla)

    def test_plural_personnel_acts_are_gated(self):
        # One resolution often retires and appoints several people at once, and
        # the first version of this gate was singular-only — `renuncia\b` cannot
        # match "renuncias", so issue #278 reached the queue while the singular
        # "Aceptan renuncia de Jefa del FONDEPES" above was correctly gated.
        for sumilla in (
            "Aceptan renuncias y designan funcionarios en diversos puestos de la "
            "Autoridad Nacional de Infraestructura",
            "Dan por concluidas las designaciones de asesores del Despacho Ministerial",
            "Dejan sin efecto las designaciones de directores de la Oficina General",
        ):
            self.assertTrue(er.is_routine_act({"sumilla": sumilla}), sumilla)

    def test_both_ends_of_a_posting_are_gated(self):
        # A rotation reaches the gazette twice, and the gate caught neither end:
        # the outgoing consul's funciones were terminated in issue #52 and the
        # incoming one was named in issue #289 — same post, same city, two
        # months apart, two false positives.
        for sumilla in (
            "Nombran Cónsul General del Perú en Orlando, Estados Unidos de América",
            "Dan por terminadas las funciones de Cónsul General del Perú en Orlando, "
            "Estados Unidos de América",
            "Dan por terminada designación de Jefe del Órgano de Control Institucional",
            "Nombran y designan fiscales en los Distritos Judiciales de Lima Centro",
        ):
            self.assertTrue(er.is_routine_act({"sumilla": sumilla}), sumilla)

    def test_delegating_signing_authority_to_staff_is_gated(self):
        for sumilla in (
            "Delegan facultades a servidores de la Oficina de Normalización "
            "Previsional durante el Año Fiscal 2026",
            "Delegan facultades a servidores de la Oficina de Normalización "
            "Previsional en materia de contrataciones del Estado",
        ):
            self.assertTrue(er.is_routine_act({"sumilla": sumilla}), sumilla)

    def test_delegating_legislative_power_stays_in_the_queue(self):
        # "Delegan facultades" is also how Congress hands its legislative power
        # to the Executive — the single most consequential act the gazette
        # carries. The gate only fires when the delegation runs *down* to an
        # entity's own staff.
        for sumilla in (
            "Delegan facultades legislativas al Poder Ejecutivo en materia de "
            "seguridad ciudadana",
            "Ley que delega facultades al Poder Ejecutivo para legislar en materia "
            "tributaria",
        ):
            self.assertFalse(er.is_routine_act({"sumilla": sumilla}), sumilla)

    def test_concluding_a_regime_is_not_a_personnel_act(self):
        # Issue #271: "dan por concluido" governs a *Régimen*, not a designación.
        # Widening the verb without anchoring its object would gate a real act.
        self.assertFalse(er.is_routine_act({"sumilla":
            "Dan por concluido el Régimen de Contingencia y Racionalización "
            "Extrema de Recursos en la Unidad Ejecutora"}))

    def test_designating_a_task_body_stays_in_the_queue(self):
        # Naming the body that will execute a commitment is a real signal.
        for sumilla in (
            "Designan a los integrantes de la Comisión Multisectorial encargada de "
            "la seguridad alimentaria",
            "Designan miembros del Grupo de Trabajo para el cierre de brechas de agua",
            "Designan integrantes de la Mesa de Trabajo para la formalización minera",
        ):
            self.assertFalse(er.is_routine_act({"sumilla": sumilla}), sumilla)

    def test_a_standing_body_is_not_a_task_body(self):
        # Issue #285: CONADIS's permanent "Comisión Consultiva" matched *both*
        # halves — "miembros" and a bare "comisión" — and slipped through, the
        # same way the BCRP Directorio did on "miembros" alone. A comisión or
        # comité only counts when it was convened to do something.
        for sumilla in (
            "Proclaman miembros de la Comisión Consultiva del Consejo Nacional para "
            "la Integración de la Persona con Discapacidad - Conadis",
            "Designan representantes ante la Comisión Permanente de Estadística",
        ):
            self.assertTrue(er.is_routine_act({"sumilla": sumilla}), sumilla)

    def test_a_tasked_comision_still_stays_in_the_queue(self):
        self.assertFalse(er.is_routine_act({"sumilla":
            "Proclaman integrantes de la Comisión encargada de implementar el Plan "
            "Nacional de Agua"}))

    def test_the_exception_needs_both_halves(self):
        # A collective noun alone is not enough: appointing to a standing board is
        # ordinary churn, and "miembros" alone let issue #268 through. A task body
        # alone is not enough either — PROMPERÚ's registered name *is* "Comisión de
        # Promoción del Perú…", so a bare "comisión" test waves an appointment past.
        for sumilla in (
            "Designan miembros del Directorio del Banco Central de Reserva del Perú, "
            "en representación del Poder Ejecutivo",
            "Designan representantes ante el Consejo Nacional de Educación",
            "Designan Presidente Ejecutivo de la Comisión de Promoción del Perú para "
            "la Exportación y el Turismo – PROMPERÚ",
        ):
            self.assertTrue(er.is_routine_act({"sumilla": sumilla}), sumilla)

    def test_drafts_out_for_comment_are_gated(self):
        # A text still in consulta is not in force, so it cannot evidence a
        # commitment — and the same instrument returns as its own candidate when
        # it is finally enacted. Issues #295, #302, #303 in one day.
        for sumilla in (
            "Disponen la prepublicación de la Resolución de Dirección Ejecutiva que "
            "modifica los “Lineamientos para la Inscripción de Plantaciones”",
            "Autorizan la difusión en consulta pública del proyecto normativo que "
            "aprueba la Norma que establece los Lineamientos aplicables a los "
            "productos de seguros",
            "Resolución de Consejo Directivo con la que se dispone la publicación del "
            "Proyecto de fijación del Valor Nuevo de Reemplazo (VNR)",
            "Disponen la publicación de proyecto de “Decreto Supremo que modifica el "
            "Reglamento Técnico sobre etiquetado”",
        ):
            self.assertTrue(er.is_routine_act({"sumilla": sumilla}), sumilla)

    def test_the_enacted_version_still_reaches_the_queue(self):
        # The gate must catch the draft and miss the norm it becomes.
        for sumilla in (
            "Decreto Supremo que aprueba el Reglamento Técnico sobre etiquetado",
            "Aprueban los Lineamientos para la Inscripción de Plantaciones en el "
            "Registro Nacional",
        ):
            self.assertFalse(er.is_routine_act({"sumilla": sumilla}), sumilla)

    def test_heritage_declarations_are_gated(self):
        for sumilla in (
            "Declaran Patrimonio Cultural de la Nación el Libro de Actas del Cabildo "
            "de la ciudad de Huamanga (1808 – 1810)",
            "Declaran Patrimonio Cultural de la Nación los “Bonos de reconocimiento de "
            "la deuda agraria peruana, emitidos entre 1974 y 1976”",
        ):
            self.assertTrue(er.is_routine_act({"sumilla": sumilla}), sumilla)

    def test_hazard_emergencies_are_gated_but_security_ones_are_not(self):
        # t1-1.P18 promises a Plan de Emergencia against inseguridad ciudadana, so
        # "estado de emergencia" cannot be gated as a phrase — only the Ley 29664
        # hazard formula (issue #301, déficit hídrico in sixteen departments).
        self.assertTrue(er.is_routine_act({"sumilla":
            "Decreto Supremo que declara el Estado de Emergencia en varios distritos "
            "de algunas provincias de los departamentos de Apurímac, Arequipa y Cusco, "
            "por peligro inminente ante déficit hídrico para el período de lluvias "
            "2026-2027"}))
        for sumilla in (
            "Decreto Supremo que declara el Estado de Emergencia en distritos de la "
            "provincia de Trujillo por el incremento de la criminalidad y la "
            "extorsión",
            "Prorrogan el Estado de Emergencia declarado en la Región Policial de "
            "Lima por inseguridad ciudadana",
        ):
            self.assertFalse(er.is_routine_act({"sumilla": sumilla}), sumilla)

    def test_academic_paperwork_is_gated(self):
        self.assertTrue(er.is_routine_act({"sumilla":
            "Autorizan duplicado de diploma de grado académico de maestro en ciencias "
            "de la educación de la Universidad Nacional de Educación Enrique Guzmán y "
            "Valle"}))

    def test_accrediting_representatives_is_personnel_churn(self):
        # Issue #296: a standing tripartite council swapping its union and CONFIEP
        # delegates. `representantes` alone never earns the task-body exception.
        self.assertTrue(er.is_routine_act({"sumilla":
            "Acreditan designaciones de representantes de la CATP, CGTP, CTP y CONFIEP "
            "ante el Consejo Nacional de Seguridad y Salud en el Trabajo"}))

    def test_extraditions_are_gated(self):
        # The most frequent class left — 22 in the first month of archive — and
        # no commitment in the plan mentions extradition at all.
        for sumilla in (
            "Acceden a solicitud de extradición activa de ciudadana de nacionalidad "
            "peruana para ser extraditada de la República de Chile",
            "Acceden a solicitud de extradición pasiva con procedimiento simplificado "
            "de entrega de ciudadano peruano y estadounidense",
        ):
            self.assertTrue(er.is_routine_act({"sumilla": sumilla}), sumilla)

    def test_regulator_adjudications_are_gated(self):
        for sumilla in (
            "Declaran barreras burocráticas ilegales los Procedimientos PA48001840 y "
            "PA48002D44 del TUPA de la SUNEDU",
            "Declaran barrera burocrática ilegal la exigencia de contar con un acta",
            "Aprueban el Mandato de Compartición de Infraestructura entre Easynet "
            "Conectividad Total S.A.C. y la Empresa Regional de Servicio Público",
        ):
            self.assertTrue(er.is_routine_act({"sumilla": sumilla}), sumilla)

    def test_granting_indecopi_new_powers_stays_in_the_queue(self):
        # t1-3.P10 promises to reinforce INDECOPI's barreras-burocráticas role by
        # *granting it powers*. A resolution declaring one barrier illegal is the
        # body using powers it already has; the reform that would fulfil P10
        # arrives as a Decreto Legislativo and must not be gated with it.
        for sumilla in (
            "Decreto Legislativo que otorga a INDECOPI facultades de supervisión "
            "preventiva y auditorías aleatorias en materia de barreras burocráticas",
            "Ley que refuerza el rol de INDECOPI en la eliminación de barreras "
            "burocráticas",
        ):
            self.assertFalse(er.is_routine_act({"sumilla": sumilla}), sumilla)

    def test_travel_and_academic_authorizations_are_gated(self):
        for sumilla in (
            "Ratifican resolución que aprueba estancia académica en Portugal de "
            "estudiantes y docente en calidad de tutor",
            "Autorizan viaje de profesionales del Ministerio de Salud a Colombia",
            "Autorizan el viaje al exterior de servidores del INDECOPI",
        ):
            self.assertTrue(er.is_routine_act({"sumilla": sumilla}), sumilla)

    def test_recurring_index_publications_are_gated(self):
        for sumilla in (
            "Índice de reajuste diario a que se refiere el artículo 240º de la Ley "
            "General del Sistema Financiero, correspondiente al mes de agosto de 2026",
            "Tipo de cambio promedio ponderado venta correspondiente a julio de 2026",
        ):
            self.assertTrue(er.is_routine_act({"sumilla": sumilla}), sumilla)

    def test_periodic_series_are_gated(self):
        # Calendar publications carrying no policy. INEI's monthly construction
        # factors matched ten commitments across nine temas (issue #333), and a
        # single new district triggers a canon recalculation (issue #332).
        for sumilla in (
            "Aprueban Factores de Reajuste que debe aplicarse a las obras de "
            "edificación, correspondiente a las trece (13) Áreas Geográficas para las "
            "Obras del Sector Privado, producidas en el mes de julio de 2026",
            "Modifican los Índices de Distribución del Canon Hidroenergético "
            "proveniente del Impuesto a la Renta correspondiente al Ejercicio Fiscal "
            "2025, por la creación de un nuevo distrito",
            "Resolución Ministerial que aprueba los Índices de Distribución del Canon "
            "Minero complementario",
        ):
            self.assertTrue(er.is_routine_act({"sumilla": sumilla}), sumilla)

    def test_a_canon_reform_stays_in_the_queue(self):
        # t2-2.P17 promises "Canon para el Pueblo" — up to 40% redistributed to the
        # extraction zone. That changes the rule; the gated resolutions only apply
        # the rule that already exists.
        for sumilla in (
            "Ley que modifica la Ley del Canon para redistribuir hasta el 40% a la "
            "población de la zona de extracción",
            "Decreto Supremo que aprueba el Reglamento del Canon para el Pueblo",
        ):
            self.assertFalse(er.is_routine_act({"sumilla": sumilla}), sumilla)

    def test_substantive_norms_are_untouched(self):
        for sumilla in (
            "Aprueban el Reglamento de la Ley que crea las unidades de flagrancia",
            "Decreto Supremo que aprueba la Política Nacional de Seguridad Alimentaria",
            "Crean el Programa Nacional de Infraestructura Educativa rural",
            "Modifican el Reglamento de la Ley General de Pesca",
            "",
        ):
            self.assertFalse(er.is_routine_act({"sumilla": sumilla}), sumilla)


class VocabularyGapTest(unittest.TestCase):
    """The plan and the gazette name the same instrument differently."""

    NEC = ("RESOLUCIÓN MINISTERIAL N° 000243-2026-PRODUCE Autorizan Transferencia "
           "Financiera a favor del Núcleo Ejecutor de Compras (NEC) para el sector "
           "productivo de Textil - confecciones")

    def test_a_compras_myperu_transfer_reaches_its_mype_commitment(self):
        # Issue #269. The plan writes "Compras MyPerú", El Peruano writes "Núcleo
        # Ejecutor de Compras", so the norma that funds the commitment shared no
        # bigram with it and was filed against a *schooling* commitment instead,
        # on the generic "sector productivo". Precision noise was hiding a recall
        # bug: the queue had the right norma under the wrong compromiso.
        #
        # Only P22. The NEC regime buys for whichever entity requests it — this
        # one clothes RENIEC staff — so tagging every transfer with P30 ("compras
        # de los *programas sociales*") would mis-attribute most of them.
        from tools.scrapers.common import matcher
        hits = matcher.load_matcher().match(self.NEC)
        self.assertIn("t2-1.P22", hits)      # Compras MyPerú as a permanent state policy
        self.assertNotIn("t2-1.P30", hits)   # not social-program procurement


class NormaRecordTest(unittest.TestCase):
    """Boletín Oficial section headings arrive shaped like records but aren't normas."""

    def test_headings_without_a_sumilla_are_dropped(self):
        # Issue #272: with no sumilla the matcher sees only the tipo, which is a
        # section name, and matches on whatever topic words it happens to contain.
        for tipo in ("Balance Por Entidades Financieras",
                     "Estudios Ambientales (suelo, agua, ruido, eléctricidad, entre otros)"):
            self.assertFalse(er.is_norma_record({"tipo": tipo, "numero": "", "sumilla": ""}), tipo)

    def test_real_normas_are_kept(self):
        self.assertTrue(er.is_norma_record(
            {"tipo": "RESOLUCIÓN MINISTERIAL", "numero": "266-2026-PCM",
             "sumilla": "Aprueban el Reglamento de la Ley que crea las unidades de flagrancia"}))


class NoiseSuppressionTest(unittest.TestCase):
    """Generic bigrams that flooded the queue are suppressed; real signal survives."""

    def setUp(self):
        from tools.scrapers.common import matcher
        self.m = matcher.load_matcher()

    def test_generic_bigrams_no_longer_match(self):
        # Real 2026-07-31 false-positive sumillas that matched only via a generic bigram.
        sumillas = [
            "Aprueban la Sección Segunda del Reglamento de Organización y Funciones del "
            "Servicio Nacional de Meteorología e Hidrología del Perú (SENAMHI)",
            "Aprueban transferencia financiera a favor del Gobierno Regional del "
            "Departamento de Amazonas, para el financiamiento exclusivo de la contrapartida "
            "nacional de diversos proyectos de inversión",
            "Designan Coordinador de las Fiscalías Superiores Penales Nacionales y Fiscalías "
            "Penales Supraprovinciales Especializadas en Derechos Humanos y contra el Terrorismo",
            "Designan Jefa de la Oficina General de Recursos Humanos",
        ]
        for sumilla in sumillas:
            self.assertEqual(self.m.match(sumilla), [], sumilla)

    def test_internal_administrative_instruments_no_longer_match(self):
        # Real 2026-08-07 false positives (issues #275-#277). ROF updates, tarifarios
        # and budget-programme boilerplate matched on wording that belongs to the
        # instrument, not the subject: an ROF update hit a commitment about the
        # *baggage* regulation, a library fee schedule sprayed across five temas.
        for sumilla in (
            "Aprueban actualización del Reglamento de Organización y Funciones (ROF) "
            "de la Universidad Nacional del Callao",
            "Aprueban el documento consolidado del “Tarifario Único de los Servicios No "
            "Prestados en Exclusividad de la Biblioteca Nacional del Perú”",
        ):
            self.assertEqual(self.m.match(sumilla), [], sumilla)

    def test_real_signal_still_matches(self):
        # The distinctive phrase of each affected commitment must still fire.
        self.assertIn("t2-1.P21", self.m.match(
            "Creación del Servicio Nacional de Defensa Jurídica del Emprendedor para "
            "jóvenes emprendedores y MYPES"))
        self.assertIn("t1-4.P01", self.m.match(
            "Modernización del sistema meritocrático liderado por SERVIR"))
        # Suppressing "programa presupuestal" must not blind the two commitments
        # that carry it — each keeps a dozen subject-matter phrases.
        self.assertIn("t3-1.P02", self.m.match(
            "Aprueban el tamizaje para la identificación de retrasos en el desarrollo "
            "infantil temprano"))
        self.assertIn("t3-2.P29", self.m.match(
            "Creación de la Red Escolar Digital de Lectura Perú Lee para mejorar la "
            "comprensión lectora"))


class NormaTextTest(unittest.TestCase):
    """Against a captured /dispositivo/ page embedding R.M. N° 419-2026-MTC (Hoja de Ruta)."""

    def test_extracts_clean_single_norma_body(self):
        page = (FIXTURES / "elperuano_dispositivo_2538172-1.html").read_bytes()
        text = ec.html_to_text(ec.extract_visor_html(page))
        self.assertIn("Hoja de Ruta", text)   # this norma's body
        self.assertIn("Que,", text)            # considerandos, not just metadata
        self.assertNotIn("Pataz", text)        # neighboring norma's <title> — <head> stripped
        self.assertNotIn("<", text)            # tags stripped
        self.assertGreater(len(text), 3000)


def _fake_search_page(n: int, base_op: int = 1000) -> str:
    card = (
        '<div class="rounded-xl border bg-card">'
        '<p class="text-sm font-semibold text-primary">SECTOR</p>'
        '<a href="/dispositivo/NL/{op}-1">'
        '<p class="text-xs text-muted-foreground">LEY</p>'
        '<p class="text-xs font-medium text-muted-foreground">N° {op}</p></a>'
        '<a class="line-clamp-3" href="/dispositivo/NL/{op}-1">sumilla {op}</a></div>'
    )
    return "<html><body>" + "".join(card.format(op=base_op + i) for i in range(n)) + "</body></html>"


def _http_error(url: str, code: int) -> urllib.error.HTTPError:
    return urllib.error.HTTPError(url, code, "boom", {}, io.BytesIO(b""))


class DraftNoteTest(unittest.TestCase):
    """The evidence note ships with a draft (the sumilla), never blank."""

    def test_uses_the_sumilla_as_the_draft(self):
        rec = {"tipo": "LEY", "numero": "N° 1", "fecha": "2026-07-28",
               "sumilla": "Ley que crea el registro nacional"}
        self.assertEqual(draft_note := er.draft_note(rec), "Ley que crea el registro nacional.")
        self.assertTrue(draft_note)  # non-blank

    def test_keeps_an_existing_final_period(self):
        rec = {"tipo": "LEY", "numero": "N° 1", "fecha": "2026-07-28", "sumilla": "Aprueban el reglamento."}
        self.assertEqual(er.draft_note(rec), "Aprueban el reglamento.")

    def test_falls_back_when_sumilla_is_empty(self):
        rec = {"tipo": "DECRETO SUPREMO", "numero": "N° 5-2026", "fecha": "2026-07-28", "sumilla": "  "}
        note = er.draft_note(rec)
        self.assertTrue(note)  # never blank
        self.assertIn("DECRETO SUPREMO N° 5-2026", note)

    def test_issue_body_evidence_note_is_never_blank(self):
        rec = {"tipo": "LEY", "numero": "N° 9", "sector": "PCM", "fecha": "2026-07-28",
               "sumilla": "Ley que reforma el sistema",
               "url": "https://busquedas.elperuano.pe/dispositivo/NL/1-1"}
        body = er.issue_body(rec, ["t1-1.P01"], "2026-07-28", excerpt="")
        self.assertIn('"note": "Ley que reforma el sistema."', body)
        self.assertNotIn('"note": ""', body)


class FetchNormasTest(unittest.TestCase):
    """Pagination + transient-error handling, with http_get stubbed (no network)."""

    def setUp(self):
        self._orig_get, self._orig_sleep = ec.http_get, ec.time.sleep
        ec.time.sleep = lambda *a, **k: None  # no real backoff waits

    def tearDown(self):
        ec.http_get, ec.time.sleep = self._orig_get, self._orig_sleep

    def test_pagination_tail_404_ends_the_edition(self):
        def fake(url):
            if "tipoPublicacion=NL" in url and "start=0" in url:
                return _fake_search_page(ec.PAGE_SIZE, 2000).encode()
            if "tipoPublicacion=NL" in url and "start=20" in url:
                raise _http_error(url, 404)  # past the last NL page
            return _fake_search_page(0).encode()  # BO/PC empty
        ec.http_get = fake
        self.assertEqual(len(ec.fetch_normas("20260101", "2026-01-01")), ec.PAGE_SIZE)

    def test_transient_error_is_retried(self):
        calls = {"n": 0}

        def flaky(url):
            if "tipoPublicacion=NL" in url and "start=0" in url:
                calls["n"] += 1
                if calls["n"] == 1:
                    raise _http_error(url, 404)  # one transient blip
                return _fake_search_page(3, 3000).encode()  # then a short page => NL ends
            return _fake_search_page(0).encode()
        ec.http_get = flaky
        records = ec.fetch_normas("20260101", "2026-01-01")
        self.assertEqual(calls["n"], 2)          # retried once, then succeeded
        self.assertEqual(len(records), 3)

    def test_first_page_404_still_raises(self):
        # a 404 on page 0 is not a pagination tail — it must fail loudly
        ec.http_get = lambda url: (_ for _ in ()).throw(_http_error(url, 404))
        with self.assertRaises(urllib.error.HTTPError):
            ec.fetch_normas("20260101", "2026-01-01")


if __name__ == "__main__":
    unittest.main()


class ExtraordinaryEditionTest(unittest.TestCase):
    """A change of government runs in the Edición Extraordinaria, not Normas Legales.

    Against the real EX search page of 2026-07-28 (page 0 of the day Keiko's
    cabinet was sworn in). NL that day carried five records; EX carried the
    whole cabinet. While TIPOS_PUBLICACION was ("NL", "BO", "PC") the sweep
    read a gazette that had published 19 nombramientos and reported none.
    """

    def setUp(self):
        page = (FIXTURES / "elperuano_search_ex_20260728.html").read_text(encoding="utf-8")
        self.records = ec.parse_search_cards(page, "EX", "2026-07-28")

    def test_the_sweep_reads_the_extraordinary_edition(self):
        self.assertIn("EX", ec.TIPOS_PUBLICACION)

    def test_the_edition_parses_like_any_other(self):
        self.assertEqual(len(self.records), 20)
        for r in self.records:
            self.assertTrue(r["tipo"] and r["numero"] and r["sumilla"])
            self.assertEqual(r["fecha"], "2026-07-28")
            self.assertEqual(r["url"], f"https://busquedas.elperuano.pe/dispositivo/EX/{r['op']}")

    def test_every_card_on_the_page_is_a_cabinet_act(self):
        from tools.scrapers.common.cabinet_rules import is_cabinet_norma
        self.assertTrue(all(is_cabinet_norma(r) for r in self.records))

    def test_carries_the_pcm_appointment(self):
        pcm = next(r for r in self.records
                   if "Presidente del Consejo de Ministros" in r["sumilla"]
                   and r["sumilla"].startswith("Nombran"))
        self.assertEqual(pcm["numero"], "N° 223-2026-PCM")
        self.assertEqual(pcm["tipo"], "RESOLUCIÓN SUPREMA")


class RequestPacingTest(unittest.TestCase):
    """Gazette requests are paced, or the site throttles a sweep into silence."""

    def setUp(self):
        self.real_get, self.real_sleep = ec.http_get, ec.time.sleep
        self.slept = []
        ec.http_get = lambda url, headers=None: b"<html></html>"
        ec.time.sleep = self.slept.append
        ec._last_request = 0.0

    def tearDown(self):
        ec.http_get, ec.time.sleep = self.real_get, self.real_sleep
        ec._last_request = 0.0

    def test_back_to_back_requests_wait(self):
        ec._throttled_get("https://example.test/a")
        self.slept.clear()
        ec._throttled_get("https://example.test/b")
        self.assertTrue(self.slept, "second request went out with no delay")
        self.assertLessEqual(max(self.slept), ec.REQUEST_DELAY)

    def test_norma_text_is_paced_too(self):
        """The /dispositivo/ fetch is one request per norma -- the bulk of a sweep."""
        ec._throttled_get("https://example.test/a")
        self.slept.clear()
        ec.norma_text({"url": "https://example.test/n", "sumilla": "x", "numero": "1"})
        self.assertTrue(self.slept, "norma_text bypassed the pacing")


class NormaTextRetryTest(unittest.TestCase):
    """A norma body gets the same retries a search page does."""

    def setUp(self):
        self.real_get, self.real_sleep = ec.http_get, ec.time.sleep
        ec.time.sleep = lambda _s: None
        ec._last_request = 0.0

    def tearDown(self):
        ec.http_get, ec.time.sleep = self.real_get, self.real_sleep
        ec._last_request = 0.0

    def test_a_transient_failure_does_not_lose_the_body(self):
        calls = []
        body = b'<div id="visor-html"><html><body>Nombran a Fulano de Tal</body></html></div>'

        def flaky(url, headers=None):
            calls.append(url)
            if len(calls) < 3:
                raise urllib.error.URLError("simulated reset")
            return body

        ec.http_get = flaky
        text = ec.norma_text({"url": "https://example.test/n", "sumilla": "Nombran", "numero": "1"})
        self.assertEqual(len(calls), 3)
        self.assertIn("Fulano de Tal", text)

    def test_persistent_failure_still_falls_back_to_the_sumilla(self):
        ec.http_get = lambda url, headers=None: (_ for _ in ()).throw(urllib.error.URLError("down"))
        text = ec.norma_text({"url": "https://example.test/n", "sumilla": "Nombran Ministro", "numero": "1"})
        self.assertEqual(text, "Nombran Ministro")


class InlineTagWordSplitTest(unittest.TestCase):
    """A word broken across styling spans must come back whole.

    Real rendition of R.S. 211-2026-PCM, where the gazette emits
    "…Riego, f</span><span>ormula el señor…". Turning every tag into a space
    gave "f ormula", and _BODY_RESIGN -- which needs that verb -- read the
    norma as unparseable. Two resignations in the 2026-07-28 cabinet edition
    were lost to it.
    """

    def setUp(self):
        self.raw = (FIXTURES / "visor_html_2538522-8.html").read_bytes()

    def test_the_fixture_still_contains_the_split(self):
        """Guards the guard: pointless test if the gazette markup were clean."""
        self.assertIn(b"f</span>", self.raw)

    def test_the_word_survives_extraction(self):
        text = ec.html_to_text(self.raw)
        self.assertNotIn("f ormula", text)
        self.assertIn("formula el señor Felipe César Meza Millán", text)

    def test_block_tags_still_separate_words(self):
        text = ec.html_to_text(b"<p>Ministro de Salud</p><p>Lima, 28 de julio</p>")
        self.assertIn("Salud Lima", text)

    def test_the_resignation_now_parses(self):
        from tools.scrapers.common.cabinet_rules import parse_cabinet_act
        record = {
            "tipo": "RESOLUCIÓN SUPREMA", "numero": "N° 211-2026-PCM",
            "sumilla": "Aceptan renuncia de Ministro de Desarrollo Agrario y Riego",
            "url": "https://busquedas.elperuano.pe/dispositivo/EX/2538522-8",
            "fecha": "2026-07-28", "op": "2538522-8",
        }
        act = parse_cabinet_act(record, ec.html_to_text(self.raw))
        self.assertEqual(act["action"], "renuncia")
        self.assertEqual(act["person"], "Felipe César Meza Millán")
        self.assertEqual(act["portfolio"], "m-agrario")
