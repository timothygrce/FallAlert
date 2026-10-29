# FallAlert - Sistem Deteksi Jatuh dengan Dua HP dan MQTT

Tugas IoT Kelas A. HP Edge 1 dibawa lansia, HP Edge 2 dipegang keluarga.
Kalau lansia jatuh, HP keluarga bergetar dan dashboard menampilkan ALERT.

## Arsitektur
Edge 1 (HP lansia) dan Edge 2 (HP keluarga) -> MQTT (HiveMQ publik, TLS 8883) -> Detector (laptop) -> alerts -> Edge 2 bergetar + Dashboard

## Sensor dan Processing
- Accelerometer: RMS getaran, magnitude minimum (free-fall), magnitude puncak (benturan)
- Gyroscope: total rotasi (perubahan orientasi)

## Algoritma (rule-based state machine)
1. Free-fall: magnitude <= 4 m/s2
2. Benturan: magnitude puncak >= 15 m/s2 dalam 2 detik setelah free-fall
3. Diam: motion_rms < 0.8 dan rotasi < 0.3 selama 2 window berturut-turut -> ALERT
- Gerakan HP keluarga tidak membatalkan alarm; kedua HP dapat berada di lokasi berbeda.
- Benturan tanpa free-fall -> abaikan (HP diketuk/ditaruh keras)
- Alarm tetap tampil sampai keluarga memeriksa dan menekan ARM untuk mereset.

Ambang ini adalah nilai awal eksperimen, bukan hasil validasi medis. Nilai risk_score hanyalah skor aturan, bukan probabilitas atau hasil validasi klinis. Ponsel yang jatuh sendiri dapat memicu alarm, sedangkan jatuh tanpa fase free-fall yang terukur dapat terlewat. Urutan titik minimum dan puncak diperiksa, tetapi pengambilan sampel yang jarang bisa melewatkan kejadian; uji dengan data nyata dan sesuaikan ambang. Ini prototipe pembelajaran, bukan alat keselamatan medis. Alarm hanya dikirim sekali dan tidak disimpan untuk HP keluarga yang sedang offline. Broker publik tidak privat dan tidak menjamin alarm sampai; gunakan broker privat untuk data sensitif.

## Cara menjalankan
```
pip install -r requirements.txt
cp .env.example .env        # ganti PROJECT_ID unik
python detector.py          # laptop
python hp_pemilik.py        # HP keluarga (Termux)
python hp_dijaga.py         # HP lansia (Termux)
```
Tanpa HP: tambahkan `--source simulator --scenario fall` pada hp_dijaga.py.
Tes: `python -m unittest discover -s tests`

Untuk demo fisik, pastikan HP lansia dibawa pada posisi yang konsisten, kedua HP dan laptop memiliki internet, jam tersinkron, dan aplikasi tetap berjalan. Lakukan simulasi jatuh dengan aman memakai HP pada bantalan; jangan menjatuhkan seseorang. Uji juga aktivitas biasa, koneksi terputus, dan penerimaan notifikasi. Pengujian simulator tidak menggantikan pengujian perangkat nyata.

Dasar kode: github.com/myudak/contoh-project-iot1 (dimodifikasi).

**Penting setelah pembaruan:** jalankan kode versi yang sama pada kedua HP, laptop, dan halaman web. Telemetri lama tanpa `min_magnitude`, `peak_magnitude`, dan `min_before_peak` ditolak agar data tidak lengkap tidak dianggap normal.
