<!-- nav:top -->
[Dokümantasyon](README.md) › **Ek A — Komut referansı** &nbsp;·&nbsp; [English](../en/appendix-a-commands.md)
<!-- /nav:top -->

# Ek A — Komut referansı

Her komut, kimin kullandığı ve CLI karşılığı.

## Claude Code komutları

| Komut | Kim | Ne yapar | CLI karşılığı |
|---|---|---|---|
| `/wizrelay:init [rol] [hub]` | Ekip lideri | Repoyu hub'a bağlar | `wizrelay init --role … --hub …` |
| `/wizrelay:doctor` | Herkes | Ortam ve yapılandırma kontrolü | `wizrelay doctor` |
| `/wizrelay:pull <ID>` | Developer | Paketi çeker, aktif yapar, model önerir | `wizrelay pull <ID>` |
| `/wizrelay:plan` | Developer | Kapsam içi plan, `plan.md`, `/goal` önerisi | — |
| `/wizrelay:ask <soru>` | Developer | Paketten kaynaklı yanıt; yoksa `[WIZRELAY-Q]` | — |
| `/wizrelay:verify` | Developer | Bağımsız doğrulama, `verification.md`, `[WIZRELAY-VERIFY]` | `wizrelay audit` + projenin test komutları |
| `/wizrelay:sync` | Developer | Yeni sürümü alır, etkiyi işler | `wizrelay sync` |
| `/wizrelay:status` | Developer | Durum ve uyarılar | `wizrelay status` |
| `/wizrelay:hub-init` | Researcher / lider | Hub iskeleti | `wizrelay hub init <dizin>` |
| `/wizrelay:hub-new <ref> [roller]` | Researcher | Paket taslağı | `wizrelay hub new <ref> --title … --roles …` |
| `/wizrelay:hub-validate <ID>` | Researcher | Yapısal + anlamsal doğrulama | `wizrelay hub validate <ID>` |
| `/wizrelay:hub-publish <ID>` | Researcher | Sürüm, commit, duyuru | `hub publish-prep` + git + `hub comment` |
| `/wizrelay:hub-inbox [ID]` | Researcher | Soruları yanıtlar, karar yazar | — |
| `/wizrelay:hub-status [ID]` | Researcher | Doğrulama raporlarının özeti | — |

CLI karşılığı olmayan dört komut, işi mekanik değil muhakeme olanlar.

## Yalnızca CLI'da

| Komut | Ne yapar |
|---|---|
| `wizrelay route [--json]` | Aktif task'ın yönlendirme tablosu ve başlatma komutu |
| `wizrelay activate <klasör>` / `--clear` | Aktif task'ı elle seçer ya da temizler |
| `wizrelay brief [--phase …] [--session ID]` | Bir skill'in enjekte ettiği bağlam. **Her zaman 0 ile çıkar** |
| `wizrelay audit [--base REF] [--task REF \| --branch AD] [--require-task] [--format md\|json] [--no-fail]` | Kapsam ve bütünlük denetimi |
| `wizrelay migrate --from-prototype` | Prototip `.ai/` yapısını `.wizrelay/`'e taşır |
| `wizrelay hub list [--json]` | Hub'daki paketleri listeler |
| `wizrelay hub comment <ref>` | Yayın yorumu metnini üretir |
| `wizrelay hook <event>` | Hook işleyicisi. Doğrudan kullanım için değil |

## Çıkış kodları

| Kod | Anlamı |
|---|---|
| `0` | Başarı |
| `1` | İhlal ya da doğrulama hatası — iş yanlış, çağrı doğruydu |
| `2` | Kullanıcı ya da yapılandırma hatası — çağrı yanlış |
| `3` | Beklenmeyen bir iç hata |

`brief` kuralı kanıtlayan istisna: **her zaman** 0 ile çıkar, çünkü bir skill onu enjekte
ediyor ve orada sıfır olmayan bir çıkış, Claude içeriğin hiçbirini görmeden tüm skill
çağrısını iptal eder.

