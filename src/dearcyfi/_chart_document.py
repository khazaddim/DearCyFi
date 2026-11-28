"""Strict, provider-independent version 1 chart document and file codec."""

import json
import math
import os
import tempfile
from itertools import pairwise
from pathlib import Path
from typing import Any, Literal, TypedDict

FORMAT = "dearcyfi-chart"
VERSION = 1
MAX_DOCUMENT_BYTES = 64 * 1024 * 1024
MAX_SOURCE_TIMESTAMP = 32_503_680_000
AXES = ("X1", "Y1", "Y2", "Y3")
ITEM_FLAGS = ("no_legend", "ignore_fit")
LEGEND_FLAGS = ("horizontal", "outside", "no_buttons", "no_highlight_item",
                "no_highlight_axis", "no_menus", "sorted")
BOX_COLORS = ("line_color", "hover_line_color", "active_line_color",
              "fill_color", "hover_fill_color", "active_fill_color")
DATE_FLAGS = ("use_local_time", "use_24_hour", "use_iso8601", "date_context_labels")


class _SeriesPayload(TypedDict):
    id: str
    data: dict[str, Any]
    display: dict[str, Any]


class BarRecord(_SeriesPayload):
    kind: Literal["horizontal-bars"]


class SourceRecord(_SeriesPayload):
    kind: Literal["candles", "econometric"]
    in_gap: Literal["next", "previous"]


class IndicatorRecord(TypedDict):
    id: str
    kind: Literal["sma"]
    input: Literal["candles"]
    parameters: dict[str, Any]
    display: dict[str, Any]


class DrawingRecord(TypedDict):
    id: str
    kind: Literal["range-box"]
    geometry: dict[str, float]
    options: dict[str, Any]
    display: dict[str, Any]


class ChartDocument(TypedDict):
    format: Literal["dearcyfi-chart"]
    version: Literal[1]
    chart: dict[str, Any]
    series: list[BarRecord | SourceRecord]
    indicators: list[IndicatorRecord]
    drawings: list[DrawingRecord]


class ChartPersistenceError(ValueError):
    """A chart cannot be represented, validated, or restored as a snapshot."""


def _fail(path, reason):
    raise ChartPersistenceError(f"{path}: {reason}")


def _object(value, path, *fields):
    if type(value) is not dict:
        _fail(path, "expected an object")
    for field in fields:
        if field not in value:
            _fail(f"{path}.{field}", "required field is missing")
    for field in value.keys() - set(fields):
        _fail(path, f"unknown field {field!r}")
    return value


def _array(value, path, length=None):
    if type(value) is not list:
        _fail(path, "expected an array")
    if length is not None and len(value) != length:
        _fail(path, f"expected {length} entries, got {len(value)}")
    return value


def _text(value, path, *, nonempty=False):
    if type(value) is not str or (nonempty and not value):
        _fail(path, "expected a non-empty string" if nonempty else "expected a string")
    try:
        value.encode("utf-8")
    except UnicodeError as exc:
        raise ChartPersistenceError(f"{path}: invalid Unicode string") from exc


def _choice(value, path, choices):
    if type(value) is not str or value not in choices:
        _fail(path, f"expected one of {', '.join(choices)}; got {value!r}")


def _flags(value, path, fields):
    for field in fields:
        if type(value[field]) is not bool:
            _fail(f"{path}.{field}", "expected a boolean")


def _number(value, path, *, minimum=None, positive=False):
    if type(value) not in (int, float):
        _fail(path, "expected a finite number")
    try:
        finite = math.isfinite(value)
    except OverflowError:
        finite = False
    if not finite:
        _fail(path, "expected a finite representable number")
    if positive and value <= 0:
        _fail(path, "must be positive")
    if minimum is not None and value < minimum:
        _fail(path, f"must be at least {minimum}")


def _color(value, path):
    for channel in _array(value, path, 4):
        if type(channel) is not int or not 0 <= channel <= 255:
            _fail(path, "expected four integer RGBA channels from 0 to 255")


