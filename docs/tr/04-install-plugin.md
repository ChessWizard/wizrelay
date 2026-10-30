<!-- nav:top -->
[Dokümantasyon](README.md) › **4. Plugin'i kurmak** &nbsp;·&nbsp; [English](../en/04-install-plugin.md)
<!-- /nav:top -->

# Plugin'i kurmak

`wizrelay`'i kurmak, çalıştığını kontrol etmek ve kapsam korumasının bir oturumda gerçekten
aktif olduğunu doğrulamak.

## Kişisel kurulum, kullanıcı başına bir kez

Her yüzeyin kendi rotası var. Hepsi aynı ayar dosyalarına yazdığı için kullanıcı kapsamında
tek bir kurulum, o makinedeki terminale, masaüstü uygulamasına ve VS Code eklentisine ulaşır.

### Terminal

Claude Code oturumunda:

```
/plugin install wizrelay --marketplace ChessWizard/wizrelay
```

Bu komut marketplace'i ekler ve `wizrelay`'in detaylarını `/plugin` panelinde açar. **Orada
bir kapsam seçmeden hiçbir şey kurulmaz** — komut tek seferlik bir kurulum değil.

Aynısı, oturum başlatmadan kabuktan:

```bash
claude plugin marketplace add ChessWizard/wizrelay
claude plugin install wizrelay@wizrelay
```

### Masaüstü uygulaması

Masaüstü uygulamasının **Code** sekmesinde `/plugin` paneli açılmaz. Marketplace'i yukarıdaki
komutla kabuktan ekle, sonra prompt kutusunun yanındaki **+** düğmesine basıp **Add plugins**
seç — eski bir sürüm **Plugins**, ardından **Browse plugins** gösterir. `wizrelay`'i seç ve
bir kapsam belirle.

### VS Code

Prompt kutusuna `/plugins` yazıp **Manage plugins**'i aç. **Marketplaces** sekmesinde
`ChessWizard/wizrelay`'i ekle, sonra **Plugins** sekmesinde `wizrelay`'i bulup **Install**'a bas.

JetBrains'in kendi plugin tarayıcısı yok: Claude Code'u IDE terminalinde çalıştırır, yani
orada terminal rotası geçerli. Bulut oturumları ise hiçbir plugin yüklemez.

`ChessWizard/wizrelay`, marketplace'in okunduğu repodur. Bir fork'tan kuruyorsan onun yerine o fork'un sahibini yaz.

Sonra doğrula:

1. `/` yaz ve `/wizrelay:` komutlarını ara. Terminal oturumunda `/plugin` plugin'i
   **Installed** sekmesinde de listeler — panel **Discover** sekmesinde açıldığı için oraya
   **Tab** ile geç — ve **Errors** sekmesi boş olmalı.
2. `/wizrelay:doctor` çalıştır. Python'u, git'i, plugin bütünlüğünü, aynı manifest adını
   kullanan ikinci bir plugin olup olmadığını ve bağlı bir repo içindeysen o reponun
   yapılandırmasını kontrol eder.

## Kurulum kapsamı

**Kullanıcı kapsamında** kur: bir kez, ve her projende kullanılabilir.

Ne `.wizrelay/` ne `wizrelay-hub.json` olan bir dizinde plugin **tamamen sessizdir**.
Bağlam eklemez, dosya yazmaz, ağa çıkmaz. Yani kişisel projelerinde ve wizrelay kullanmayan
repolarda hiçbir şeye karışmaz.

Ekip repolarında otomatik önerilmesi için marketplace ve plugin kaydını repo ayarına ekle —
bkz. [13. Ekip ve kurum yönetimi](13-team-and-enterprise.md).

## Güncelleme

```
/plugin marketplace update wizrelay
```

Sonra `/plugin` ekranından `wizrelay` için güncellemeyi uygula; oturum almazsa
`/reload-plugins` çalıştır. Sürüm notları ürün reposundaki `CHANGELOG.md`'de.

Öngörülebilirlik istiyorsan bir sürüme sabitle: plugin manifest'indeki `version` kullanıcılara
ne gittiğini belirler, ve bir marketplace girişi bir etiketi sabitleyebilir.

**Bu marketplace'te auto-update kapalı.** Claude Code bunu yalnızca Anthropic'in kendi
marketplace'lerinde açıyor, yani güncellemeler istendiğinde geliyor. Kendiliğinden gelmesini
istiyorsan `/plugin`'i aç, **Marketplaces** sekmesine geç, `wizrelay`'i seç ve **Enable
auto-update**'i işaretle. O zaman bile çalışan oturum yüklediği sürümde kalır; yeni sürümü
bir sonraki oturum alır.

## Kaldırma ve bir projede kapatma

Tamamen kaldırmak için:

```
/plugin uninstall wizrelay@wizrelay
```

Yalnızca bir projede kapatmak için, o projenin `.claude/settings.json` dosyasına:

```json
{ "enabledPlugins": { "wizrelay@wizrelay": false } }
```

## Kısa komutlar

Claude Code, başka bir komut aynı adı kullanmıyorsa plugin komutunu kısa adıyla da
çalıştırır. Bu kılavuz her zaman tam biçimi yazar; günlük kullanımda kısa biçim de olur.

| Kısa yazılabilir | Her zaman tam yazılır (yerleşikle çakışır) |
|---|---|
| `/pull`, `/ask`, `/verify`, `/sync` | `/wizrelay:plan` |
| `/hub-init`, `/hub-new`, `/hub-validate` | `/wizrelay:init` |
| `/hub-publish`, `/hub-inbox`, `/hub-status` | `/wizrelay:status`, `/wizrelay:doctor` |

Kısa ad beklenmedik bir şey çalıştırırsa — başka bir plugin ya da projedeki bir skill aynı
adı kullanıyorsa — tam biçime geç.

## Kapsam korumasının aktif olduğunu bilmek

Bunu bir kez bilerek yapmaya değer, çünkü başarıya benzeyen başarısızlık bu.

Kapsam koruması hook'larla çalışır. Hook'lar bir oturumda çalışmıyorsa wizrelay komutları
çıktılarının en üstünde şunu gösterir:

```text
⚠ Kapsam koruması bu oturumda aktif değil.
```

Üç şey buna yol açar:

- Kurulu başka bir plugin de `wizrelay` manifest adını kullanıyor ve hook kaydını o tutuyor.
  Aynı adlı iki plugin varken **yalnızca biri hook'larını kaydeder.**
- Ayarlarda tüm hook'lar kapatılmış (`disableAllHooks`).
- Repo klasörü için güven diyaloğu hiç onaylanmamış.

`/wizrelay:doctor` üçünü ayrı ayrı kontrol ediyor.
[16. Sorun giderme](16-troubleshooting.md) çözümleri içeriyor.

Akılda tutulacak ayrım: **`doctor` yapılandırmayı kontrol eder, `/wizrelay:status` bu
oturumu.** Bir yapılandırma kusursuz olabilirken hook'lar burada çalışmamış olabilir.

## Sonraki

[5. Ekip hub'ını kurmak](05-set-up-hub.md) — ekip başına bir kez.

<!-- nav:bottom -->
---

| ← | ↑ | → |
|:---|:---:|---:|
| [← 3. Ön koşullar](03-prerequisites.md) | [İçindekiler](README.md) | [5. Ekip hub'ını kurmak →](05-set-up-hub.md) |
<!-- /nav:bottom -->
