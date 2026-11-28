"""Reusable candle-derived indicators and chart-facing indicator series."""

import math
import uuid
from collections.abc import Iterator, Mapping, Sized
from dataclasses import dataclass
from typing import Any

import dearcygui as dcg
import numpy as np

from .econometric_series import DEFAULT_LINE_COLOR, PlotEconometricSeries
from ._chart_document import indicator_registration_id


SUPPORTED_OHLC_FIELDS = ("open", "high", "low", "close")


def validate_indicator_line_color(line_color: object) -> tuple[int, int, int, int]:
    if not isinstance(line_color, (tuple, list, np.ndarray)):
        raise ValueError(
            "line_color must be an RGBA tuple with four integer channels from 0 to 255"
        )
    try:
        if len(line_color) != 4:
            raise ValueError(
                "line_color must be an RGBA tuple with four integer channels from 0 to 255"
            )
    except TypeError as exc:
        raise ValueError(
            "line_color must be an RGBA tuple with four integer channels from 0 to 255"
        ) from exc
    channels = []
    for channel in line_color:
        if isinstance(channel, (bool, np.bool_)) or not isinstance(channel, (int, np.integer)):
            raise ValueError(
                "line_color must be an RGBA tuple with four integer channels from 0 to 255"
            )
        value = int(channel)
        if not 0 <= value <= 255:
            raise ValueError(
                "line_color must be an RGBA tuple with four integer channels from 0 to 255"
            )
        channels.append(value)
    return tuple(channels)


def validate_ohlc_field(field: object) -> str:
    if not isinstance(field, str):
        raise ValueError("SMA field must be one of: open, high, low, close")
    normalized = field.strip().lower()
    if normalized not in SUPPORTED_OHLC_FIELDS:
        raise ValueError("SMA field must be one of: open, high, low, close")
    return normalized


def validate_sma_period(period: object) -> int:
    if isinstance(period, (bool, np.bool_)):
        raise ValueError("SMA period must be a positive integer")
    if isinstance(period, (int, np.integer)):
        integer = int(period)
    elif isinstance(period, (float, np.floating)):
        number = float(period)
        if not math.isfinite(number) or not number.is_integer():
            raise ValueError("SMA period must be a positive integer")
        integer = int(number)
    else:
        try:
            number = float(period)
        except (TypeError, ValueError, OverflowError) as exc:
            raise ValueError("SMA period must be a positive integer") from exc
        if not math.isfinite(number) or not number.is_integer():
            raise ValueError("SMA period must be a positive integer")
        integer = int(number)
    if integer < 1:
        raise ValueError("SMA period must be a positive integer")
    return integer


@dataclass(frozen=True)
class CandleSnapshot:
    """Canonical one-candle-per-observation input to an indicator."""

    dates: np.ndarray
    opens: np.ndarray
    highs: np.ndarray
    lows: np.ndarray
    closes: np.ndarray
    volumes: np.ndarray | None = None

    def __post_init__(self) -> None:
        arrays = {
            "dates": np.asarray(self.dates, dtype=float),
            "opens": np.asarray(self.opens, dtype=float),
            "highs": np.asarray(self.highs, dtype=float),
            "lows": np.asarray(self.lows, dtype=float),
            "closes": np.asarray(self.closes, dtype=float),
        }
        count = arrays["dates"].size
        if arrays["dates"].ndim != 1:
            raise ValueError("Candle dates must be one-dimensional")
        for name, values in arrays.items():
            if values.ndim != 1 or values.size != count:
                raise ValueError(f"Candle {name} must be one-dimensional and aligned with dates")
        object.__setattr__(self, "dates", arrays["dates"].copy())
        object.__setattr__(self, "opens", arrays["opens"].copy())
        object.__setattr__(self, "highs", arrays["highs"].copy())
        object.__setattr__(self, "lows", arrays["lows"].copy())
        object.__setattr__(self, "closes", arrays["closes"].copy())
        if self.volumes is None:
            object.__setattr__(self, "volumes", np.zeros(count, dtype=float))
        else:
            volumes = np.asarray(self.volumes, dtype=float)
            if volumes.ndim != 1 or volumes.size != count:
                raise ValueError("Candle volumes must be one-dimensional and aligned with dates")
            object.__setattr__(self, "volumes", volumes.copy())

    @classmethod
    def from_data(cls, source: object = None, **kwargs) -> "CandleSnapshot":
        if isinstance(source, cls):
            return source
        if isinstance(source, Mapping):
            kwargs = dict(source, **kwargs)
            source = None
        if source is not None:
            if hasattr(source, "dates") and hasattr(source, "opens"):
                return cls(
                    dates=getattr(source, "dates"),
                    opens=getattr(source, "opens"),
                    highs=getattr(source, "highs"),
                    lows=getattr(source, "lows"),
                    closes=getattr(source, "closes"),
                    volumes=getattr(source, "volume", getattr(source, "volumes", None)),
                )
            raise ValueError("Candle source must be CandleSnapshot or a candle mapping")
        required = ("dates", "opens", "highs", "lows", "closes")
        missing = [name for name in required if name not in kwargs]
        if missing:
            raise ValueError(f"Missing candle field(s): {', '.join(missing)}")
        return cls(
            dates=kwargs["dates"],
            opens=kwargs["opens"],
            highs=kwargs["highs"],
            lows=kwargs["lows"],
            closes=kwargs["closes"],
            volumes=kwargs.get("volumes", kwargs.get("volume")),
        )

    def field(self, name: str) -> np.ndarray:
        name = validate_ohlc_field(name)
        return getattr(self, name + "s")


