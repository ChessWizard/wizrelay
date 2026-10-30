<!-- nav:top -->
[Dokümantasyon](README.md) › **7. Researcher: hazırlamak ve yayınlamak** &nbsp;·&nbsp; [English](../en/07-researcher-workflow.md)
<!-- /nav:top -->

# Researcher: hazırlamak ve yayınlamak

Bir task paketini dosya dosya yazmak ve developer'lar çekebilmeden önce geçtiği iki kapı.

## Akış

```
/wizrelay:hub-new  →  paketi yaz  →  /wizrelay:hub-validate  →  /wizrelay:hub-publish
     (v0, taslak)                    (engelleyici var mı?)      (v1, yayında)
```

Taslak paketler developer'lara görünmez; yalnızca yayınlanmış bir paket çekilebilir.

## Adım 1 — Paketi başlat

Hub reposunda Claude Code'u aç. Claude'un ilgili projelerin kodunu da okumasını istiyorsan
onları ekle:

```bash
cd research-hub
claude --add-dir ../api-service --add-dir ../web-app
```

Sonra:

```
/wizrelay:hub-new 86c1abcd backend,frontend
```

Claude şunları yapar:

1. Tracker'dan task'ı okur: başlık, açıklama, alt görevler **ve yorumlar**.
2. Şablondan klasörü oluşturur:
   `tasks/CU-86c1abcd-tenant-bazli-gunluk-api-istek-kotasi/` (`version: 0`, `status: draft`).
3. Eklediğin repoları salt okunur inceler ve bulgularını dosya yollarıyla kaynaklar.
4. Paket dosyalarının taslağını yazar.
5. Çözemediği noktaları **sana** sorar. Bu sorular developer'lara devredilmez; senin
   kararınla `decisions.md`'ye girer.

Bu komut yüksek effort'la çalışır; kapsamlı bir task'ta birkaç dakika sürebilir.

Yorumlar üzerinde ısrar edilmeye değen kısım. Tracker tartışmaları açıklamaya hiç ulaşmayan
kararlar taşır, ve bunları kaçıran bir paket ekibin çoktan çözdüğü bir soruyu yeniden sorar.

## Adım 2 — Paketi yazmak, dosya dosya

### `research.md` — analiz

Önerilen bölümler:

1. Problem ve ölçülebilir hedef
2. Kanıtlı mevcut durum
3. Seçilen yaklaşım
4. Elenen alternatifler
5. Roller arası etkileşim
6. Riskler ve kenar durumlar
7. Kapsam özeti
8. Varsayımlar

İyi bir analizde **her iddia bir kaynağa dayanır** — "`app/api/v1/messages.py:48` içindeki
`send_template_message`…" — ve hiçbir şey yoruma davet eden biçimde yazılmaz. "Uygun
şekilde", "gerekirse" ve "düzgünce ele al" silinecek ifadeler.

Kanıtsız iddia bir research paketindeki en yaygın kusurdur, ve en pahalısı: developer ona
güvenir.

### `acceptance.md` — kabul kriterleri

Developer'ın neyi "bitti" sayacağını ve `/wizrelay:verify`'ın neyi kanıtlayacağını belirler.

```markdown
## AC-1 [backend] Kota aşımında istek 429 ile reddedilir
- **Given** `basic` planlı bir tenant bugün (UTC) 1.000 istek yapmış
- **When** 1.001. istek için `POST /v1/exports` çağrılır
- **Then** yanıt `429`, gövde `contracts.md#C-2` ile birebir; istek karşılanmaz
- **Doğrulama:** `tests/quota/test_quota_exceeded.py`
```

| Kötü yazım | Sorunu | İyi yazım |
|---|---|---|
| "Kota aşılınca uygun hata dönülmeli" | "Uygun" yoruma açık | "Yanıt 429, gövde C-2 ile birebir" |
| "Performans iyi olmalı" | Ölçülemez | "p95 < 200 ms (yerel, 1.000 istek)" |
| Başlıkta rol yok | Hangi reponun uygulayacağı belirsiz | `## AC-1 [backend] …` |
| Doğrulama satırı yok | Neyin kanıt sayılacağı belirsiz | `**Doğrulama:** tests/quota/…` |

Köşeli parantezdeki rol listesini boş bırakırsan kriter tüm rollere uygulanır.

### `contracts.md` — roller arası sözleşme

Backend ile frontend'in birebir uyacağı endpoint ve event şemaları ile hata gövdeleri.
Bir alan adı ya da hata kodu **yalnızca** burada tanımlanır; kriterler ve rol dosyaları
buraya atıf yapar.

```markdown
## C-1 Kota kullanım endpoint'i
- Üretici: backend · Tüketici: frontend
- `GET /v1/tenants/{tenant_id}/quota/template-messages`
- 200 yanıtı: `{ "used": 250, "limit": 1000, "warning_threshold": 0.8, "resets_at": "2026-10-30T00:00:00Z" }`
```

