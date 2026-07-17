# PARS — Proje Notları

> KDE Plasma 6 için futbol fikstür/sonuç widget'ı. Anadolu parsından adını alır.
> Repo: github.com/parsapp/pars-plasmoid · Yerel: ~/projeler/pars-plasmoid

## Mimari felsefe (tek cümle)

**Widget aptal, üretici akıllı:** widget tek bir statik JSON'u çekip gösterir;
veri toplama, biçimleme, zamanlama tamamen üretici tarafındadır (cache-proxy).

Faydaları: kullanıcı başına API maliyeti sıfır · veri kaynağı widget'a
dokunmadan değiştirilebilir (elle giriş → cron script → LLM) · API anahtarı
asla widget'a girmez, sunucuda kalır.

## Veri sözleşmesi (JSON şeması)

```json
{
  "league": "Başlıkta görünen ad",
  "updated": "2026-07-17",
  "next": "Panel kompakt metni, örn: Final · Paz 22:00",
  "matches": [
    { "home": "İspanya", "away": "Arjantin", "score": "–", "info": "FİNAL · 19 Tem 22:00" }
  ]
}
```

- `score`: hazır metin ("2 - 1" veya oynanmadıysa "–")
- Feed şu an repoda: `data/worldcup.json`, GitHub raw üzerinden servis edilir
- Widget 30 dk'da bir yeniler (main.qml içinde Timer, 1800000 ms)

## Durum — biten aşamalar

- [x] 1. Hello world plasmoid (plasmoidviewer döngüsü)
- [x] 2. Statik liste (ListModel → delegate → ListView)
- [x] 2.5. Git + GitHub (gh cli ile push akışı)
- [x] 3. Uzak JSON'dan veri + 30dk yenileme
- [x] 4. Kompakt panel görünümü (`next` alanı → "⚽ Final · Paz 22:00")
- [x] Rebrand: Matchday → Pars (Id: com.parsapp.pars)

## Kalan yol

- [ ] Logo: Flux Schnell ile amblem adayları (branding/candidates/) → seçim
      → README + store görseli + sade SVG panel ikonu (metadata.json Icon)
- [ ] store.kde.org yayını (hesap + açıklama + görseller)
- [ ] FİNAL GECESİ (19 Tem 22:00, İspanya-Arjantin): skoru elle gir, Timer'ı
      geçici 300000 (5 dk) yap — GitHub raw CDN ~5 dk önbellek tutar
- [ ] Ayarlar sayfası: lig / özel feed URL seçimi
- [ ] Süper Lig feed'i (sezon açılınca; kaynak adayı: CollectAPI veya API-Football)
- [ ] Otomatik üretici: cron + API → JSON (match-night mode: maç saati 5dk,
      normalde saatlik)
- [ ] Sponsor satırı: "data provided by X" (reklam DEĞİL — KDE topluluğu
      widget'ta reklama alerjiktir; para modeli web/mobil tarafında)

## Refleks komutlar

```fish
# geliştirme döngüsü: değiştir → kapat → tekrar aç
plasmoidviewer --applet ~/projeler/pars-plasmoid/package
plasmoidviewer --applet package --formfactor horizontal   # panel/kompakt hali

# panele kurulu sürümü güncelle
kpackagetool6 --type Plasma/Applet --upgrade ~/projeler/pars-plasmoid/package

# yayınlama reflexi
git add . && git commit -m "mesaj" && git push
# "X işleme ileride" görürsen eksik olan şey: git push
```

## Sistem hatırlatmaları

- SD webui: /home/pars/sd/webui, servis: pars-sd.service ("pars" kullanıcısı)
  aç/kapa: sudo -u pars env XDG_RUNTIME_DIR=/run/user/1001 systemctl --user start|stop pars-sd.service
- VRAM kontrol: cat /sys/class/drm/card1/device/mem_info_vram_used
- Site beyni artık Gemini'de; GPU tamamen serbest
- Disk %85 dolu — büyük indirmelerde dikkat