class IndicatorResult(Mapping[str, np.ndarray]):
    """Timestamp-aligned named outputs returned by an indicator."""

    def __init__(self, timestamps: Sized, outputs: Mapping[str, Sized]) -> None:
        timestamp_array = np.asarray(timestamps, dtype=float)
        if timestamp_array.ndim != 1:
            raise ValueError("Indicator timestamps must be one-dimensional")
        if not outputs:
            raise ValueError("Indicator must provide at least one named output")
        self.timestamps = timestamp_array.copy()
        self.source_dates = self.timestamps.copy()
        normalized: dict[str, np.ndarray] = {}
        for name, values in outputs.items():
            if not isinstance(name, str) or not name:
                raise ValueError("Indicator output names must be non-empty strings")
            array = np.asarray(values, dtype=float)
            if array.ndim != 1 or array.size != timestamp_array.size:
                raise ValueError("Indicator outputs must be aligned one-for-one with timestamps")
            normalized[name] = array.copy()
        self.outputs = normalized
        self.named_outputs = normalized
        self.values = normalized

    def __getitem__(self, name: str) -> np.ndarray:
        return self.outputs[name]

    def __iter__(self) -> Iterator[str]:
        return iter(self.outputs)

    def __len__(self) -> int:
        return len(self.outputs)

    def __contains__(self, name: object) -> bool:
        return name in self.outputs


class Indicator:
    """Minimal reusable contract for candle-derived indicators."""

    kind = "indicator"

    def calculate(self, candles: object = None, **kwargs) -> IndicatorResult:
        raise NotImplementedError

    __call__ = calculate


class SMA(Indicator):
    """Simple moving average over existing finite candle observations."""

    kind = "SMA"

    def __init__(self, period: object = 20, field: object = "close", **kwargs) -> None:
        if "ohlc_field" in kwargs:
            if field != "close" and kwargs["ohlc_field"] != field:
                raise ValueError("Specify only one of field or ohlc_field")
            field = kwargs.pop("ohlc_field")
        if kwargs:
            unknown = ", ".join(sorted(kwargs))
            raise ValueError(f"Unsupported SMA parameter(s): {unknown}")
        self.period = validate_sma_period(period)
        self.field = validate_ohlc_field(field)
        self.parameters = {"period": self.period, "field": self.field}

    @property
    def input_field(self) -> str:
        return self.field

    @property
    def name(self) -> str:
        return f"SMA {self.period} {self.field}"

    def calculate(
        self,
        candles: object = None,
        *,
        dates: object = None,
        opens: object = None,
        highs: object = None,
        lows: object = None,
        closes: object = None,
        close: object = None,
        high: object = None,
        low: object = None,
        open: object = None,
        snapshot: object = None,
    ) -> IndicatorResult:
        if snapshot is not None:
            if candles is not None:
                raise ValueError("Specify only one candle source")
            candles = snapshot
        if isinstance(candles, CandleSnapshot):
            candle_snapshot = candles
        elif isinstance(candles, Mapping):
            candle_snapshot = CandleSnapshot.from_data(candles)
        elif candles is not None and hasattr(candles, "dates"):
            candle_snapshot = CandleSnapshot.from_data(candles)
        elif candles is not None and dates is None:
            # Convenient direct close-series use: SMA(period).calculate([1, 2, 3]).
            close_values = np.asarray(candles, dtype=float)
            if close_values.ndim != 1:
                raise ValueError("Direct close values must be one-dimensional")
            synthetic_dates = np.arange(close_values.size, dtype=float)
            candle_snapshot = CandleSnapshot(
                synthetic_dates,
                close_values,
                close_values,
                close_values,
                close_values,
            )
        else:
            aliases = {
                "open": open,
                "high": high,
                "low": low,
                "close": close,
            }
            for name, value in (("opens", opens), ("highs", highs), ("lows", lows), ("closes", closes)):
                if value is not None:
                    aliases[name[:-1]] = value
            selected = {
                name: aliases[name] if aliases[name] is not None else np.array([], dtype=float)
                for name in SUPPORTED_OHLC_FIELDS
            }
            if dates is None:
                lengths = [np.asarray(values).size for values in selected.values()]
                count = max(lengths, default=0)
                dates = np.arange(count, dtype=float)
            count = np.asarray(dates, dtype=float).size
            for name, values in selected.items():
                array = np.asarray(values, dtype=float)
                if array.size == 0:
                    selected[name] = np.zeros(count, dtype=float)
                elif array.size != count:
                    raise ValueError(f"{name} must be aligned with candle dates")
            candle_snapshot = CandleSnapshot(
                dates=dates,
                opens=selected["open"],
                highs=selected["high"],
                lows=selected["low"],
                closes=selected["close"],
            )

        values = candle_snapshot.field(self.field)
        output = np.full(values.size, np.nan, dtype=float)
        for index in range(self.period - 1, values.size):
            window = values[index - self.period + 1:index + 1]
            if np.all(np.isfinite(window)):
                output[index] = float(np.mean(window))
        return IndicatorResult(candle_snapshot.dates, {"sma": output})

    def with_parameters(self, period: object, field: object) -> "SMA":
        return SMA(period=period, field=field)


