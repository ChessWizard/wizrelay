<!-- nav:top -->
[Dokümantasyon](README.md) › **Ek B — Dosya referansı** &nbsp;·&nbsp; [English](../en/appendix-b-files.md)
<!-- /nav:top -->

# Ek B — Dosya referansı

Sistemin oluşturduğu ya da okuduğu her dosya, sahibi ve commit edilip edilmediği.

## Hub reposu

| Dosya | Sahip | Commit | Ne |
|---|---|---|---|
| `wizrelay-hub.json` | Researcher | Evet | Hub kimliği ve ekip varsayılanları. Varlığı bir dizini hub yapan şey |
| `CLAUDE.md` | Researcher | Evet | Researcher protokolü |
| `.mcp.json` | Researcher | Evet | Tracker bağlantısı |
| `policies/routing-policy.json` | Researcher | Evet | Ekibin model ve effort politikası |
| `templates/package/` | Researcher | Evet | Ekip paket şablonları |
| `tasks/<ID>-<slug>/*` | Researcher | Evet | Paketler |
| `tasks/<ID>-<slug>/.validation.md`, `.notes/` | Researcher | Evet | Hub'da kalır; asla yayınlanmaz |

## Proje reposu

| Dosya | Sahip | Commit | Ne |
|---|---|---|---|
| `.wizrelay/config.json` | Ekip | Evet | Hub, rol, tracker, dil |
| `.wizrelay/config.local.json` | Sen | **Hayır** | Kişisel ayarlar |
| `.wizrelay/profile.json` | Ekip | Evet | Repo profili |
| `.wizrelay/PROTOCOL.md` | Plugin | Evet | Çalışma kuralları; `init` yazar |
| `.wizrelay/.active-task` | Sen | **Hayır** | Aktif task işaretçisi |
| `.wizrelay/tasks/<klasör>/` researcher dosyaları | Researcher | Evet | Salt okunur kopya |
| `.wizrelay/tasks/<klasör>/.lock.json` | Plugin | Evet | Sürüm, hub commit'i, hash'ler, yönlendirme |
| `.wizrelay/tasks/<klasör>/plan.md`, `questions.md`, `verification.md` | Developer | Evet | Çalışma dosyaların |
| `.wizrelay/tasks/<klasör>/notes/` | Developer | Evet | Notların |
| `CLAUDE.md` | Proje | Evet | `init` bir import satırı ekler |
| `.claude/settings.json` | Proje | Evet | `init` deny kurallarını ekler |
| `.gitignore` | Proje | Evet | `init` iki satır ekler |

## Paket dosyaları ve sahiplik

| Dosya | Sahip | Zorunlu | İçerik |
|---|---|---|---|
| `task.json` | Researcher | evet | Makine-okunur tanım |
| `research.md` | Researcher | evet | Problem, kanıtlı mevcut durum, yaklaşım, elenen alternatifler, riskler |
| `scope.md` | Researcher | evet | Kapsamın anlatımı ve gerekçesi |
| `acceptance.md` | Researcher | evet | Kabul kriterleri |
| `decisions.md` | Researcher | evet | Karar kaydı |
| `contracts.md` | Researcher | birden çok rol varsa | Roller arası arayüzler |
| `roles/<rol>.md` | Researcher | her rol için | Rolün dilimi, ipuçları, tuzaklar, test beklentisi |
| diğer `*.md` ve dosyalar | Researcher | hayır | Diyagramlar, akışlar; otomatik dahil olur |
| `.*` (ör. `.validation.md`, `.notes/`) | Researcher (özel) | hayır | **Asla yayınlanmaz** |
| `plan.md`, `questions.md`, `verification.md`, `notes/` | Developer | — | Hub'dan asla kopyalanmaz, aynı adda bir dosya orada olsa bile |

## Dosyalar çeliştiğinde öncelik

```
decisions.md  >  task.json + scope.md  >  contracts.md  >  acceptance.md  >  roles/<rol>.md  >  research.md
(en yeni)        (kapsam)                 (arayüzler)      (davranış)        (dilim)            (gerekçe)
```

