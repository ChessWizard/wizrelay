<!-- nav:top -->
[Dokümantasyon](README.md) › **15. Örnek: bir task baştan sona** &nbsp;·&nbsp; [English](../en/15-walkthrough.md)
<!-- /nav:top -->

# Örnek: bir task baştan sona

Tek bir task, tracker kaydından merge edilmiş PR'a kadar; her adımda gerçek dosya içerikleri
ve gerçek komut çıktılarıyla.

Bu bölümdeki her şey repoda [`examples/`](../../examples/) altında duruyor, yani okumak
yerine çalıştırabilirsin.

## Kurgu

**acme** ekibi `CU-86c1abcd` — "Tenant bazlı günlük API istek kotası" — task'ını iki
repoda uyguluyor.

```
acme/research-hub              ekip hub'ı (özel)
acme/api-service               rol: backend
acme/web-app                   rol: frontend
```

Organizasyon ve repo adları örnek; kendi adlarınla değiştir.

## Üç reponun dizin yapısı

### Hub

```
research-hub/
├── wizrelay-hub.json
├── CLAUDE.md                                  researcher protokolü
├── .mcp.json                                  ClickUp bağlantısı
├── policies/
│   └── routing-policy.json                    ekibin kendi yönlendirme politikası
├── templates/package/                         ekip paket şablonları (isteğe bağlı)
└── tasks/
    └── CU-86c1abcd-tenant-bazli-gunluk-api-istek-kotasi/
        ├── task.json                           ← kurallar
        ├── research.md                         ← analiz
        ├── scope.md                            ← sınır, düz metinle
        ├── acceptance.md                       ← "bitti" ne demek
        ├── decisions.md                        ← karar kaydı
        ├── contracts.md                        ← roller arası arayüz
        ├── roles/
        │   ├── backend.md
        │   └── frontend.md
        └── .validation.md                      ← özel; hub'dan çıkmaz
```

### Backend projesi, `init` ve `pull` sonrası

```
api-service/
├── CLAUDE.md                                  @.wizrelay/PROTOCOL.md eklendi
├── .claude/settings.json                      deny kuralları eklendi
├── .gitignore                                 iki satır eklendi
├── .mcp.json                                  ClickUp bağlantısı
├── app/
│   ├── quota/                              ← kapsam içi
│   ├── api/limits.py                       ← kapsam içi
│   └── billing/invoice.py                  ← açıkça yasak
├── tests/quota/                            ← kapsam içi
└── .wizrelay/
    ├── config.json                            hub, rol, tracker, dil
    ├── config.local.json                      kişisel, gitignore'da
    ├── profile.json                           repo profili
    ├── PROTOCOL.md                            çalışma kuralları
    ├── .active-task                           gitignore'da
    └── tasks/
        └── CU-86c1abcd-tenant-bazli-gunluk-api-istek-kotasi/
            ├── task.json, research.md, scope.md, acceptance.md,
            │   contracts.md, decisions.md, roles/*.md  ← salt okunur
            ├── .lock.json                              ← sürüm, hub commit'i, hash'ler, yönlendirme
            ├── plan.md                                 ← senin
            └── questions.md                            ← senin
```

Orada **olmayana** dikkat: `.validation.md` gelmedi. Nokta ile başlayan hiçbir şey gelmez.

---

## Pazartesi 10:00 — Researcher paketi başlatıyor

```bash
cd research-hub
claude --add-dir ../api-service --add-dir ../web-app
```

```
/wizrelay:hub-new 86c1abcd backend,frontend
```

```text
CU-86c1abcd taslak paketi tasks/CU-86c1abcd-tenant-bazli-gunluk-api-istek-kotasi
içinde oluşturuldu.
  + task.json
  + acceptance.md
  + contracts.md
  + decisions.md
  + research.md
  + roles/backend.md
  + roles/frontend.md
  + scope.md

Sıradaki: paketi doldurun, sonra /wizrelay:hub-validate CU-86c1abcd çalıştırın.
```