SimpleMovingAverage = SMA


def calculate_sma(
    candles: object,
    period: object = 20,
    field: object = "close",
) -> IndicatorResult:
    return SMA(period=period, field=field).calculate(candles)


class PlotCandleIndicatorSeries(PlotEconometricSeries):
    """A candle-derived indicator rendered as one legend-enabled series item."""

    def __init__(
        self,
        context: dcg.Context,
        *,
        indicator_id: str,
        calculator: SMA,
        candles: CandleSnapshot,
        y_axis: dcg.Axis = dcg.Axis.Y1,
        line_color=DEFAULT_LINE_COLOR,
        **kwargs,
    ) -> None:
        line_color = validate_indicator_line_color(line_color)
        result = calculator.calculate(candles)
        kwargs.setdefault("label", calculator.name)
        kwargs.setdefault("markers", False)
        kwargs.setdefault("tooltip", True)
        super().__init__(
            context,
            dates=candles.dates,
            source_dates=candles.dates,
            values=result["sma"],
            y_axis=y_axis,
            line_color=line_color,
            **kwargs,
        )
        self.indicator_id = indicator_id
        self.calculator = calculator
        self._parameters = dict(calculator.parameters)

    @property
    def parameters(self) -> dict[str, object]:
        return dict(self._parameters)

    @property
    def line_color(self) -> tuple[int, int, int, int]:
        return tuple(self._line_color)

    def update_all(self, *, dates, values, source_dates=None, label: str | None = None) -> None:
        raise TypeError(
            "Candle indicators are derived from candles and cannot be mutated directly"
        )

    def apply_calculation_update(
        self,
        *,
        dates,
        values,
        source_dates=None,
        label: str | None = None,
    ) -> None:
        super().update_all(
            dates=dates,
            values=values,
            source_dates=source_dates,
            label=label,
        )

    def update_from_calculation(
        self,
        *,
        calculator: SMA,
        candles: CandleSnapshot,
        plot_dates: object | None = None,
        label: str | None = None,
        line_color: object | None = None,
    ) -> IndicatorResult:
        result = calculator.calculate(candles)
        source_dates = candles.dates
        plotted = source_dates if plot_dates is None else np.asarray(plot_dates, dtype=float)
        if plotted.ndim != 1 or plotted.size != source_dates.size:
            raise ValueError("plot_dates must be one-dimensional and aligned with candle dates")
        validated_line_color = (
            None if line_color is None else validate_indicator_line_color(line_color)
        )
        if validated_line_color is not None:
            self._line_color = validated_line_color
        self._parameters = dict(calculator.parameters)
        self.calculator = calculator
        self.apply_calculation_update(
            dates=plotted,
            values=result["sma"],
            source_dates=source_dates,
            label=calculator.name if label is None else label,
        )
        return result