def _column(value, path, length=None, *, missing=False, minimum=None):
    column = _array(value, path, length)
    for i, sample in enumerate(column):
        if sample is not None or not missing:
            _number(sample, f"{path}[{i}]", minimum=minimum)
    return column


def _dates(value, path, *, strict=False):
    dates = _column(value, path, minimum=0)
    if any(value > MAX_SOURCE_TIMESTAMP for value in dates):
        _fail(path, "timestamps exceed the supported ImPlot time range")
    if strict:
        for i, (left, right) in enumerate(pairwise(dates), 1):
            if float(right) <= float(left):
                _fail(f"{path}[{i}]", "timestamps must be strictly increasing")
    return dates


def _item_display(value, path, *extra, axis=True):
    _object(value, path, "label", *ITEM_FLAGS, *(("y_axis",) if axis else ()), *extra)
    _text(value["label"], f"{path}.label")
    _flags(value, path, ITEM_FLAGS)
    if axis:
        _choice(value["y_axis"], f"{path}.y_axis", AXES[1:])


BAR_STYLES = ("colors", "line_colors", "value_space", "normalized_max_fraction", "weight",
              "anchor", "anchor_value")


def _bar_display(value, path, count, *, volume=False):
    _item_display(value, path, *BAR_STYLES, *(("auto_weight",) if volume else ()), axis=not volume)
    _choice(value["value_space"], f"{path}.value_space", ("data", "normalized"))
    _choice(value["anchor"], f"{path}.anchor", ("baseline", "axis_min", "axis_max"))
    _number(value["anchor_value"], f"{path}.anchor_value")
    fraction = value["normalized_max_fraction"]
    _number(fraction, f"{path}.normalized_max_fraction", positive=True)
    if fraction > 1:
        _fail(f"{path}.normalized_max_fraction", "must not exceed 1")
    _number(value["weight"], f"{path}.weight", positive=True)
    if volume:
        _flags(value, path, ("auto_weight",))
    for name in ("colors", "line_colors"):
        colors = value[name]
        if not (volume and name == "colors" and colors is None):
            _array(colors, f"{path}.{name}")
            if len(colors) not in (0, 1, count):
                _fail(f"{path}.{name}", "expected zero, one, or one RGBA per bar")
            for i, color in enumerate(colors):
                _color(color, f"{path}.{name}[{i}]")


def _candles(record, path):
    if record["id"] != "candles":
        _fail(f"{path}.id", "the candle series ID must be 'candles'")
    data = _object(record["data"], f"{path}.data",
                   "dates", "open", "high", "low", "close", "volume", "index", "time_counts")
    dates = _dates(data["dates"], f"{path}.data.dates", strict=True)
    count = len(dates)
    for field in ("open", "high", "low", "close"):
        _column(data[field], f"{path}.data.{field}", count)
    for i, (o, h, low, c) in enumerate(zip(data["open"], data["high"], data["low"], data["close"])):
        if not (low <= o <= h and low <= c <= h):
            _fail(f"{path}.data[{i}]", "expected low <= open/close <= high")
    if data["volume"] is not None:
        _column(data["volume"], f"{path}.data.volume", count, missing=True, minimum=0)
    if data["index"] is not None:
        for i, value in enumerate(_array(data["index"], f"{path}.data.index", count)):
            field = f"{path}.data.index[{i}]"
            if type(value) is str:
                _text(value, field)
            elif value is not None and type(value) is not bool:
                _number(value, field)
    if data["time_counts"] is not None:
        for i, row in enumerate(_array(data["time_counts"], f"{path}.data.time_counts", count)):
            field = f"{path}.data.time_counts[{i}]"
            if len(_array(row, field)) > 3:
                _fail(field, "expected at most three count annotations")
            for value in row:
                if type(value) is not int:
                    _fail(field, "expected integer count annotations")
                _number(value, field)
    display = record["display"]
    field = f"{path}.display"
    _item_display(display, field, "bull_color", "bear_color", "weight", "tooltip",
                  "count_position", "count_offset", "volume")
    for color in ("bull_color", "bear_color"):
        _color(display[color], f"{field}.{color}")
    _flags(display, field, ("tooltip",))
    _choice(display["count_position"], f"{field}.count_position", ("above", "below"))
    _number(display["count_offset"], f"{field}.count_offset")
    _number(display["weight"], f"{field}.weight", positive=True)
    _bar_display(display["volume"], f"{field}.volume", count, volume=True)
    return dates


