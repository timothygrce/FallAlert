"""DATA PROCESSING (used by BOTH edge devices).

Processing A: accelerometer -> RMS, minimum (free-fall) and peak (impact) magnitude.
Processing B: gyroscope -> total angular movement (orientation change).
"""

from dataclasses import dataclass
from math import isfinite, sqrt

GRAVITY = 9.81


@dataclass(frozen=True)
class SensorSample:
    seconds: float
    acceleration: tuple[float, float, float]
    gyroscope: tuple[float, float, float]


@dataclass(frozen=True)
class Features:
    motion_rms: float
    rotation_rad: float
    min_magnitude: float = GRAVITY   # terendah dalam window -> free-fall
    peak_magnitude: float = GRAVITY  # tertinggi dalam window -> benturan
    min_before_peak: bool = False


def extract_features(samples: list[SensorSample]) -> Features:
    if len(samples) < 2:
        raise ValueError("At least 2 sensor samples are required")

    for sampel in samples:
        if not all(isfinite(nilai) for nilai in (sampel.seconds, *sampel.acceleration, *sampel.gyroscope)):
            raise ValueError("Pembacaan sensor harus berupa angka terbatas")

    acceleration_errors = []
    magnitudes = []
    for sample in samples:
        x, y, z = sample.acceleration
        acceleration_magnitude = sqrt(x * x + y * y + z * z)
        magnitudes.append(acceleration_magnitude)
        acceleration_errors.append(acceleration_magnitude - GRAVITY)

    motion_rms = sqrt(sum(value ** 2 for value in acceleration_errors) / len(samples))

    rotation_rad = 0.0
    for previous, current in zip(samples, samples[1:]):
        delta_seconds = max(0.0, current.seconds - previous.seconds)
        gx, gy, gz = current.gyroscope
        angular_speed = sqrt(gx * gx + gy * gy + gz * gz)
        rotation_rad += angular_speed * delta_seconds

    return Features(
        motion_rms=round(motion_rms, 4),
        rotation_rad=round(rotation_rad, 4),
        min_magnitude=round(min(magnitudes), 4),
        peak_magnitude=round(max(magnitudes), 4),
        min_before_peak=magnitudes.index(min(magnitudes)) < magnitudes.index(max(magnitudes)),
    )