class _CandleIndicatorMutationAdapter:
    def capture(self):
        raise TypeError("Candle indicators are derived and do not support direct mutation")

    def prepare_append(self, timestamp, values):
        raise TypeError("Candle indicators are derived and do not support direct append")

    def prepare_update(self, values):
        raise TypeError("Candle indicators are derived and do not support direct updates")

    def publish(self, prepared):
        raise TypeError("Candle indicators are derived and do not support direct publication")


@dataclass(frozen=True)
class IndicatorInstance:
    instance_id: str
    registration_id: str
    series: PlotCandleIndicatorSeries
    calculator: SMA


class IndicatorRegistry:
    """Minimal type-name to SMA factory registry."""

    def __init__(self) -> None:
        self._factories: dict[str, Any] = {"SMA": SMA}

    def register(self, type_name: str, factory: Any) -> None:
        normalized = self._normalize(type_name)
        if not callable(factory):
            raise TypeError("Indicator factory must be callable")
        self._factories[normalized] = factory

    @staticmethod
    def _normalize(type_name: object) -> str:
        if not isinstance(type_name, str) or not type_name.strip():
            raise ValueError("Indicator type must be a non-empty string")
        return type_name.strip().upper()

    def create(self, type_name: object = "SMA", **parameters) -> SMA:
        normalized = self._normalize(type_name)
        if normalized not in self._factories:
            raise ValueError(f"Unsupported indicator type: {type_name}")
        factory = self._factories[normalized]
        try:
            return factory(**parameters)
        except TypeError as exc:
            raise ValueError(str(exc)) from exc

    @property
    def types(self) -> tuple[str, ...]:
        return tuple(sorted(self._factories))


