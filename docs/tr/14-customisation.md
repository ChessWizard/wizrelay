<!-- nav:top -->
[Dokümantasyon](README.md) › **14. Özelleştirme** &nbsp;·&nbsp; [English](../en/14-customisation.md)
<!-- /nav:top -->

# Özelleştirme

Her ayar, nerede durduğu ve ikisi çeliştiğinde hangi katmanın kazandığı.

## Hızlı tablo

| İstediğin | Nerede | Nasıl |
|---|---|---|
| Projeye özel kurallar (ör. migration biçimi) | Projenin `CLAUDE.md`'si | Normal şekilde yaz; plugin protokolüyle birlikte okunur |
| Projeye özel komut | `.claude/skills/<ad>/SKILL.md` | Çakışma yok: plugin komutları `/wizrelay:` ad alanında |
| Mesaj dili | `.wizrelay/config.json` → `language` | `tr` ya da `en` |
| Mesaj başına hatırlatıcıyı kapatmak | `.wizrelay/config.json` → `prompt_anchor: false` | |
| Oturum adının task'a göre konmasını kapatmak | `.wizrelay/config.json` → `session_title: false` | |
| Hub'ı yerel kopyadan okumak | `.wizrelay/config.local.json` → `hub.path` | [6. Repoyu bağlamak](06-connect-repository.md) |
| Ekibe özel paket şablonları | Hub'daki `templates/package/` | `hub-new` bunları kullanır |
| Model politikası | Hub'daki `policies/routing-policy.json` | [10. Yönlendirme](10-routing.md) |
| Plugin'i bir projede kapatmak | Projenin `.claude/settings.json`'u | [4. Plugin'i kurmak](04-install-plugin.md) |
| Kapsam dışında değişebilecek dosyalar | `.wizrelay/profile.json` → `incidental_allow` | [11. Kapsam koruması](11-scope-protection.md) |
| Bir task'ın kapsam modu | `task.json` → `enforcement` | Researcher ayarlar |

## Yapılandırma katmanları

En düşük öncelikten. Üst katman alttakini geçersiz kılar; **nesneler derin birleşir, diziler
değiştirir**.

| # | Katman | Nerede | Sahibi |
|---|---|---|---|
| 1 | Kütüphane varsayılanları | derlenmiş | plugin |
| 2 | Hub varsayılanları | `wizrelay-hub.json`, `init` sırasında kopyalanır | researcher'lar |
| 3 | Proje, paylaşılan | `.wizrelay/config.json` — commit edilir | ekip |
| 4 | Proje, kişisel | `.wizrelay/config.local.json` — gitignore'da | sen |
| 5 | Task | Paketteki `task.json` | researcher |

Nesneler derin birleşiyor ki `config.local.json` `hub.repo`'yu tekrarlamadan `hub.path`
ayarlayabilsin. Diziler birikmek yerine değiştiriyor çünkü bir yol listesi tek bir karar —
katmanlar arası birleşen bir `critical_paths` listesi hakkında akıl yürütmek imkânsız
olurdu.

`_` ile başlayan bir anahtar yorumdur ve doğrulamadan önce atılır. JSON'un yorum sözdizimi
yok, ve bir hub kendi dosyalarını böyle açıklıyor:

```json
{
  "_comment": "test_maturity düşük çünkü kota modülünün henüz testi yok.",
  "schema_version": 1,
  "test_maturity": "low"
}
```

## Projenin mevcut yapısıyla birlikte yaşamak

Plugin çakışmamak üzere kurulmuş:

- **Komutlar ad alanında.** `plan` adlı bir proje skill'i ile `/wizrelay:plan` birlikte
  yaşar. `/plan` projenin kendisini çalıştırır, `/wizrelay:plan` plugin'inkini.
- **`init` ekler, asla değiştirmez.** `CLAUDE.md`'n içeriğini korur, `.gitignore`'un
  girişlerini korur, `.claude/settings.json`'un kendi kurallarını korur.
- **Proje başına kapatılabilir**, ve o zaman tamamen sessiz.
- **İşaretçi dosyası olmayan bir dizinde hiçbir şey yapmaz** — bağlam yok, dosya yok, ağ
  yok.

## Ekip paket şablonları

Hub'ın `templates/package/` klasörüne dosya koy; `hub-new` gönderilenler yerine dosya dosya
onları kullanır. Yalnızca gerçekten değiştirmek istediğini ekle: kendi `acceptance.md`
şablonu olan ve başka bir şeyi olmayan bir hub, geri kalanın gönderilen sürümlerini alır.

Ekibinin analiz dokümanları için bir ev stili varsa, ya da her paketin taşıması gereken bir
bölüm varsa — geri alma planı, veri migration notu, güvenlik incelemesi kutusu — işe yarar.

## Ortam değişkenleri

| Değişken | Ne yapar |
|---|---|
| `WIZRELAY_DEBUG=1` | stderr'e tanılama, ve beklenmeyen bir hatada yığın izi |
| `WIZRELAY_PYTHON` | `bin/wizrelay` başlatıcısının yorumlayıcısı, `python3` yanlış ya da yoksa |
| `WIZRELAY_CACHE_DIR` | Önbellek konumunu değiştirir |
| `WIZRELAY_TRACKERS_DIR` | Pip ile kurulan CLI için tracker kataloğunun yeri |

## Tracker adaptörü eklemek

Adaptör kod değil veri: plugin'de iki dosya.

1. `plugin/trackers/<type>.json` — tanımlayıcı: `ref_pattern`, `canonical_id`,
   `url_template`, `required_config`, `mcp`.
2. `plugin/trackers/<type>.md` — bir skill'in gerektiğinde yüklediği talimat.
3. `tests/unit/test_trackers.py`'de kimlik ve URL vakaları.
4. MCP uç noktası **yalnızca** doğrulandıktan sonra girer.

`ref_pattern`'ı ECMA-262 adlandırılmış gruplarıyla yaz — `(?<ref>...)` — böylece aynı ifade
bir JSON Schema `pattern`'ı olarak da kullanılabilir; çalışma zamanı Python için çeviriyor.
Bir test bunu zorluyor.

Talep etmek için bir issue şablonu var:
`.github/ISSUE_TEMPLATE/tracker_adapter.yml`.

## Özelleştirilemeyenler ve nedeni

| Yapılandırılamaz | Neden |
|---|---|
| Hangi dosyaların researcher'a ait olduğu | Her şeyin üstünde durduğu sahiplik modeli bu |
| `off` modunda researcher dosyalarının salt okunur kalması | Düzenlenmiş bir kriter "bitti"nin ne demek olduğunu sessizce değiştirir |
| Paket dosyaları arasındaki öncelik sırası | Ekip başına bir sıra, paketi başka bir ekipten gelen biri için okunamaz kılardı |
| `pull`'un yalnızca yayınlanmış paketleri kabul etmesi | Bir taslak, sürüm artışı olmadan altından değişebilir |
| Kopyalama güvenlik sınırları (dosya başına 5 MB, paket başına 20 MB) | Paket analiz, varlık paketi değil |

## Sonraki

[15. Örnek: bir task baştan sona](15-walkthrough.md) — her şey, tek bir task, baştan sona.

<!-- nav:bottom -->
---

| ← | ↑ | → |
|:---|:---:|---:|
| [← 13. Ekip ve kurum yönetimi](13-team-and-enterprise.md) | [İçindekiler](README.md) | [15. Örnek: bir task baştan sona →](15-walkthrough.md) |
<!-- /nav:bottom -->