def _line_display(display, path):
    _item_display(display, path, "line_color", "line_thickness", "markers",
                  "marker_color", "marker_radius", "tooltip")
    _flags(display, path, ("markers", "tooltip"))
    for name in ("line_color", "marker_color"):
        _color(display[name], f"{path}.{name}")
    for name in ("line_thickness", "marker_radius"):
        _number(display[name], f"{path}.{name}", positive=True)


def _econometric(record, path):
    data = _object(record["data"], f"{path}.data", "dates", "values")
    dates = _dates(data["dates"], f"{path}.data.dates")
    _column(data["values"], f"{path}.data.values", len(dates), missing=True)
    _line_display(record["display"], f"{path}.display")
    return dates


def _horizontal_bars(record, path):
    data = _object(record["data"], f"{path}.data", "lengths", "levels")
    lengths = _column(data["lengths"], f"{path}.data.lengths")
    _column(data["levels"], f"{path}.data.levels", len(lengths))
    _bar_display(record["display"], f"{path}.display", len(lengths))
    if record["display"]["value_space"] == "normalized":
        for i, length in enumerate(lengths):
            if not 0 <= length <= 1:
                _fail(f"{path}.data.lengths[{i}]", "normalized length must be between 0 and 1")
    return None


def _sma(record, path):
    _choice(record["input"], f"{path}.input", ("candles",))
    parameters = _object(record["parameters"], f"{path}.parameters", "period", "field")
    period = parameters["period"]
    if type(period) is not int:
        _fail(f"{path}.parameters.period", "expected a positive integer")
    _number(period, f"{path}.parameters.period", positive=True)
    _choice(parameters["field"], f"{path}.parameters.field", ("open", "high", "low", "close"))
    _line_display(record["display"], f"{path}.display")


def _range_box(record, path):
    geometry = _object(record["geometry"], f"{path}.geometry", "left_time", "right_time", "bottom", "top")
    for name, value in geometry.items():
        _number(value, f"{path}.geometry.{name}")
    options = _object(record["options"], f"{path}.options",
                      "anchor_tooltips_enabled", "hit_size", "min_source_width", "min_source_height")
    _flags(options, f"{path}.options", ("anchor_tooltips_enabled",))
    _number(options["hit_size"], f"{path}.options.hit_size", positive=True)
    for name in ("min_source_width", "min_source_height"):
        _number(options[name], f"{path}.options.{name}", minimum=0)
    for lower, upper, minimum in (("left_time", "right_time", "min_source_width"),
                                  ("bottom", "top", "min_source_height")):
        span = float(geometry[upper]) - float(geometry[lower])
        _number(span, f"{path}.geometry.{upper}", minimum=options[minimum])
    display = _object(record["display"], f"{path}.display", "y_axis", *BOX_COLORS)
    _choice(display["y_axis"], f"{path}.display.y_axis", AXES[1:])
    for name in BOX_COLORS:
        _color(display[name], f"{path}.display.{name}")


SERIES_VALIDATORS = {"candles": _candles, "econometric": _econometric, "horizontal-bars": _horizontal_bars}
INDICATOR_VALIDATORS = {"sma": _sma}
DRAWING_VALIDATORS = {"range-box": _range_box}


def indicator_registration_id(instance_id: str) -> str:
    return f"indicator:{instance_id}"