class CandleIndicatorManager:
    """Own independent indicator instances and chart registrations."""

    def __init__(self, chart) -> None:
        self.chart = chart
        self.registry = IndicatorRegistry()
        self._instances: dict[str, IndicatorInstance] = {}
        self._next_number = 1

    @property
    def instances(self) -> dict[str, IndicatorInstance]:
        return dict(self._instances)

    @property
    def indicator_ids(self) -> tuple[str, ...]:
        return tuple(self._instances)

    def _chart_candles(self) -> CandleSnapshot:
        candle = getattr(self.chart, "candlestick_plot", None)
        if candle is None:
            return CandleSnapshot(
                dates=np.array([], dtype=float),
                opens=np.array([], dtype=float),
                highs=np.array([], dtype=float),
                lows=np.array([], dtype=float),
                closes=np.array([], dtype=float),
            )
        return CandleSnapshot(
            dates=np.asarray(candle.source_dates, dtype=float),
            opens=np.asarray(candle.opens, dtype=float),
            highs=np.asarray(candle.highs, dtype=float),
            lows=np.asarray(candle.lows, dtype=float),
            closes=np.asarray(candle.closes, dtype=float),
            volumes=np.asarray(candle.volumes, dtype=float) if len(candle.volumes) else None,
        )

    def create(
        self,
        *,
        type: object = "SMA",
        period: object = 20,
        field: object = "close",
        y_axis: dcg.Axis = dcg.Axis.Y1,
        line_color=DEFAULT_LINE_COLOR,
        instance_id: str | None = None,
        **kwargs,
    ) -> IndicatorInstance:
        if instance_id is None:
            while True:
                candidate = f"indicator-{uuid.uuid4().hex}"
                if (candidate not in self._instances
                        and indicator_registration_id(candidate) not in self.chart.time_series_ids):
                    instance_id = candidate
                    break
        if not isinstance(instance_id, str) or not instance_id:
            raise ValueError("Indicator instance ID must be a non-empty string")
        registration_id = indicator_registration_id(instance_id)
        if instance_id in self._instances or registration_id in self.chart.time_series_ids:
            raise ValueError(f"Indicator instance or registration ID already exists: {instance_id!r}")
        calculator = self.registry.create(type, period=period, field=field)
        candles = self._chart_candles()
        calculator.calculate(candles)
        with self.chart:
            series = PlotCandleIndicatorSeries(
                self.chart.context,
                indicator_id=instance_id,
                calculator=calculator,
                candles=candles,
                y_axis=y_axis,
                line_color=line_color,
                **kwargs,
            )
        if self.chart._gap_manager.time_is_collapsed and self.chart._gap_manager.time_map is not None:
            plotted = self.chart._gap_manager.time_map.project_many(
                candles.dates,
                in_gap="next",
            )
            series.set_plot_dates(plotted)
        self.chart.register_time_series(
            registration_id,
            series,
            in_gap="next",
            mutation_adapter=_CandleIndicatorMutationAdapter(),
        )
        self.chart._plot_dates_by_id[registration_id] = np.asarray(series.plot_dates, dtype=float).copy()
        instance = IndicatorInstance(
            instance_id=instance_id,
            registration_id=registration_id,
            series=series,
            calculator=calculator,
        )
        self._instances[instance_id] = instance
        self._next_number += 1
        return instance

    add = create
    add_sma = create
    create_indicator = create

    def get(self, instance_id: str) -> IndicatorInstance:
        if instance_id not in self._instances:
            raise ValueError(f"Unknown indicator instance ID: {instance_id!r}")
        return self._instances[instance_id]

    def edit(
        self,
        instance_id: str,
        *,
        period: object | None = None,
        field: object | None = None,
        line_color: object | None = None,
    ) -> IndicatorInstance:
        instance = self.get(instance_id)
        parameters = instance.calculator.parameters
        calculator = SMA(
            period=parameters["period"] if period is None else period,
            field=parameters["field"] if field is None else field,
        )
        candles = self._chart_candles()
        result = calculator.calculate(candles)
        plot_dates = np.asarray(instance.series.plot_dates, dtype=float)
        if self.chart._gap_manager.time_is_collapsed and self.chart._gap_manager.time_map is not None:
            plot_dates = self.chart._gap_manager.time_map.project_many(
                candles.dates,
                in_gap="next",
            )
        instance.series.update_from_calculation(
            calculator=calculator,
            candles=candles,
            plot_dates=plot_dates,
            line_color=line_color,
        )
        self.chart._plot_dates_by_id[instance.registration_id] = np.asarray(
            instance.series.plot_dates,
            dtype=float,
        ).copy()
        if not isinstance(result["sma"], np.ndarray):
            raise RuntimeError("Indicator calculation did not return an SMA array")
        updated = IndicatorInstance(
            instance_id=instance.instance_id,
            registration_id=instance.registration_id,
            series=instance.series,
            calculator=calculator,
        )
        self._instances[instance_id] = updated
        return updated

    edit_indicator = edit

    def remove(self, instance_id: str) -> None:
        instance = self.get(instance_id)
        self.chart.unregister_time_series(instance.registration_id)
        try:
            instance.series.delete_item()
        finally:
            del self._instances[instance_id]

    remove_indicator = remove

    def prepare_candle_state(self, prepared: dict[str, object]) -> dict[str, IndicatorResult]:
        candles = CandleSnapshot(
            dates=np.asarray(prepared["source_dates"], dtype=float),
            opens=np.asarray(prepared["opens"], dtype=float),
            highs=np.asarray(prepared["highs"], dtype=float),
            lows=np.asarray(prepared["lows"], dtype=float),
            closes=np.asarray(prepared["closes"], dtype=float),
            volumes=np.asarray(prepared["volumes"], dtype=float) if len(prepared["volumes"]) else None,
        )
        return {
            instance_id: instance.calculator.calculate(candles)
            for instance_id, instance in self._instances.items()
        }

    def publish_candle_state(
        self,
        prepared: dict[str, object],
        prepared_results: dict[str, IndicatorResult] | None = None,
    ) -> None:
        candles = CandleSnapshot(
            dates=np.asarray(prepared["source_dates"], dtype=float),
            opens=np.asarray(prepared["opens"], dtype=float),
            highs=np.asarray(prepared["highs"], dtype=float),
            lows=np.asarray(prepared["lows"], dtype=float),
            closes=np.asarray(prepared["closes"], dtype=float),
            volumes=np.asarray(prepared["volumes"], dtype=float) if len(prepared["volumes"]) else None,
        )
        results = (
            prepared_results
            if prepared_results is not None
            else self.prepare_candle_state(prepared)
        )
        for instance_id, instance in list(self._instances.items()):
            result = results[instance_id]
            if self.chart._gap_manager.time_is_collapsed and self.chart._gap_manager.time_map is not None:
                plotted = self.chart._gap_manager.time_map.project_many(
                    candles.dates,
                    in_gap="next",
                )
            else:
                plotted = candles.dates
            instance.series.apply_calculation_update(
                dates=plotted,
                source_dates=candles.dates,
                values=result["sma"],
                label=instance.calculator.name,
            )
            self.chart._plot_dates_by_id[instance.registration_id] = np.asarray(plotted, dtype=float).copy()
