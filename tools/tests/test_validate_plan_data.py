"""Integrity rules for the measurement series in tracking.json.

A quantitative commitment ("presupuesto anual mínimo de S/ 1 000 millones") is
never answered by fulfilled/no_progress — it is answered by adding up the year's
transfers. These rules exist so a series cannot quietly become unusable: a point
without a number, a number that is really a boolean, or a series hung off an id
the plan does not contain would each corrupt the arithmetic without failing
anything downstream.
"""
import copy
import unittest

from tools.plan.validate_plan_data import validate_measurements  # noqa: E402

KNOWN = {"t2-1.P22", "t1-1.M01"}

POINT = {
    "date": "2026-08-06",
    "value": 7360112.76,
    "source": "El Peruano — RESOLUCIÓN MINISTERIAL N° 000243-2026-PRODUCE",
    "url": "https://busquedas.elperuano.pe/dispositivo/NL/2540898-1",
    "note": "Transferencia al NEC Textil-confecciones.",
}

SERIES = {"unit": "PEN", "target": 1_000_000_000, "period": "2026", "points": [POINT]}


def data(series=None, cid="t2-1.P22"):
    return {"measurements": {cid: copy.deepcopy(series if series is not None else SERIES)}}


def with_point(**overrides):
    point = copy.deepcopy(POINT)
    point.update(overrides)
    series = copy.deepcopy(SERIES)
    series["points"] = [point]
    return data(series)


def with_series(**overrides):
    series = copy.deepcopy(SERIES)
    series.update(overrides)
    return data(series)


class MeasurementsTest(unittest.TestCase):
    def assertRejected(self, payload):
        with self.assertRaises(SystemExit):
            validate_measurements(payload, KNOWN)

    def test_a_well_formed_series_passes(self):
        validate_measurements(data(), KNOWN)

    def test_absent_measurements_are_fine(self):
        # The key is optional: most commitments are not quantitative.
        validate_measurements({"items": {}, "log": []}, KNOWN)

    def test_the_id_must_exist_in_the_plan(self):
        self.assertRejected(data(cid="t9-9.P99"))

    def test_a_point_needs_a_number(self):
        self.assertRejected(with_point(value="7360112.76"))

    def test_a_boolean_is_not_a_value(self):
        # bool is an int in Python, so a bare isinstance check would let True
        # through and silently add 1 to the year's total.
        self.assertRejected(with_point(value=True))

    def test_a_point_needs_a_date_and_a_source(self):
        self.assertRejected(with_point(date="6 de agosto"))
        broken = copy.deepcopy(SERIES)
        broken["points"] = [{k: v for k, v in POINT.items() if k != "source"}]
        self.assertRejected(data(broken))

    def test_a_url_must_be_http(self):
        self.assertRejected(with_point(url="/dispositivo/NL/2540898-1"))

    def test_a_series_needs_a_unit_and_at_least_one_point(self):
        self.assertRejected(with_series(unit=""))
        self.assertRejected(with_series(points=[]))

    def test_a_target_must_be_a_positive_number(self):
        self.assertRejected(with_series(target=0))
        self.assertRejected(with_series(target="1000 millones"))

    def test_unknown_keys_are_rejected(self):
        # A typo'd key is worse than a missing one: it reads as recorded data.
        self.assertRejected(with_series(targt=1_000_000_000))
        self.assertRejected(with_point(valor=7360112.76))


if __name__ == "__main__":
    unittest.main()
