<!-- nav:top -->
[Dokümantasyon](README.md) › **9. Soru ve sürüm döngüsü** &nbsp;·&nbsp; [English](../en/09-question-loop.md)
<!-- /nav:top -->

# Soru ve sürüm döngüsü

Bir developer sorduktan sonra Researcher'ın ne yaptığı ve yanıtın neden bir yorum değil bir
sürüm olması gerektiği.

## Yorum neden yetmez

Developer sorar; Researcher tracker'da yanıtlar; developer uygular. Bu bir kez işe yarar, o
developer için.

Herkes için başarısız olur. Paketi okuyan bir sonraki oturum tracker'ı görmez. Arayüzün
diğer yanını uygulayan diğer rol görmez. Ve üç hafta sonra kimse uygulamanın analize mi, bir
yorum dizisinde verilmiş bir yanıta mı uyduğunu söyleyemez.

Bu yüzden **her yanıt `decisions.md`'de bir `D-<nnn>` kaydı olur ve paket yeni bir sürüm
alır.** Tracker yanıtı karara işaret eder; karar değildir.

## 1. Gelen kutusu

```
/wizrelay:hub-inbox
```

1. Yayınlanmış task'lardaki yanıtlanmamış `[WIZRELAY-Q]` yorumlarını toplar.
2. Her soru için:
   - Paket zaten yanıtlıyorsa ilgili bölümü gösteren kısa bir yanıt taslağı hazırlar.
   - Yanıtlamıyorsa seçenekleri, etkilerini (hangi kriterler, sözleşmeler, kapsam ve roller)
     ve bir karar önerisini çıkarır.
3. Onayladığın kararları `decisions.md`'ye ekler (`## D-004 … (v2, tarih)`) ve gereken
   kriter, sözleşme ve kapsam dosyalarını güncelleyer.
4. Soru yorumunu `[WIZRELAY-A] Q-001 → D-004` ile yanıtlar.
5. Paket değiştiyse `/wizrelay:hub-validate` ve `/wizrelay:hub-publish` önerir.

## Dört tür soru

Hangisiyle karşı karşıya olduğunu bilmek kararın ne söylemesi gerektiğini değiştirir. Gelen
kutusu her birinin hangisi olduğunu düşündüğünü söyler; kontrol et.

| Tür | Ne olmuş | Karar ne yapar |
|---|---|---|
| **Paket sessiz** | Gerçekten karar verilmemiş | Karar ver |
| **Yanıt var ama bulunabilir değil** | `research.md` içinde, kimsenin bakmadığı yerde | Yine de karar olarak kaydet, sonraki sefer doğru yerde olsun |
| **Önerme yanlış** | Developer kapsamı ya da bir sözleşmeyi yanlış okumuş | Netleştir ve neyin yanlış okunduğunu söyle — bu genellikle paketin belirsiz olduğu anlamına gelir |
| **Kapsam yanlış** | Task gerçekten yayınlanan kapsamın dışında bir şey gerektiriyor | Bir kapsam değişikliği, orijinal kapsamın gördüğü değerlendirmeyi hak eden |

İkinci tür farkedilmeye değen olan. Bir developer orada olan bir yanıtı bulamadıysa, sonraki
developer da bulamayacak. Onu `decisions.md`'ye taşımak bürokrasi değil; insanların baktığı
yere koymak.

## 2. Kararı yazmak

```markdown
## D-004 Retry-After bir saatle sınırlı (v2, 2026-10-30)
- Soru: Q-001 — Retry-After için üst sınır nedir?
- Karar: 3600 saniyeyle sınırla.
- Gerekçe: Daha büyük bir değer istemcileri takılmış gösterir, ve kota penceresi zaten bir
  günü aşmıyor.
- Etki: AC-1 ve contracts.md'deki C-2
```

İki kural:

**Karar daha fazla yoruma gerek bırakmadan uygulanabilir olmalı.** Developer senin kararını
uygulamak için bir şeye karar vermek zorunda kalıyorsa, karar bitmemiş.

**`Etki` alanını dürüst doldur.** Bir kriterin değişmesi gerekiyorsa söyle — ve aynı sürümde
değiştir. Güncellemediği bir kriterle çelişen bir karar, hiç karar olmamasından kötüdür.

## 3. Yayınla ve yanıtla

`/wizrelay:hub-publish CU-86c1abcd`, kararları adlandıran bir özetle. Sonra yanıt, onayınla:

```text
[WIZRELAY-A] Q-001 → D-004
Retry-After 3600 saniyeyle sınırlı. Gerekçe: daha büyük bir değer istemcileri takılmış
gösterir.
research v2 yayında; reponda /wizrelay:sync çalıştır.
```

## 4. Durum

```
/wizrelay:hub-status CU-86c1abcd
```

| Rol | Son rapor | Sonuç | Eksik | Kapsam |
|---|---|---|---|---|
| backend | 2026-11-02 | KISMİ | AC-3 KAPSANMADI | temiz |
| frontend | 2026-11-01 | GEÇTİ | — | temiz |

Açık soruları, her birinin ne kadar süredir beklediğiyle de listeler — sayfadaki en zaman
duyarlı bilgi bu. Bir karara takılmış developer, çalışmayan developer.

## Kapsam genişletme talepleri

Bir developer'ın kapsam dışı bir dosyaya ihtiyaç duyduğunu bildirmesi — örneğin
`app/core/errors.py` — alacağın en yaygın soru. Akış:

1. Talebi değerlendir. Kriter bunu gerçekten gerektiriyor mu?
2. Gerektiriyorsa dosyayı `task.json`'daki `allow` listesine ekle ve gerekçeyi
   `decisions.md`'ye yaz.
3. Yeni sürümü yayınla.

`/wizrelay:sync` sonrası developer dosyayı düzenleyebilir.

"Daha fazla soru gelmesin" diye kapsamı cömertçe genişletme dürtüsüne direnin. İşten geniş
bir kapsam korumayı anlamsızlaştırır, ve sorular analizin eksik olduğunun sinyaliydi.

## Tracker olmadan döngü

`tracker: none` ile döngü yine kapanır — sadece soruyu taşıyacak bir insana ihtiyaç duyar:

1. Developer'ın `/wizrelay:ask`'i `Q-001`'i `questions.md`'ye yazar.
2. `questions.md` developer'ın reposunda durur, bu yüzden soruyu ekip nasıl iletişim
   kuruyorsa öyle iletirler.
3. Researcher kararı kaydeder ve yeni bir sürüm yayınlar.
4. Developer'ın bir sonraki oturumu bunu bildirir ve `/wizrelay:sync` getirir.

Dikkat edilecek tek şey: Researcher'a bir sorunun beklediğini hatırlatan bir mekanizma yok.
`ask` skill'i bir soru yazarken bunu söylüyor.

## Sonraki

[10. Model ve effort yönlendirmesi](10-routing.md).

<!-- nav:bottom -->
---

| ← | ↑ | → |
|:---|:---:|---:|
| [← 8. Developer: task'ı uygulamak](08-developer-workflow.md) | [İçindekiler](README.md) | [10. Model ve effort yönlendirmesi →](10-routing.md) |
<!-- /nav:bottom -->