Bu sıra `.wizrelay/PROTOCOL.md` içine yazılı ve her oturum onu yüklüyor.

## Kopyalama güvenliği

`pull` şunları adıyla reddeder, böylece mesaj uygulanabilir olur:

- sembolik bağlar, paketin içine ya da dışına işaret etmelerinden bağımsız
- mutlak yollar ve her `..` segmenti
- düzenli dosya olmayan her şey
- 5 MB'ı aşan bir dosya ya da toplamda 20 MB'ı aşan bir paket
- `^[A-Za-z0-9][A-Za-z0-9._-]{0,120}$` kalıbına uymayan bir klasör adı

Ret, hiçbir şey yazılmadan **önce** olur, yani kötü bir paket yarı kopyalanmış bir klasör
bırakmaz.

## `.lock.json`

```json
{
  "schema_version": 1,
  "task_id": "CU-86c1abcd",
  "tracker_ref": "86c1abcd",
  "title": "Tenant bazlı günlük API istek kotası",
  "folder": "CU-86c1abcd-tenant-bazli-gunluk-api-istek-kotasi",
  "version": 2,
  "status": "published",
  "hub_commit": "f95f2307ad3c",
  "hub_id": "acme-research-hub-2e807908",
  "pulled_at": "2026-10-30T09:12:44+00:00",
  "role": "backend",
  "files": { "research.md": "<sha256>", "roles/backend.md": "<sha256>" },
  "routing": { "tier": "T4-high-risk", "score": 10, "phases": {}, "launch": "claude --model opus …" }
}
```

`hub_id`, aynı makinedeki iki hub'ı ayrı tutan şey: normalize edilmiş bir kimlik, yani
`git@github.com:acme/research-hub.git` ile `https://github.com/acme/research-hub.git` aynı
değeri üretirken farklı bir hub farklı bir değer üretir.

Hash'leme CRLF'yi LF'ye normalize eder, böylece hub'ın Windows checkout'u ile aynı commit'in
macOS checkout'u anlaşır. Bu olmadan `sync` her seferinde tüm paketi bozuk raporlardı.

## Veri sözleşmeleri

Her JSON dosyası `schema_version: 1` taşıyor. JSON Schema dosyaları
[`schemas/`](../../schemas/) altında, draft 2020-12 biçiminde, ve çalışma zamanı aynı
kuralları standart kütüphaneyle uyguluyor. İkisi aynı fikstürlere karşı test ediliyor, bu
yüzden birbirinden ayrışamıyorlar.

| Şema | Doküman |
|---|---|
| `task.schema.json` | `task.json` |
| `config.schema.json` | `.wizrelay/config.json` ve `config.local.json` |
| `profile.schema.json` | `.wizrelay/profile.json` |
| `lock.schema.json` | `.lock.json` |
| `routing-policy.schema.json` | `policies/routing-policy.json` |
| `wizrelay-hub.schema.json` | `wizrelay-hub.json` |

## Plugin'in kendi dosyaları

Kaynağı okuyorsan referans olsun diye:

```
plugin/
├── .claude-plugin/plugin.json    manifest
├── hooks/hooks.json              beş olay, exec biçimi
├── bin/wizrelay, wizrelay.py     iki başlatıcı
├── skills/<ad>/SKILL.md          14 skill
├── agents/*.md                   3 subagent
├── trackers/*.{json,md}          6 adaptör
├── config/routing-policy.json    varsayılan politika
├── templates/{dev,hub}/{en,tr}/  init ve hub-init'in yazdıkları
├── evals/                        davranış test vakaları
└── lib/wizrelay/                 çekirdek kütüphane, yalnızca stdlib
```

<!-- nav:bottom -->
---

| ← | ↑ | → |
|:---|:---:|---:|
| [← Ek A — Komut referansı](appendix-a-commands.md) | [İçindekiler](README.md) | [Ek C — Tracker yorum etiketleri →](appendix-c-tracker-tags.md) |
<!-- /nav:bottom -->