Her okuma komutunun `--json` çıktısı bir `schema_version` taşır ve sürümler arasında geriye
uyumludur.

## Kısa komutlar

| Kısa yazılabilir | Her zaman tam yazılır |
|---|---|
| `/pull`, `/ask`, `/verify`, `/sync` | `/wizrelay:plan` |
| `/hub-init`, `/hub-new`, `/hub-validate` | `/wizrelay:init` |
| `/hub-publish`, `/hub-inbox`, `/hub-status` | `/wizrelay:status`, `/wizrelay:doctor` |

Sağdaki dördü Claude Code'un yerleşik komutlarıyla çakışıyor.

## Tracker'lar

| Tracker | Kanonik | Kabul edilen giriş | URL neye ihtiyaç duyar | MCP | v1 seviyesi |
|---|---|---|---|---|---|
| ClickUp | `CU-86c1abcd` | `86c1abcd`, `CU-86c1abcd`, task URL'si | hiçbir şey | **doğrulandı**: `https://mcp.clickup.com/mcp` (OAuth) | tam |
| GitHub Issues | `GH-123` | `123`, `#123`, `owner/repo#123`, URL | `tracker.repo` | doğrulanmadı — `gh` kullan | tam |
| Jira | `PROJ-123` | `PROJ-123`, `proj-123`, URL | `tracker.base_url` | doğrulanmadı | beta |
| Linear | `ENG-123` | `ENG-123`, `eng-123`, URL | `tracker.workspace` | doğrulanmadı | beta |
| Azure DevOps | `AB-123` | `123`, `AB#123`, URL | `tracker.base_url`, `tracker.project` | doğrulanmadı | beta |
| none | ne isim verirsen | güvenli her ad | — | — | tam |

`beta`, kimlik işleme ve URL üretiminin test edildiği, okuma ve yorum yazmanın ise senin
erişimine bağlı olduğu anlamına geliyor.

**Doğrulanmamış bir uç nokta yapılandırmana asla yazılmaz.** ClickUp için
`wizrelay init --tracker clickup` sunucuyu `.mcp.json`'a ekler ve tarayıcıda bir kez
yetkilendirirsin. Diğer her adaptör için `init` onun yerine talimat yazdırır — tahmin
edilmiş bir uç nokta, plugin bozukmuş gibi görünen bir şekilde başarısız olur ve kimlik
bilgilerini yanlış host'a yöneltebilir.

Her adaptör ayrıca bir skill'in gerektiğinde okuduğu bir talimat dosyası taşıyor:
`plugin/trackers/<type>.md`.

### Kimlik biçimleri

Bunların hepsi aynı paketi bulur:

```bash
wizrelay pull 86c1abcd
wizrelay pull CU-86c1abcd
wizrelay pull https://app.clickup.com/t/86c1abcd
wizrelay pull CU-86c1abcd-tenant-kota        # paket klasörünün adı
```

Kendi şeması olan bir ekip `tracker.id_prefix` ayarlar ve o önek kanonik olanı olur:
`id_prefix: "TASK-"` ile hem `123456` hem `TASK-123456` `TASK-123456`'ya çözümlenir.

Jira ve Linear kimlikleri büyük/küçük harfe duyarsız eşleşir ve büyütülür, yani `proj-123`
çalışır.

## Ortam değişkenleri

| Değişken | Ne yapar |
|---|---|
| `WIZRELAY_DEBUG=1` | stderr'e tanılama, ve beklenmeyen bir hatada yığın izi |
| `WIZRELAY_PYTHON` | `bin/wizrelay` başlatıcısının yorumlayıcısı |
| `WIZRELAY_CACHE_DIR` | Önbellek konumunu değiştirir |
| `WIZRELAY_TRACKERS_DIR` | Pip ile kurulan CLI için tracker kataloğunun yeri |

<!-- nav:bottom -->
---

| ← | ↑ | → |
|:---|:---:|---:|
| [← 17. Sık sorulan sorular](17-faq.md) | [İçindekiler](README.md) | [Ek B — Dosya referansı →](appendix-b-files.md) |
<!-- /nav:bottom -->