def _validate_time(time, sources):
    path = "chart.time"
    _object(time, path, "source", "vectorized", "gaps", "active_method", "stream_interval", *DATE_FLAGS)
    _flags(time, path, ("vectorized", *DATE_FLAGS))
    source = time["source"]
    if source is not None:
        _text(source, f"{path}.source", nonempty=True)
        if source not in sources:
            _fail(f"{path}.source", f"unknown registration {source!r}")
    if time["stream_interval"] is not None:
        _number(time["stream_interval"], f"{path}.stream_interval", positive=True)
        if source is None or not sources[source]:
            _fail(f"{path}.stream_interval", "requires a nonempty collapse source")
    gaps = time["gaps"]
    if gaps is None:
        if time["active_method"] is not None:
            _fail(f"{path}.active_method", "must be null in source time")
        return
    _choice(time["active_method"], f"{path}.active_method", ("scalar", "vectorized"))
    _array(gaps, f"{path}.gaps")
    dates = sources.get(source)
    if not dates:
        _fail(f"{path}.source", "collapsed time requires a nonempty source")
    if any(right < left for left, right in pairwise(dates)):
        dates = sorted(dates)
    sample_idx = 0
    for i, gap in enumerate(gaps):
        field = f"{path}.gaps[{i}]"
        _array(gap, field, 3)
        for value in gap:
            _number(value, field)
        start, stop, retained = map(float, gap)
        if not 0 < retained < stop - start or start + retained <= start:
            _fail(field, "retained width must be representable, positive and shorter than the gap")
        while sample_idx + 1 < len(dates):
            left, right = float(dates[sample_idx]), float(dates[sample_idx + 1])
            if left == start and right == stop:
                break
            if left > start:
                _fail(field, "gap must be ordered and bounded by adjacent source samples")
            sample_idx += 1
        else:
            _fail(field, "gap must be ordered and bounded by adjacent source samples")
        sample_idx += 1


def _validate_view(chart, sources):
    _object(chart, "chart", "axes", "legend", "anchor_tooltips_enabled", "time")
    _flags(chart, "chart", ("anchor_tooltips_enabled",))
    legend = _object(chart["legend"], "chart.legend", "show", "location", *LEGEND_FLAGS)
    _flags(legend, "chart.legend", ("show", *LEGEND_FLAGS))
    _choice(legend["location"], "chart.legend.location",
            ("CENTER", "NORTH", "SOUTH", "WEST", "EAST", "NORTHWEST", "NORTHEAST", "SOUTHWEST", "SOUTHEAST"))
    _validate_time(chart["time"], sources)
    axes = _object(chart["axes"], "chart.axes", *AXES)
    for name, axis in axes.items():
        path = f"chart.axes.{name}"
        _object(axis, path, "enabled", "label", "scale", "range", "invert", "opposite",
                *(("space",) if name == "X1" else ()))
        _text(axis["label"], f"{path}.label")
        _flags(axis, path, ("enabled", "invert", "opposite"))
        _choice(axis["scale"], f"{path}.scale", ("LINEAR", "TIME", "LOG10", "SYMLOG"))
        if name == "X1":
            space = "source" if chart["time"]["gaps"] is None else "collapsed"
            _choice(axis["space"], f"{path}.space", (space,))
        if axis["range"] is not None:
            lo, hi = _column(axis["range"], f"{path}.range", 2)
            if not float(lo) < float(hi) or not math.isfinite(float(hi) - float(lo)):
                _fail(f"{path}.range", "expected increasing limits with a finite span")
            if axis["scale"] == "LOG10" and lo <= 0:
                _fail(f"{path}.range", "logarithmic limits must be positive")


