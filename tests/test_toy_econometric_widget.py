from datetime import datetime, timezone

import numpy as np
import pytest

from examples.DearCyFi_Demo.data_widgets import DATA_WIDGETS, DataRequest
from examples.DearCyFi_Demo.data_widgets.toy_econometric import (
    PROVIDER_ID,
    load_toy_econometric_data,
)


def test_registry_resolves_toy_provider_and_rejects_unknown_id():
    assert DATA_WIDGETS.get(PROVIDER_ID).provider_id == PROVIDER_ID
    with pytest.raises(ValueError, match="Unknown data provider"):
        DATA_WIDGETS.get("missing")


def test_toy_generation_is_deterministic_sorted_and_normalized():
    request = DataRequest(
        provider_id=PROVIDER_ID,
        dataset_id="weekly-liquidity",
        start=datetime(2024, 1, 5, tzinfo=timezone.utc),
        interval="weekly",
        filters={"periods": 12, "seed": 42},
    )

    first = load_toy_econometric_data(request)
    second = load_toy_econometric_data(request)
    series = first.series[0]

    assert series.kind == "line"
    assert set(series.values) == {"value"}
    assert len(series.timestamps) == len(series.values["value"]) == 12
    assert np.all(np.diff(series.timestamps) > 0)
    np.testing.assert_array_equal(series.timestamps, second.series[0].timestamps)
    np.testing.assert_array_equal(series.values["value"], second.series[0].values["value"])


def test_toy_generation_rejects_invalid_configuration():
    request = DataRequest(
        provider_id=PROVIDER_ID,
        dataset_id="weekly-liquidity",
        filters={"periods": 0},
    )
    with pytest.raises(ValueError, match="periods"):
        load_toy_econometric_data(request)