Claude ClickUp task'ını ve yorumlarını okudu, iki repoyu okudu ve Researcher için üç soru
bıraktı — developer'lar için değil.

## Pazartesi 11:30 — paket, dosya dosya

### `research.md`

```markdown
# Araştırma — CU-86c1abcd

## Problem

Tenant'lar API'ye günlük hiçbir sınır olmadan istek atabiliyor. Geçen ay yanlış yapılandırılmış
tek bir tenant paylaşılan üst kaynak kotasını tüketti ve diğer bütün tenant'ları bloke etti.

## Kanıtlı mevcut durum

`app/api/limits.py:14` tenant başına bir sayaç olmadan istekleri karşılıyor. Tek sınır
sağlayıcının global rate limit'i, `app/api/client.py:112` içinde uygulanıyor.

## Yaklaşım

Redis'te tenant başına günlük sayaç; gönderimden önce kontrol, başarılı gönderimden sonra
artırma. Sınır tenant'ın planından geliyor.

## Elenen alternatifler

| Alternatif | Neden olmaz |
|---|---|
| Postgres sayaç | Sıcak yolda mesaj başına bir yazma; Redis zaten oturum durumunu taşıyor. |
| Sağlayıcı tarafında kota | Sağlayıcı tenant başına değil hesap başına faturalıyor. |

## Riskler

| Risk | Etki | Azaltma |
|---|---|---|
| Redis erişilemez | Gönderimler kapalı ya da açık başarısız olur | Açık başarısız ol ve logla; kota bir güvenlik kontrolü değil. |
```

Mevcut duruma dair her iddia bir yol ve satır gösteriyor. Developer'ın güvenebileceği bir
analiz ile yeniden türetmek zorunda kalacağı bir analiz arasındaki fark bu.

### `acceptance.md`

```markdown
## AC-1 [backend] Günlük sınırındaki tenant reddedilir

Given günlük sayacı plan sınırına eşit bir tenant
When tenant bir istek daha yapar
Then istek 429 ve bir Retry-After başlığıyla reddedilir
Doğrulama: `pytest -q tests/quota/test_limit.py`

## AC-2 [backend] Kabul edilen istek sayacı artırır

Given sınırının altında bir tenant
When bir istek kabul edilir
Then tenant'ın günlük sayacı tam olarak bir artar
Doğrulama: `pytest -q tests/quota/test_counter.py`

## AC-3 [frontend] Kalan kota görünür

Given kullanım ekranındaki bir admin
When sayfa yüklenir
Then tenant için kalan günlük kota gösterilir
Doğrulama: `npm test -- quota-indicator`
```

### `contracts.md`

```markdown
## C-1 Kota durumu endpoint'i

- Üretici: backend
- Tüketici: frontend

### Biçim

{ "limit": 1000, "used": 240, "remaining": 760, "resets_at": "2026-10-31T00:00:00Z" }

### Kurallar

- `GET /api/tenants/{id}/quota`, başarıda 200, tenant yoksa 404.
- `remaining` asla negatif olmaz.
- Kota tarafından reddedilen bir istek 429 döner, `Retry-After` saniye cinsinden ve
  3600 ile sınırlı.
```

### `decisions.md`

```markdown
## D-001 Redis erişilemezken açık başarısız ol (v1, 2026-10-30)

- Soru: Sayaç deposuna erişilemediğinde isteğe ne olur?
- Karar: İsteğe izin ver ve bir uyarı logla. Kota bir maliyet kontrolü, güvenlik kontrolü
  değil; bir kesinti müşteri trafiğini durdurmamalı.
- Gerekçe: Sert bir hata, Redis olayını API kesintisine çevirir.
- Etki: AC-1 yalnızca sayaç okunabildiğinde geçerli.
```

