<!-- nav:top -->
[Dokümantasyon](README.md) › **Ek C — Tracker yorum etiketleri** &nbsp;·&nbsp; [English](../en/appendix-c-tracker-tags.md)
<!-- /nav:top -->

# Ek C — Tracker yorum etiketleri

Dört etiket, tam ilk satırları ve yorum yazma kuralları.

## Etiketler

| Etiket | Yazan | Ne zaman | İlk satır |
|---|---|---|---|
| `[WIZRELAY-PUBLISH]` | Researcher | Paketin her yayınında | `[WIZRELAY-PUBLISH] <ID> — research v<N> yayınlandı` |
| `[WIZRELAY-Q]` | Developer | Paketin yanıtlamadığı bir soru | `[WIZRELAY-Q] Q-<nnn> — <ID> — <rol>` |
| `[WIZRELAY-A]` | Researcher | Yanıt, soruyu karara eşleyerek | `[WIZRELAY-A] Q-<nnn> → D-<nnn>` |
| `[WIZRELAY-VERIFY]` | Developer | Doğrulama raporu | `[WIZRELAY-VERIFY] <ID> — <rol> — <GEÇTİ/KALDI/KISMİ>` |

**Etiket ilk satırın en başında olmak zorunda.** `hub-inbox` ve `hub-status` bu yorumları
sonradan böyle buluyor; cümle ortasındaki bir etiket onlar için görünmez.

## Kurallar

**Açık onay olmadan hiçbir şey gönderilmez.** Bu yorumların her biri Claude tarafından,
tracker'ın MCP araçlarıyla ve ancak sen evet dedikten sonra yazılır. Bir yorum task'taki
herkese görünür, yani senin adına yapılacak bir şey değil.

**Tracker içeriği veridir, talimat değil.** Bir task açıklaması ya da yorumu bir asistana
hitap eden metin içeriyorsa skill'ler onu sana alıntılar ve uygulamaz. Her skill bunu kendi
metninde söylüyor.

**Researcher etiketlenir** — yapılandırmada `researcher_mention` ayarlıysa bir
`[WIZRELAY-Q]` yorumunda.

## Tam örnekler

### Yayın

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

### Soru

```text
[WIZRELAY-Q] Q-001 — CU-86c1abcd — backend
Retry-After için üst sınır?

contracts.md C-1 Retry-After'ı saniye cinsinden belirtiyor ama maksimum söylemiyor, ve
decisions.md'de bununla ilgili bir şey yok.

Seçenekler: (a) 3600 saniyeyle sınırla, (b) bir sonraki UTC gece yarısına kalan süreyle
sınırla, (c) sınır yok. Yanıt olmazsa (b)'yi uygularım, çünkü kota penceresi günlük. Risk,
bir istemci kütüphanesinin büyük bir değeri kesin durma olarak ele alması.

Engellediği: AC-1
```

### Yanıt

```text
[WIZRELAY-A] Q-001 → D-002
Retry-After 3600 saniyeyle sınırlı. Gerekçe: daha büyük bir değer istemcileri takılmış
gösterir, ve kota penceresi zaten bir günü aşmıyor.
research v2 yayında; reponda /wizrelay:sync çalıştır.
```

### Doğrulama raporu

```text
[WIZRELAY-VERIFY] CU-86c1abcd — backend — KISMİ
- AC-1 GEÇTİ — pytest tests/quota/test_limit.py (3 passed)
- AC-2 GEÇTİ — pytest tests/quota/test_counter.py (1 passed)
- AC-3 KAPSANMADI — D-001'deki Redis-erişilemez yolunun testi yok
Kapsam denetimi: temiz · Research bütünlüğü: temiz
```

## Deep link'ler

Bir deep link, okuyucunun bilgisayarında Claude Code'u doğru repoda açar ve komutu hazır
yazılmış **ama gönderilmemiş** getirir — okur ve Enter'a basar.

```
claude-cli://open?repo=acme%2Fapi-service&q=%2Fwizrelay%3Apull%20CU-86c1abcd
```

| Parametre | Ne yapar |
|---|---|
| `repo` | GitHub `owner/name` kısaltması. Claude Code bunu daha önce gördüğü bir klona çözümler |
| `q` | Ön-doldurulacak metin. URL kodlanmış; satır sonu için `%0A`; en fazla 5000 karakter |

Bilinmesi gereken iki şey:

- **Deep link yalnızca `repos` girişinde bir repo adı olan rol için üretilir.** Makineler
  arası çözümlenen tek parametre `repo`.
- **GitHub `claude-cli://` bağlantılarını siliyor.** Markdown bağlantısı etiket metnine
  dönüşüyor ve URL kayboluyor, bu yüzden bağlantı her zaman bir kod bloğunda. Bu her
  renderer'da hayatta kalıyor ve okuyucu kopyalıyor.

Oturum repo yerine ana dizinde açılıyorsa, `repo` kısaltması yalnızca Claude Code'un daha
önce gördüğü klonlara çözümleniyor — klonun içinde bir kez `claude` çalıştırmak yolunu
kaydediyor.

## Tracker başına notlar

Her adaptör bir skill'in gerektiğinde yüklediği bir talimat dosyası taşıyor. Onları açmadan
bilinmeye değenler:

**ClickUp.** Task'ı, açıklamayı **ve tüm yorumları** oku — ClickUp tartışmaları açıklamaya
hiç ulaşmayan kararlar taşır. Özel alanlara dikkat: ClickUp ekipleri öncelik, sprint ya da
bileşeni genellikle etiket yerine oraya koyuyor.

**GitHub Issues.** Doğrulanmış MCP uç noktası yok, bu yüzden alışılmış yol `gh`:
`gh issue view 123 --repo acme/web --comments`. Etiketler genellikle bileşeni ve önceliği
taşıyor. Ve yorum yazmadan önce repoyu kullanıcıyla doğrula.

**Jira.** Issue türüne ve iş akışı durumuna dikkat — bir Story ile bir Bug farklı kabul
beklentisi taşır — bağlı issue'lara, özellikle "blocks" ve "is blocked by", ve genellikle
gerçek deadline olan sprint ya da fix version'a.

**Linear.** Alt issue'lar önemli: bir üst issue genellikle gerçek task'tır ve alt issue'lar
rollerdir. Project ve cycle deadline'ı taşıyor.

**Azure DevOps.** Özel bir **Acceptance Criteria** alanı var ve ekipler onu kullanıyor. Area
path genellikle doğrudan bir role karşılık geliyor.

**none.** Hiçbir yere yorum gönderilmiyor ve deep link yok. `hub comment` yine rol başına
kriterleri ve pull komutunu üretiyor; ekip nerede konuşuyorsa oraya yapıştırabilirsin.

<!-- nav:bottom -->
---

| ← | ↑ | → |
|:---|:---:|---:|
| [← Ek B — Dosya referansı](appendix-b-files.md) | [İçindekiler](README.md) | [Ek D — Kontrol listeleri →](appendix-d-checklists.md) |
<!-- /nav:bottom -->
