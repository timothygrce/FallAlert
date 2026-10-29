"""Demonstrasi algoritma tanpa broker atau perangkat fisik."""
from nodes.detector_service.rules import FallDetector
from shared.messages import Telemetry


def main():
    detektor = FallDetector()
    waktuAwal = 1_790_000_000_000
    tahapan = [(1, 9.81, 9.81), (9, 1, 28), (0.1, 9.81, 9.81), (0.1, 9.81, 9.81)]
    for urutan, (gerakan, minimum, puncak) in enumerate(tahapan):
        waktu = waktuAwal + urutan * 1000
        data = Telemetry("edge1", "demo", urutan, waktu, gerakan, 0, minimum, puncak, minimum < 4 and puncak >= 15)
        hasil = detektor.accept(data, now_ms=waktu)
        print(f"{urutan + 1}. {hasil.status}: {hasil.reason}")
    print("Simulasi saja; uji MQTT dan sensor fisik secara terpisah.")


if __name__ == "__main__":
    main()