### `task.json` — uygulanan kısım

```json
{
  "schema_version": 1,
  "id": "CU-86c1abcd",
  "tracker": { "type": "clickup", "ref": "86c1abcd" },
  "title": "Tenant bazlı günlük API istek kotası",
  "slug": "tenant-bazli-gunluk-api-istek-kotasi",
  "version": 1,
  "status": "published",
  "roles": ["backend", "frontend"],
  "repos": { "backend": "acme/api-service", "frontend": "acme/web-app" },
  "enforcement": "strict",
  "scope": {
    "backend": {
      "allow": ["app/quota/**", "app/api/limits.py", "tests/quota/**"],
      "deny": ["app/billing/**"]
    },
    "frontend": {
      "allow": ["src/features/usage/**"],
      "deny": []
    }
  },
  "routing": {
    "signals": { "complexity": "medium", "risk": "high", "ambiguity": "low" },
    "role_signals": { "frontend": { "complexity": "low", "risk": "low", "ambiguity": "low" } },
    "overrides": {}
  }
}
```

Üç şeye dikkat:

- `app/billing/**` `deny`'da, yalnızca `allow`'da olmaması yetmiyor. `deny`, `ask` modunda
  bile engelliyor.
- `tests/quota/**` `allow`'da. Testleri unutmak en yaygın kapsam hatası.
- `role_signals` frontend'in sinyallerini düşürüyor, ve iki repoya farklı tier veren şey bu.

## Pazartesi 11:45 — doğrulama

```
/wizrelay:hub-validate CU-86c1abcd
```

```text
## Doğrulama — CU-86c1abcd-tenant-bazli-gunluk-api-istek-kotasi

Hata ve uyarı yok.
```

Paket doldurulmadan önce aynı komut şunu diyordu — ve bu mekanizmanın çalışması, hatası
değil:

```text
### Hatalar (45) — bunlar yayını engeller
- acceptance.md:6: doldurulmamış yer tutucu {{Başlık}}
- acceptance.md:6: AC-1 bilinmeyen rol adlandırıyor '{{backend}}'
- acceptance.md:8: doldurulmamış yer tutucu {{başlangıç durumu}}
- …
```

İskelet hâlindeki bir paket, bir insan doldurana kadar kasten geçersiz.

## Pazartesi 12:00 — yayın

```
/wizrelay:hub-publish CU-86c1abcd
```

```text
CU-86c1abcd v1 olarak yayına hazırlandı.

Sıradaki: tasks/CU-86c1abcd-tenant-bazli-gunluk-api-istek-kotasi klasörünü commit edip
push edin, sonra `wizrelay hub comment CU-86c1abcd` çıktısını yorum olarak yazın.
```

Onay sonrası yorum:

```text
[WIZRELAY-PUBLISH] CU-86c1abcd — research v1 yayınlandı

Tenant bazlı günlük API istek kotası

**backend**
- AC-1: Günlük sınırındaki tenant reddedilir
- AC-2: Başarılı gönderim sayacı artırır

```
/wizrelay:pull CU-86c1abcd
```

Ya da oturumu doğrudan açın (tarayıcının adres çubuğuna yapıştırın):
```
claude-cli://open?repo=acme%2Fapi-service&q=%2Fwizrelay%3Apull%20CU-86c1abcd
```

**frontend**
- AC-3: Kalan kota görünür

```
/wizrelay:pull CU-86c1abcd
```

Ya da oturumu doğrudan açın (tarayıcının adres çubuğuna yapıştırın):
```
claude-cli://open?repo=acme%2Fweb-app&q=%2Fwizrelay%3Apull%20CU-86c1abcd
```
```

`q` parametresi tamamen kodlanmış — `%2Fwizrelay%3Apull` — ve bağlantı kod bloğunda, çünkü
GitHub `claude-cli://` bağlantılarını Markdown bağlantısından siliyor: etiketi bırakıp
URL'yi atıyor.

