"""NODE 3: algoritma deteksi jatuh (pure Python, tanpa dependensi MQTT).

Algoritma: state machine berbasis fitur sensor (rule-based sensor fusion).
  IDLE -> (free-fall + benturan) -> POSSIBLE_FALL -> (diam >= 2 window) -> ALERT
Edge 1 = HP yang dibawa pengguna. Edge 2 = HP keluarga penerima alarm.
Gerakan HP keluarga tidak membatalkan dugaan jatuh.
"""

from dataclasses import dataclass
import time

from shared.messages import Telemetry


@dataclass(frozen=True)
class Decision:
    status: str
    reason: str
    score: float = 0.0


class FallDetector:
    def __init__(self, freefall_threshold: float = 4.0, impact_threshold: float = 15.0,
                 still_motion: float = 0.8, still_rotation: float = 0.3,
                 still_windows_needed: int = 2, freefall_memory_ms: int = 2_000,
                 possible_timeout_ms: int = 15_000):
        self.freefall_threshold = freefall_threshold
        self.impact_threshold = impact_threshold
        self.still_motion = still_motion
        self.still_rotation = still_rotation
        self.still_windows_needed = still_windows_needed
        self.freefall_memory_ms = freefall_memory_ms
        self.possible_timeout_ms = possible_timeout_ms
        self.armed = True
        self.latest: dict[str, Telemetry] = {}
        self.last_seq: dict[tuple[str, str], int] = {}
        self.bootAktif: dict[str, str] = {}
        self.waktuTerakhir: dict[str, int] = {}
        self.freefall_at_ms: int | None = None
        self.possible_since_ms: int | None = None
        self.still_count = 0
        self.impact_peak = 0.0
        self.alarm_aktif = False

    def set_armed(self, armed: bool):
        self.armed = armed
        self._reset()
        self.alarm_aktif = False

    def _reset(self):
        self.freefall_at_ms = None
        self.possible_since_ms = None
        self.still_count = 0
        self.impact_peak = 0.0

    def _is_still(self, data: Telemetry) -> bool:
        return data.motion_rms < self.still_motion and data.rotation_rad < self.still_rotation

    def accept(self, data: Telemetry, now_ms: int | None = None) -> Decision:
        waktuSekarangMs = now_ms if now_ms is not None else int(time.time() * 1000)
        if abs(waktuSekarangMs - data.sent_at_ms) > 30_000:
            return Decision("REJECTED_STALE", "Timestamp outside the allowed 30-second window")

        key = (data.device_id, data.boot_id)
        if data.sequence <= self.last_seq.get(key, -1):
            return Decision("REJECTED_REPLAY", "Repeated/out-of-order sequence for this boot ID")
        if data.sent_at_ms < self.waktuTerakhir.get(data.device_id, 0):
            return Decision("REJECTED_STALE", "Waktu telemetri lebih lama daripada data sebelumnya")
        bootLama = self.bootAktif.get(data.device_id)
        if bootLama is not None and bootLama != data.boot_id and data.device_id == "edge1":
            self._reset()  # Jangan gabungkan sampel sebelum dan sesudah HP restart.
        self.bootAktif[data.device_id] = data.boot_id
        self.waktuTerakhir[data.device_id] = data.sent_at_ms
        self.last_seq[key] = data.sequence
        self.latest[data.device_id] = data

        if not self.armed:
            return Decision("DISARMED", "Monitoring paused by the owner")
        if data.device_id != "edge1":
            return Decision("WAITING", "Telemetri HP keluarga diterima")
        if self.alarm_aktif:
            return Decision("ALERT_ACTIVE", "Alarm aktif; periksa kondisi dan tekan ARM untuk mereset")

        # Sebuah window bisa memuat kedua kejadian. Periksa urutan sampelnya,
        # atau gunakan jatuh bebas dari window sebelumnya yang masih baru.
        jatuhBebasSebelumnya = (self.freefall_at_ms is not None
                                and 0 <= data.sent_at_ms - self.freefall_at_ms <= self.freefall_memory_ms)
        adaJatuhBebas = data.min_magnitude <= self.freefall_threshold
        adaBenturan = data.peak_magnitude >= self.impact_threshold
        jatuhBebasTerbaru = jatuhBebasSebelumnya or (adaJatuhBebas and data.min_before_peak)
        if adaJatuhBebas:
            self.freefall_at_ms = data.sent_at_ms

        if self.possible_since_ms is None:
            if adaBenturan and jatuhBebasTerbaru:
                self.possible_since_ms = data.sent_at_ms
                self.impact_peak = data.peak_magnitude
                self.still_count = 0
                return Decision("POSSIBLE_FALL", "Free-fall + benturan terdeteksi, memeriksa kondisi diam",
                                round(min(1.0, data.peak_magnitude / (self.impact_threshold * 3)), 3))
            if adaBenturan:
                return Decision("NORMAL", "Benturan tanpa free-fall (mis. HP diketuk/ditaruh keras)")
            return Decision("NORMAL", "Tidak ada pola jatuh")

        # ---- Tahap 2: setelah benturan, apakah HP diam (orang tidak bangun)?
        if data.sent_at_ms - self.possible_since_ms > self.possible_timeout_ms:
            self._reset()
            return Decision("NORMAL", "Waktu pengamatan habis tanpa kondisi diam yang cukup")
        if self._is_still(data):
            self.still_count += 1
            if self.still_count >= self.still_windows_needed:
                score = round(min(1.0, 0.5 + self.impact_peak / (self.impact_threshold * 4)), 3)
                self._reset()
                self.alarm_aktif = True
                return Decision("ALERT", "Terdeteksi jatuh: free-fall, benturan, lalu tidak bergerak", score)
            return Decision("POSSIBLE_FALL", f"Diam {self.still_count}/{self.still_windows_needed} window", 0.5)
        self.still_count = 0
        return Decision("POSSIBLE_FALL", "Masih bergerak setelah benturan, menunggu", 0.3)

