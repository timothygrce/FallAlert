# Memahami FallAlert

HP pengguna membaca accelerometer dan gyroscope. Accelerometer menghasilkan RMS perubahan magnitudo, magnitudo minimum, dan magnitudo maksimum. Gyroscope menghasilkan total gerakan sudut selama window.

Detector mencari magnitudo rendah, kemudian benturan dalam dua detik, lalu dua window diam. Jika terpenuhi, detector mengirim alarm. Status alarm tetap aktif sampai di-reset melalui ARM. Gerakan HP keluarga tidak membatalkan deteksi.

Nilai ambang masih bersifat percobaan. Urutan titik minimum dan maksimum diperiksa, tetapi sampel yang jarang dapat melewatkan kejadian. Uji beberapa aktivitas biasa dan simulasi jatuh yang aman sebelum menarik kesimpulan.