## Pazartesi 13:00 — backend developer çekiyor

```
/wizrelay:pull CU-86c1abcd
```

Gönderilen örnekten gerçek çıktı:

```text
CU-86c1abcd v1 — Tenant bazlı günlük API istek kotası
8 researcher dosyası kopyalandı.
Sizin için oluşturuldu: plan.md, questions.md
Kapsam içi: app/quota/**, app/api/limits.py, tests/quota/**

Yönlendirme: T4-high-risk (skor 10)
  plan       opus / xhigh
  implement  opus / high + advisor opus
  verify     opus / xhigh
  ask        opus / low
Uygulanan değiştiriciler: test_maturity_low, touches_critical_paths

Bu task'ın oturumunu şununla başlatın:
  claude --model opus --effort high --advisor opus --name 'CU-86c1abcd Tenant bazlı'
```

10 nereden geldi:

| Kaynak | Katkı |
|---|---|
| Paketin sinyalleri: complexity medium, risk high, ambiguity low | 2 + 3 + 1 = 6 |
| Bu reponun `test_maturity: low` değeri | +2 |
| Bu reponun `critical_paths` listesinin backend kapsamıyla kesişmesi | +2 |

Son ikisi 1 yerine 2 ediyor çünkü hub'ın kendi `policies/routing-policy.json` dosyası
varsayılan ağırlıkları geçersiz kılıyor. O dosyayı sil ve aynı task plugin'in
varsayılanlarıyla 8 alır — T3-critical.

## Pazartesi 13:10 — frontend developer aynı paketi çekiyor

```bash
cd ../web-app
```

```
/wizrelay:pull CU-86c1abcd
```

```text
Yönlendirme: T1-routine (skor 3)
  plan       sonnet / medium
  implement  sonnet / medium
  verify     sonnet / medium
  ask        sonnet / low

Bu task'ın oturumunu şununla başlatın:
  claude --model sonnet --effort medium --name 'CU-86c1abcd Tenant bazlı'
```

**Aynı hub, aynı paket, iki rol, iki tier.** Paket frontend rolünün sinyallerini düşürdü ve
o reponun profilinde hiçbir ek tetiklenmedi. Yönlendirmenin task başına değil rol başına
hesaplanmasının sebebi bu.

## Pazartesi 13:15 — oturum ne yaptığını biliyor

Her oturum başında ve her sıkıştırmadan sonra modele şu ulaşıyor:

```text
## Aktif araştırma paketi (wizrelay)
CU-86c1abcd v1 — Tenant bazlı günlük API istek kotası. Rol: backend. Kapsam modu: strict.
Researcher dosyaları (burada salt okunur): `acceptance.md`, `contracts.md`, `decisions.md`,
`research.md`, `roles/backend.md`, `roles/frontend.md`, `scope.md`, `task.json`
Kapsam içi: `app/quota/**`, `app/api/limits.py`, `tests/quota/**`
Açıkça yasaklı: `app/billing/**`
Yönlendirme: T4-high-risk, skor 10. Uygulama opus üzerinde high effort ile yürür.

Bu rolün kabul kriterleri (2):
- AC-1: Günlük sınırındaki tenant reddedilir
- AC-2: Başarılı gönderim sayacı artırır

Plan ilerlemesi: 1 adımdan 0 tamamlandı. Sıradaki: AC-1 — sayaç ve gönderim öncesi kontrol
questions.md içinde 1 soru hâlâ açık.

Çalışma kuralları .wizrelay/PROTOCOL.md içinde, CLAUDE.md üzerinden içe aktarılıyor.
```

Ve her prompt'ta tek satır:

```text
[WIZRELAY] Aktif task CU-86c1abcd · research v1 · rol backend · kapsam modu strict · açık soru 1
```

## Pazartesi 13:30 — kontroller, gösterimle

Gönderilen örnekten gerçek kararlar:

| Dosya | Hüküm | Neden |
|---|---|---|
| `app/quota/service.py` | **izin verildi** | `app/quota/**` ile eşleşiyor |
| `app/billing/invoice.py` | **deny** | `deny` kalıbı `app/billing/**` ile eşleşiyor |
| `README.md` | **deny** | rolün kapsamı dışında, ve mod `strict` |
| `.wizrelay/tasks/…/acceptance.md` | **deny** | researcher dosyası, her modda salt okunur |
| `.wizrelay/tasks/…/plan.md` | **izin verildi** | developer dosyası |
| `poetry.lock` | **izin verildi** | her derinlikte yan ürün |
| `CLAUDE.md` | **izin verildi** | `init` yazdı; yan ürün |
| `/etc/hosts` | **karar yok** | repo dışında; plugin karışmıyor |

Developer'ın gerçekte gördüğü ret:

```text
README.md, CU-86c1abcd kapsamının dışında. Kapsam içi: app/quota/**,
app/api/limits.py, tests/quota/**. Kapsamı yerel olarak genişletmek yerine
/wizrelay:ask ile soru açın.
```

Ve bir researcher dosyası için:

```text
acceptance.md Researcher'a aittir ve burada salt okunurdur (CU-86c1abcd). /wizrelay:ask ile
sorun; yanıt yeni bir paket sürümü olarak gelir.
```

## Pazartesi 15:00 — paketin yanıtlamadığı bir soru

```
/wizrelay:ask Retry-After için üst sınır var mı?
```

`contracts.md#C-1` "3600 ile sınırlı" dediği için bu paketten, kaynağıyla yanıtlanıyor.
Yanıtlanmamış olduğunu varsayalım:

```text
Paket bunu yanıtlamıyor. contracts.md C-1 Retry-After'ı saniye cinsinden belirtiyor ama üst
sınır söylemiyor, ve decisions.md'de bununla ilgili bir şey yok.

questions.md'ye Q-001 olarak kaydettim:

  ## Q-001 Retry-After üst sınırı
  Durum: AÇIK
  Soruldu: 2026-10-30
  Bağlam: AC-1'i engelliyor

  Retry-After saniye cinsinden belirtilmiş, maksimum yok. Seçenekler: (a) 3600 saniyeyle
  sınırla, (b) bir sonraki UTC gece yarısına kalan süreyle sınırla, (c) sınır yok. Yanıt
  olmazsa (b)'yi uygularım, çünkü kota penceresi günlük — ama risk, bir istemci
  kütüphanesinin büyük bir değeri kesin durma olarak ele alması.

Bunu tracker'a [WIZRELAY-Q] olarak göndereyim mi?
```

Onay olmadan hiçbir şey gönderilmiyor. Ve hiçbir yanıt uydurulmuyor — sistemdeki tek en
önemli davranış bu, çünkü Researcher'ın hiç vermediği makul bir yanıt karar gibi görünür ve
uygulanır.

## Pazartesi 16:00 — Researcher yanıtlıyor

```
/wizrelay:hub-inbox
```

`decisions.md`'ye eklenen karar:

```markdown
## D-002 Retry-After bir saatle sınırlı (v2, 2026-10-30)

- Soru: Q-001 — Retry-After için üst sınır nedir?
- Karar: 3600 saniyeyle sınırla.
- Gerekçe: Daha büyük bir değer istemcileri takılmış gösterir, ve kota penceresi zaten bir
  günü aşmıyor.
- Etki: AC-1 ve contracts.md'deki C-1.
```

Sonra `/wizrelay:hub-publish CU-86c1abcd` → v2, ve yanıt:

```text
[WIZRELAY-A] Q-001 → D-002
Retry-After 3600 saniyeyle sınırlı. research v2 yayında; /wizrelay:sync çalıştırın.
```

## Salı 09:00 — developer sync yapıyor

Oturum başlangıcı:

```text
CU-86c1abcd: sizde v1 var, hub'da v2. Devam etmeden önce /wizrelay:sync çalıştırın.
```

```
/wizrelay:sync
```

Gerçek çıktı:

```text
CU-86c1abcd v1 sürümünden v2 sürümüne güncellendi.
Değişti: acceptance.md, decisions.md, task.json
Hub'dan geri yüklendi (yerelde değiştirilmişlerdi): scope.md

--- a/decisions.md
+++ b/decisions.md
@@ -8,2 +8,9 @@
  - Gerekçe: Sert bir hata, Redis olayını API kesintisine çevirir.
  - Etki: AC-1 yalnızca sayaç okunabildiğinde geçerli.
+
+## D-002 Retry-After bir saatle sınırlı (v2, 2026-10-30)
+
+- Soru: Q-001 — Retry-After için üst sınır nedir?
+- Karar: 3600 saniyeyle sınırla.

decisions.md değişti. Yeniden okuyun, sonra plan.md dosyasını güncelleyip yanıtlanan
soruları kapatın.
```

Tek komutta üç şey oldu: sürüm ilerledi, yerelde düzenlenmiş bir researcher dosyası geri
kondu, ve `decisions.md` değişenler arasında olduğu için sonraki adım mesajı değişti.

## Salı 14:00 — doğrulama

```
/wizrelay:verify
```

```text
# Doğrulama — CU-86c1abcd

Doğrulayan: wizrelay:test-engineer

Sonuç: KISMİ

## Kabul kriterleri

| AC | Kanıt (komut) | Sonuç |
|---|---|---|
| AC-1 | `pytest -q tests/quota/test_limit.py` (3 passed) | GEÇTİ |
| AC-2 | `pytest -q tests/quota/test_counter.py` (1 passed) | GEÇTİ |
| AC-3 | — | UYGULANMAZ (frontend rolü) |

Tüm paket: `pytest -q` — 184 passed.

## Kapsam denetimi

## Kapsam denetimi — CU-86c1abcd (backend)
İhlal yok. Değişen 6 yolun tamamı açıklanabilir.

## Doğrulanamayanlar

D-001'deki Redis-erişilemez yolunun testi yok. Önerilen:
tests/quota/test_counter_store_unavailable.py
```

`GEÇTİ` değil `KISMİ`, çünkü paketteki bir kararın arkasında test yok. Doğrulayıcı o testi
**yazamaz** — düzenleme araçları yapılandırmayla kaldırılmış — bu yüzden boşluk sessizce
kapatılmak yerine raporlanıyor.

## Salı 15:00 — boşluk, sonra yeşil

Developer ana oturumdan eksik testi yazmasını istiyor, sonra `/wizrelay:verify`'ı tekrar
çalıştırıyor:

```text
Sonuç: GEÇTİ
```

Ve onay sonrası tracker yorumu:

```text
[WIZRELAY-VERIFY] CU-86c1abcd — backend — GEÇTİ
```

## Salı 15:30 — PR

```bash
git add app/quota tests/quota app/api/limits.py .wizrelay/tasks/
git commit -m "feat(quota): tenant bazlı günlük API istek kotası (AC-1, AC-2)"
git push -u origin feature/CU-86c1abcd-tenant-kota
```

`.wizrelay/tasks/` klasörünü commit etmek, CI kapısının kapsamı bilmesini sağlayan şey. Dal
adı kimliği taşıyor, kapının task'ı bulma yolu da bu.

CI:

```text
## Kapsam denetimi — CU-86c1abcd (backend)
İhlal yok. Değişen 7 yolun tamamı açıklanabilir.

### Kapsam içinde (5)
- app/api/limits.py
- app/quota/__init__.py
- app/quota/service.py
- tests/quota/test_counter.py
- tests/quota/test_limit.py

### Yan ürün (derleme çıktıları ve wizrelay kurulumu)
- poetry.lock
```

Yeşil. Merge.

Ve developer billing'e de dokunmuş olsaydı:

```text
2 ihlal bulundu.

### Açıkça yasaklanmış
- `app/billing/invoice.py` — `app/billing/**`

### Bu rolün kapsamı dışında
- `README.md`
```

Çıkış kodu 1, kontrol kırmızı, merge engelli. Oturumun iyi davranmasına bağlı olmayan
katman bu.

---

## Aynı döngünün üç başka biçimi

### Yanlış çıkan bir kapsam

Backend developer `Retry-After` başlığını eklemek için `app/core/errors.py`'ye ihtiyaç
duyuyor. v1 kapsamında yok.

1. Claude düzenlemeyi deniyor; hook engelliyor ve nedenini açıklıyor.
2. Developer gerekçeyi `questions.md`'ye Q-002 olarak yazıyor ve `/wizrelay:ask` gönderiyor.
3. Researcher `/wizrelay:hub-inbox` ile görüyor, dosyayı `allow`'a ekliyor, gerekçesiyle
   D-003'ü yazıyor ve v3'ü yayınlıyor.
4. `/wizrelay:sync`, ve dosya artık düzenlenebilir.

Tek bir sessiz düzenleme yerine dört adım — ve sonunda task'taki her developer kapsamın
değiştiğini ve nedenini biliyor.

### Mekanik bir task

"Tüm hata mesajlarını i18n kataloğuna taşı."

- Researcher `routing.signals.kind: "mechanical"` ve dar bir kapsam ayarlıyor
  (`src/i18n/**`, `src/components/errors/**`).
- `pull` T0 öneriyor: uygulama `haiku`, doğrulama `sonnet`.

Bir yeniden adlandırma Opus gerektirmez, ve yönlendirme bunun her seferinde tahmin edilmek
yerine bir kez karara bağlandığı yer.

### Kişisel bir proje, GitHub Issues ile

1. Özel bir `personal-hub` aç ve `/wizrelay:hub-init` çalıştır: tracker `github`, rol
   `backend`.
2. Projende: `/wizrelay:init backend git@github.com:sen/personal-hub.git`.
3. `#42` issue'su için: `/wizrelay:hub-new 42 backend` → paket `GH-42-…` olur.
4. Geri kalanı birebir aynı. Bu hub ekibinkinden tamamen ayrı — hub kimliğine göre
   anahtarlanmış farklı önbellekler, yani aynı kimlik ikisinde de olsa karışmaz.

## Kendin çalıştır

```bash
cp -R examples/hub examples/dev-backend examples/dev-frontend /tmp/wizrelay-demo/
cd /tmp/wizrelay-demo
for d in hub dev-backend dev-frontend; do (cd $d && git init -q -b main . && git add -A && git commit -qm init); done

cd hub             && wizrelay hub validate CU-86c1abcd
cd ../dev-backend  && wizrelay pull CU-86c1abcd && wizrelay route
cd ../dev-frontend && wizrelay pull CU-86c1abcd && wizrelay route
```

Örnek hub `hub.path` kullanıyor, yani hiçbir şey klonlanmıyor ve ağ kullanılmıyor. Sonra
bilerek bir şeyi boz:

```bash
cd ../dev-backend
echo "x" >> app/billing/invoice.py
echo "y" > README.md
wizrelay audit --base ""     # 1 ile çıkar ve ikisini de adlandırır
```

## Sonraki

Bir şey burada olduğu gibi davranmadığında
[16. Sorun giderme](16-troubleshooting.md).

<!-- nav:bottom -->
---

| ← | ↑ | → |
|:---|:---:|---:|
| [← 14. Özelleştirme](14-customisation.md) | [İçindekiler](README.md) | [16. Sorun giderme →](16-troubleshooting.md) |
<!-- /nav:bottom -->