def validate_document(document: object) -> ChartDocument:
    """Validate a detached document without constructing any GUI objects."""
    doc = _object(document, "document", "format", "version", "chart", "series", "indicators", "drawings")
    _choice(doc["format"], "format", (FORMAT,))
    if type(doc["version"]) is not int or doc["version"] != VERSION:
        _fail("version", f"unsupported chart version {doc['version']!r}; expected {VERSION}")
    sources = {}
    for collection, validators, fields in (
        ("series", SERIES_VALIDATORS, ("data", "display")),
        ("indicators", INDICATOR_VALIDATORS, ("input", "parameters", "display")),
        ("drawings", DRAWING_VALIDATORS, ("geometry", "options", "display")),
    ):
        ids = set()
        have_bars = False
        for i, record in enumerate(_array(doc[collection], collection)):
            path = f"{collection}[{i}]"
            kind = record.get("kind") if type(record) is dict else None
            _choice(kind, f"{path}.kind", validators)
            time_series = kind in ("candles", "econometric")
            _object(record, path, "id", "kind", *fields, *(("in_gap",) if time_series else ()))
            item_id = record["id"]
            _text(item_id, f"{path}.id", nonempty=True)
            if item_id in ids:
                _fail(f"{path}.id", f"duplicate ID {item_id!r}")
            ids.add(item_id)
            path += f" ({item_id!r})"
            dates = validators[kind](record, path)
            if kind == "horizontal-bars":
                if have_bars:
                    _fail(path, "this chart supports one horizontal bar overlay")
                have_bars = True
            if time_series:
                _choice(record["in_gap"], f"{path}.in_gap", ("next", "previous"))
                if kind != "candles" and item_id == "candles":
                    _fail(f"{path}.id", "'candles' is reserved for the chart's candle series")
                sources[item_id] = dates
            elif collection == "indicators":
                registration_id = indicator_registration_id(item_id)
                if registration_id in sources:
                    _fail(f"{path}.id", f"registration ID {registration_id!r} collides with a source series")
                sources[registration_id] = sources.get("candles", [])
            elif collection == "drawings" and "candles" not in sources:
                _fail(path, "range boxes require a candle series")
    _validate_view(doc["chart"], sources)
    return doc


def _unique_keys(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            _fail("JSON", f"duplicate object key {key!r}")
        result[key] = value
    return result


def _invalid_constant(value):
    _fail("JSON", f"non-finite number {value!r}")


def read_document(path: str | os.PathLike[str]) -> ChartDocument:
    """Read one bounded, strictly UTF-8 encoded chart document."""
    target = Path(path)
    with target.open("rb") as stream:
        if os.fstat(stream.fileno()).st_size > MAX_DOCUMENT_BYTES:
            _fail(str(target), "chart exceeds the 64 MiB limit")
        raw = stream.read(MAX_DOCUMENT_BYTES + 1)
    if len(raw) > MAX_DOCUMENT_BYTES:
        _fail(str(target), "chart exceeds the 64 MiB limit")
    try:
        document = json.loads(raw.decode("utf-8"), object_pairs_hook=_unique_keys,
                              parse_constant=_invalid_constant)
    except (UnicodeError, ValueError, RecursionError) as exc:
        raise ChartPersistenceError(f"{target}: invalid UTF-8 JSON: {exc}") from exc
    return validate_document(document)


def write_document(path: str | os.PathLike[str], document: ChartDocument, *, overwrite: bool = False,
                   publish=None) -> None:
    """Write a complete sibling temporary file and publish without a clobber race."""
    if type(overwrite) is not bool:
        raise TypeError("overwrite must be a boolean")
    target = Path(path).absolute()
    validate_document(document)
    encoder = json.JSONEncoder(ensure_ascii=False, allow_nan=False, separators=(",", ":"))
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="wb", prefix=".dearcyfi-", suffix=".tmp",
                                         dir=target.parent, delete=False) as stream:
            temporary = Path(stream.name)
            written = 0
            # Keep chunks bounded even for a document with one very large column.
            buffer = bytearray()
            for chunk in encoder.iterencode(document):
                encoded = chunk.encode("utf-8")
                written += len(encoded)
                if written > MAX_DOCUMENT_BYTES:
                    _fail(str(target), "chart exceeds the 64 MiB limit")
                buffer.extend(encoded)
                if len(buffer) >= 65536:
                    stream.write(buffer)
                    buffer.clear()
            stream.write(buffer)
            stream.flush()
            os.fsync(stream.fileno())

        def replace():
            if overwrite:
                os.replace(temporary, target)
            elif os.name == "nt":
                os.rename(temporary, target)  # On Windows rename never replaces.
            else:
                os.link(temporary, target)  # Publish only if the name is still free.

        if publish is None:
            replace()
        else:
            publish(replace)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