### `decisions.md` — karar kaydı

```markdown
## D-001 Kota günü UTC'ye göre sıfırlanır (v1, 2026-10-29)
- Karar: Sayaç günü UTC tarihine göre belirlenir.
- Gerekçe: Tenant saat dilimi verisi tutarlı değil.
- Etki: AC-1, AC-4
```

**Kararlar silinmez.** Bir karar değişirse yeni bir karar eklenir ve eskisine "Geçersiz
kılındı: D-00x" yazılır. İki karar çeliştiğinde en yenisi geçerlidir.

`Karar` alanını daha fazla yoruma gerek bırakmadan uygulanabilecek biçimde yaz. "Bunu
düzgünce ele al" karar değildir. "429 döndür ve `Retry-After`'ı 3600 saniyeyle sınırla"
karardır.

### `roles/<rol>.md` — rolün dilimi

Bu rolün işi, ona uygulanan kriterler, ipuçları (yön gösterir, bağlamaz), tuzaklar ve test
beklentisi.

Tuzaklar bölümü başka kimsenin üretemeyeceği kısım. "Sağlayıcı gönderimi onaylamadan
artırmak başarısız bir gönderimi iki kez saydırır" türü bir bilgi, makul bir developer'ın
bir kez yanlış yaptığı ve bir öğleden sonraya mal olan şeydir.

### `scope.md` — kapsamın anlatımı

Sınırların neden orada olduğu; nelere dokunulmayacağı ve nedeni. Burada bariz bir
iyileştirme gören bir developer'ın, bunun gözden kaçma değil karar olduğunu bilmesi
gerekir.

### `task.json` — makine-okunur tanım

Plugin'in kurallarını belirleyen dosya bu. Elle düzenlediğin alanlar: `roles`, `repos`,
`enforcement`, `scope`, `routing`. `version`, `status`, `updated_at` ve `changelog`
alanlarına dokunma — yayın komutu onları yönetir.

```json
{
  "scope": {
    "backend": {
      "allow": ["app/quota/**", "app/api/v1/messages.py", "app/api/v1/tenants.py",
                "app/core/errors.py", "alembic/versions/**", "tests/quota/**"],
      "deny": ["app/billing/**", "app/consumers/**", "app/auth/**"]
    },
    "frontend": {
      "allow": ["src/features/quota/**", "src/api/quota.ts", "src/lib/http/errors.ts"],
      "deny": ["src/features/billing/**"]
    }
  }
}
```

Kapsam yazarken:

- **Dar başla.** Developer gerçekten başka bir dosyaya ihtiyaç duyarsa soru gelir ve
  genişletirsin. Gereğinden geniş bir kapsam korumayı anlamsızlaştırır.
- **Yan dosyaları unutma.** Testler, migration'lar ve çeviri dosyaları da kapsama girer.
- **Kritik alanları `deny`'a yaz.** `deny`, `ask` modunda bile engeller.
- Glob kuralları [11. Kapsam koruması](11-scope-protection.md)'nda.

Kapsam modu:

| Mod | Kapsam dışı düzenleme | Ne zaman |
|---|---|---|
| `strict` | Engellenir | Varsayılan; kapsamı net işler |
| `ask` | Developer'a sorulur | Keşif gerektiren, kapsamı tam çizilemeyen işler |
| `off` | Serbest (Researcher dosyaları yine korunur) | Spike ya da prototip |

Yönlendirme sinyalleri [10. Yönlendirme](10-routing.md)'de.

`repos` alanı rolü bir GitHub `owner/repo` ile eşler; yayın yorumundaki deep link'ler
bundan üretilir.

### Ek dosyalar

Pakete istediğin dosyayı ekleyebilirsin — `sequence.md`, `api-examples.json` — ve hepsi
developer'a salt okunur gider. **Nokta ile başlayan dosyalar** (`.notes/`,
`.validation.md`) sende kalır ve developer'a hiç gitmez.

## Adım 3 — Doğrulamak

```
/wizrelay:hub-validate CU-86c1abcd
```

Doğrulama iki aşamalı.

**1. Yapısal, deterministik.**

| Hatalar (yayını engeller) | Uyarılar (engellemez) |
|---|---|
| Doldurulmamış `{{…}}` yer tutucuları | `TODO` |
| `TBD` ya da `???` | `ambiguity: high` |
| Bilinmeyen rol adlandıran bir kriter | Çok rollü pakette boş `contracts.md` |
| Hiç kriteri olmayan bir rol | Doğrulama satırı olmayan bir kriter |
| Boş `allow` listesi | Given/When/Then içermeyen bir kriter |
| Geçersiz glob | |

Her bulgu bir `dosya:satır` taşır.

**2. Anlamsal, `research-critic` ajanı tarafından.** Şunlara bakar:

- Tracker'daki her gereksinimin bir kriteri var mı?
- Kriterler, yazmayan biri tarafından test edilebilir mi?
- Dosyalar birbiriyle çelişiyor mu — `contracts.md`'deki bir alan adı kriterdekinden farklı
  mı?
- Kapsam kriterleri uygulamaya yetiyor mu?

Sonuç `.validation.md`'ye yazılır ve hub'da kalır. Engelleyici bir bulgu dururken hiçbir şey
yayınlanmaz.

## Adım 4 — Yayınlamak

```
/wizrelay:hub-publish CU-86c1abcd
```

Sırasıyla:

1. Bu sürümün tek cümlelik özetini sorar (ilk yayında "İlk yayın").
2. Yapısal doğrulamayı tekrar çalıştırır ve hata varsa durur.
3. `task.json`'u günceller: `version` 0 → 1, `status: published`, changelog girişi.
4. Commit atar: `research(CU-86c1abcd): v1 — İlk yayın`.
5. Onayınla push eder ya da PR açar.
6. Onayınla tracker'a yorum yazar:

```text
[WIZRELAY-PUBLISH] CU-86c1abcd — research v1 yayınlandı
Özet: İlk yayın
- backend: AC-1, AC-2, AC-3, AC-4
- frontend: AC-5, AC-6
Başlamak için ilgili repoda Claude Code içinde:
/wizrelay:pull CU-86c1abcd
Deep link (tarayıcının adres çubuğuna yapıştırın):
- backend: claude-cli://open?repo=acme%2Fapi-service&q=%2Fwizrelay%3Apull%20CU-86c1abcd
- frontend: claude-cli://open?repo=acme%2Fweb-app&q=%2Fwizrelay%3Apull%20CU-86c1abcd
```

Deep link, developer'ın bilgisayarında Claude Code'u ilgili repoda açar ve komutu hazır
yazılmış **ama gönderilmemiş** getirir — Enter'a basarlar. Bazı platformlar, GitHub dahil,
özel şemalı bağlantıları siler; bu yüzden kod bloğu içinde metin olarak verilir.

Özet satırı göründüğünden önemli: developer'ın `/wizrelay:sync` sırasında okuduğu şey o.
"güncellemeler" değil, neyin neden değiştiğini yaz.

## Sürüm kuralları

- **Yayınlanmış bir paketi değiştirmek yeni sürüm demektir:** düzenle → doğrula → yayınla
  (v2).
- **Git geçmişini asla yeniden yazma.** Force push yapma; developer'ların kilit dosyaları
  commit'lere bağlı.
- **Arşivleme:** iptal edilen bir task için `task.json`'daki `status`'u elle `archived` yap
  ve commit et. Durum alanını elle düzenlemenin tek istisnası bu. Arşivlenmiş bir paket
  yeniden çekilemez.

## Claude olmadan

Aynı akış komut satırından yürür:

```bash
wizrelay hub new 86c1abcd --title "Tenant bazlı günlük API istek kotası" --roles backend,frontend
# paket dosyalarını düzenle
wizrelay hub validate CU-86c1abcd
wizrelay hub publish-prep CU-86c1abcd --summary "İlk yayın"
git add tasks && git commit -m "research(CU-86c1abcd): v1 — İlk yayın" && git push
wizrelay hub comment CU-86c1abcd     # çıktıyı tracker'a yorum olarak yapıştır
```

Tamamen elle de olur: `templates/package/` klasörünü `tasks/<ID>-<slug>/` olarak kopyalayıp
doldur. `hub validate` o paketi de birebir aynı kurallarla kontrol eder.

## Yayından önce — kontrol listesi

- [ ] Her tracker gereksinimi en az bir kritere bağlı
- [ ] Her kriterin rolü, Given/When/Then'i ve bir komut adlandıran doğrulama satırı var
- [ ] Roller arası her arayüz `contracts.md`'de, kimliğiyle tanımlı
- [ ] Açık soru kalmadı; kararlar `decisions.md`'de
- [ ] Mevcut duruma dair her iddia bir yol gösteriyor
- [ ] Kapsam dar, testleri ve migration'ları içeriyor, kritik alanlar `deny`'da
- [ ] Sinyaller yüksek sesle söyleyebileceğin bir gerekçeyle seçildi
- [ ] `/wizrelay:hub-validate` engelleyici göstermiyor

## Sonraki

[8. Developer: task'ı uygulamak](08-developer-workflow.md) — devrin diğer yanı.

<!-- nav:bottom -->
---

| ← | ↑ | → |
|:---|:---:|---:|
| [← 6. Bir repoyu bağlamak](06-connect-repository.md) | [İçindekiler](README.md) | [8. Developer: task'ı uygulamak →](08-developer-workflow.md) |
<!-- /nav:bottom -->
