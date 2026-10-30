<!-- nav:top -->
[Dokümantasyon](README.md) › **1. Genel bakış** &nbsp;·&nbsp; [English](../en/01-overview.md)
<!-- /nav:top -->

# Genel bakış

wizrelay'in ne olduğu, çözdüğü problem ve oluştuğu üç parça.

## Çözdüğü problem

Researcher bir task'ı analiz eder ve analizini ekiple paylaşır. Her developer ise kendi
Claude Code oturumunda çalışır ve her oturum o analizi biraz farklı yorumlar. Sonuç: kapsam
dışı değişiklikler, roller arası sözleşme uyumsuzlukları ve buglar.

wizrelay bu konuda üç şey yapar:

1. **Analizi her oturuma birebir aynı şekilde taşır**, tek bir kaynaktan.
2. **Kapsamı Claude'a bırakmaz** — kurallarla korur.
3. **Yanıtsız bir soruyu developer'ın tahminine bırakmaz** — soruyu Researcher'a geri
   döndürür.

## Üç parça

| Parça | Ne | Kaç tane | Benzetme |
|---|---|---|---|
| **Plugin** (`wizrelay`) | Claude Code'a komut, otomatik kontrol ve yardımcı ajan ekleyen araç. Hiçbir ekibin analizini içermez. | Dünyada tek ürün; herkes kurar | ClickUp uygulaması |
| **Hub** | Ekibin analiz paketlerinin durduğu özel git reposu. Kod içermez. | **Ekip** başına bir tane | Şirketin ClickUp workspace'i |
| **Proje repoları** | Developer'ların kodları. Her biri bir kez hub'a bağlanır. | İstediğin kadar | Workspace'teki projeler |

```
                PLUGIN (wizrelay) — herkesin Claude Code'unda kurulu
                                │  okur / yazar
                                ▼
                 EKİP HUB'I  (acme/research-hub)
                 tasks/CU-86c1abcd-…/    tasks/CU-91f2aa10-…/
                                │  /wizrelay:pull
          ┌─────────────────────┼─────────────────────┐
          ▼                     ▼                     ▼
          api-service           web-app               deploy-infra
          rol: backend          rol: frontend         rol: infra
          .wizrelay/            .wizrelay/            .wizrelay/
```

### Adlar

| Öğe | Değer |
|---|---|
| Ürün, repo, marketplace | `wizrelay` — üçü için tek ad |
| Plugin | `wizrelay` — tüm komutlar `/wizrelay:` ile başlar |
| Kurulum kimliği | `wizrelay@wizrelay` |
| CLI (CI ve terminal) | `wizrelay` |
| Projedeki klasör / hub işaretçisi | `.wizrelay/` / `wizrelay-hub.json` |
| Tracker etiketleri | `[WIZRELAY-PUBLISH]`, `[WIZRELAY-Q]`, `[WIZRELAY-A]`, `[WIZRELAY-VERIFY]` |

En sık karıştırılan nokta: **hub proje başına değil, ekip başına açılır.** Ekibe yeni bir
proje reposu eklemek yeni hub gerektirmez; o repo mevcut hub'a bağlanır.

## Kim ne yapar

| Rol | Sorumluluğu | Kullandığı komutlar |
|---|---|---|
| Researcher | Task'ı analiz eder, paketi yazar, doğrular, yayınlar; soruları yanıtlar | `/wizrelay:hub-*` |
| Developer | Paketi çeker, planlar, uygular, gerektiğinde sorar, kendi doğrulamasını yapar | `/wizrelay:pull`, `plan`, `ask`, `verify`, `sync`, `status` |
| Ekip lideri / kurulumcu | Hub'ı kurar, repoları bağlar, ekip ayarlarını yönetir | `/wizrelay:hub-init`, `/wizrelay:init`, `/wizrelay:doctor` |
| CI | PR'larda kapsam denetimi yapar | `wizrelay audit` |

## Bir task'ın yolculuğu

```
Tracker'da task (CU-86c1abcd)
   │
   ▼
[Researcher] /wizrelay:hub-new → paketi yaz → /wizrelay:hub-validate → /wizrelay:hub-publish (v1)
   │                                                      └─► Tracker: [WIZRELAY-PUBLISH]
   ▼
[Developer] /wizrelay:pull → /wizrelay:plan → uygula (kontroller devrede) → /wizrelay:verify
   │                │                                                  └─► Tracker: [WIZRELAY-VERIFY]
   │                └─► soru: /wizrelay:ask ──► Tracker: [WIZRELAY-Q]
   │                                             │
   │        [Researcher] /wizrelay:hub-inbox → decisions.md → /wizrelay:hub-publish (v2)
   │                                             └─► Tracker: [WIZRELAY-A], [WIZRELAY-PUBLISH]
   ▼
[Developer] oturum açılışında "v2 var" uyarısı → /wizrelay:sync → devam
   │
   ▼
PR → CI: wizrelay audit → merge
```

## Neden böyle tasarlandı

**Tek doğruluk kaynağı.** Analiz yalnızca hub'da yazılır. Projelerdeki kopyalar salt
okunurdur ve her dosyanın hash'i tutulur; yerel bir düzenleme sessiz kalmaz, tespit edilir.

**Talimat değil kural.** Claude'a "kapsam dışına çıkma" demek yetmez. Plugin, kapsam dışı
düzenlemeyi Claude Code seviyesinde engeller — kararın olasılıksal olmadığı yerde.

**Belirsizlik geri döner.** Pakette cevabı olmayan bir soru, developer'ın tahminiyle değil
Researcher'ın kararıyla kapanır ve yeni sürüm olarak herkese ulaşır.

## Bir paket ne içerir

Paket hem düz metin hem veridir, kasıtlı olarak:

- **Düz metin** insanın okuduğu kısım. `research.md` nedenini, `scope.md` sınırın nerede
  olduğunu, `roles/<rol>.md` tuzakları anlatır.
- **Veri** araçların uyguladığı kısım. `task.json` kapsam glob'larını, sinyalleri ve kapsam
  modunu taşır.

Düz metin ikna eder; korkuluğu gerçek yapan veridir. Kapsamı yalnızca düz metinle yazmak
uygulanacak bir şey bırakmazdı. Yalnızca glob'ları yazmak anlaşılacak bir şey bırakmazdı.

İki dosya örtüşen şeyler söylediğinde sabit bir öncelik sırası çözer ve o sıra her oturumun
yüklediği protokole yazılıdır:

```
decisions.md  >  task.json + scope.md  >  contracts.md  >  acceptance.md  >  roles/<rol>.md  >  research.md
(en yeni)        (kapsam)                 (arayüzler)      (davranış)        (dilim)            (gerekçe)
```

`decisions.md` kazanır çünkü üzerinde en son anlaşılan şeydir. `research.md` kaybeder çünkü
gerekçedir, ve gerekçe bir kararın geçersiz kılmasına izin verilen şeydir.

## Sonraki

[2. Ne yapar, ne yapmaz](02-scope.md) sınırı çiziyor — bu aracın kasten dokunmadığı yerler
dahil.

<!-- nav:bottom -->
---

| ← | ↑ | → |
|:---|:---:|---:|
| &nbsp; | [İçindekiler](README.md) | [2. Ne yapar, ne yapmaz →](02-scope.md) |
<!-- /nav:bottom -->
