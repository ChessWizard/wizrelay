<!-- nav:top -->
[Dokümantasyon](README.md) › **16. Sorun giderme** &nbsp;·&nbsp; [English](../en/16-troubleshooting.md)
<!-- /nav:top -->

# Sorun giderme

Belirti, neden, çözüm. `wizrelay doctor` ile başla — bunların çoğunu senin için kontrol
ediyor.

## Tablo

| Belirti | Olası neden | Çözüm |
|---|---|---|
| "Kapsam koruması bu oturumda aktif değil" | `wizrelay` adlı başka bir plugin hook'ları tutuyor; `disableAllHooks`; güven diyaloğu hiç onaylanmadı | `/plugin` → **Errors** sekmesindeki notu oku; çakışan plugin'i devre dışı bırak ya da kaldır; `/reload-plugins`; `/wizrelay:doctor` |
| Kısa komut (`/pull`) beklenmedik bir şey çalıştırıyor | Başka bir plugin ya da proje skill'i o adı kullanıyor | Tam biçimi kullan: `/wizrelay:pull` |
| `/wizrelay:` komutları görünmüyor | Plugin kurulu ya da etkin değil; güven diyaloğu onaylanmadı | `/plugin` → Installed ve Errors sekmeleri; `/reload-plugins`; repoyu yeniden açıp güven diyaloğunu onayla |
| Oturum başlangıcında task bağlamı gelmiyor | `.wizrelay/config.json` yok; aktif task yok; hook'lar kapalı | `/wizrelay:status`; `/hooks` menüsünde wizrelay hook'larını kontrol et; `disableAllHooks` olmadığından emin ol |
| "Yapılandırılmış bir hub yok" | `hub.repo` yok ya da hâlâ yer tutucu | `/wizrelay:init`'i doğru hub ile tekrar çalıştır |
| "durumu draft, bu yüzden çekilemez" | Paket hâlâ taslak | Researcher'ın yayınlaması gerekiyor |
| `pull` "paket bulunamadı" diyor | Kimlik yanlış; paket push edilmemiş; yanlış hub | Hub'da `wizrelay hub list`; `config.json`'daki hub adresi |
| Git kimlik doğrulama hatası | SSH anahtarı ya da kimlik bilgisi yok | `git ls-remote <hub-url>` ile dene |
| Her dosya kapsam dışı görünüyor | `config.json`'daki `role` task rolleriyle uyuşmuyor; glob hatası | `/wizrelay:status` ile rolü kontrol et; Researcher `allow` listesine bakar |
| "yerelde değiştirilmiş" uyarısı sürüyor | Bir researcher dosyası elle düzenlendi | `/wizrelay:sync` |
| "yeni sürüm" uyarısı sync'ten sonra da sürüyor | Farklı bir daldasın; önbellek yenilenmedi | `/wizrelay:sync`'i tekrar çalıştır; gerekirse `fetch_ttl_minutes: 0` |
| Windows'ta "Python bulunamadı" | `python3` `PATH`'te değil | Python'u kur, Git Bash kullan, `/wizrelay:doctor` |
| Tracker yorumları gönderilmiyor | MCP girişi yok ya da izin istemi reddedildi | `/mcp` ile giriş yap; istemi onayla |
| Plugin hiç önerilmedi | Bilinen bir istem sorunu | Elle kur ([4. bölüm](04-install-plugin.md)) |
| `/wizrelay:verify` ajanı bulamadı | Claude Code ya da plugin sürüm uyumsuzluğu | `claude update`, plugin güncellemesi; sürerse sorun bildir |
| Model değiştirirken onay istendi | Task'ın yönlendirildiğinden zayıf bir model seçtin | Bilinçli onay ver ya da önerilen modelde kal |
| `--advisor` hata veriyor | Anthropic API dışı sağlayıcı ya da uyumsuz model | Komuttan `--advisor`'ı çıkar |
| CI kapısı "atlandı" diyor | Dal adında task kimliği yok | Dalı yeniden adlandır; ya da `--require-task` |
| CI kapısı kırmızı, makinende temiz | CI PR'daki her commit'e bakıyor | Yerelde `wizrelay audit --base origin/main` çalıştır |

## Ciddi olan, ayrıntıyla

### Komutlar çalışıyor ama hiçbir şey engellenmiyor

Kapsam koruması yok ama her komut varmış gibi gösteriyor. Görünce tanınmaya değen hata
biçimi bu.

`/wizrelay:status` çalıştır. Çıktısı `WIZRELAY_NO_GUARD` ile başlıyorsa hook'lar bu oturumda
çalışmadı. Üç sebep:

**1. `python3` çözümlenmiyor.** Hook'lar `python3` çalıştırıyor; o olmadan başlayamazlar.
`wizrelay doctor` `python` kontrolünü **hata** olarak raporluyor. Windows'ta Python 3.9+
kur ki `python3` çözümlensin, ya da Python'u erişilebilir olan Git Bash kullan.

**2. Başka bir plugin de `wizrelay` adında.** Aynı adlı iki plugin varken yalnızca biri
`hooks/hooks.json`'unu kaydeder. `doctor`'ın `duplicate-plugin-name` kontrolü bunu
raporluyor; yinelenen plugin'i kaldır. İkisinden hangisinin kazandığı belgelenmemiş, bu
yüzden kurulum sırasına güvenme.

**3. Hook'lar kapalı ya da klasöre hiç güvenilmemiş.** Ayarlarda `disableAllHooks`'u
kontrol et ve güven istemini almak için klasörü yeniden aç.

## Alana göre

### `pull` ve `sync`

**"Araştırma hub'ına erişilemedi."** `hub.repo` yanlış, erişimin yok, ya da proxy
arkasındasın. Aynı kimlik bilgileriyle elle klonlamayı dene. Proxy için
`.wizrelay/config.local.json`'da `hub.path`'i kendi tuttuğun bir klona ayarla — `hub.path`
ayarlıyken hiçbir şey fetch edilmez, yani çalışma kopyana dokunulmaz.

**"birden fazla paketle eşleşiyor."** İki paket klasörü kimlik önekini paylaşıyor. Tam
klasör adını geç.

**"Yapılandırılmış hub URL'si bir kimlik bilgisi gömüyor."** `https://kullanıcı:token@host`
biçimli bir URL reddediliyor, böylece token bir önbellek yoluna ya da kilit dosyasına hiç
ulaşmıyor. SSH ya da bir git credential helper kullan.

**`sync` bir dosyayı "geri yüklendi" diye raporluyor.** Bir researcher dosyası yerelde
değiştirilmişti ve hub'dan geri kondu. Amaçlanan davranış bu. Değişiklik gerekiyorsa
`/wizrelay:ask` ile sor.

**"Kopyalama reddedildi: `<dosya>` sembolik bağ."** Hub paketi bir kopyanın taşımaması
gereken bir şey içeriyor: sembolik bağ, `..` yolu, 5 MB'tan büyük bir dosya, 20 MB'ı aşan
bir paket. Mesaj dosyayı adlandırıyor; Researcher onu kaldırıp yeniden yayınlar.

### Kapsam

**Bir düzenleme engellendi ve engellenmemeliydi.** Kapsamı görmek için
`/wizrelay:status`, sonra:

- **Kapsam gerçekten yanlış.** `/wizrelay:ask` ile sor. Yerel olarak genişletme — CI kapısı
  aynı kapsamı kontrol ediyor, yani sorun sadece PR'a taşınır.
- **Yanlış roldesin.** `.wizrelay/config.json`'daki `role`.
- **Bayat bir sürümdesin.** `/wizrelay:sync`.

**`enforcement: off` olmasına rağmen bir researcher dosyası engellendi.** Doğru. `off`
*kapsam* zorlamasını kapatır; researcher dosyaları her modda salt okunur kalır.

**`audit` dokunmadığım dosyaları raporluyor.** `.claude/settings.json`, `.gitignore`,
`.mcp.json` ve `CLAUDE.md` *Yan ürün* altında görünür, ihlal olarak değil — onları
`wizrelay init` yazdı. Lockfile'lar her derinlikte yan ürün. Başka bir şey ise bir şey
tarafından değiştirildi: bir formatter, bir derleme adımı, bir üretici. Gerçekten yan ürün
olan yolları profildeki `incidental_allow`'a ekle.

**`audit` taban ref'in çözümlenmediğini söylüyor.** Shallow bir checkout'un merge base'i
yok. CI'da önce taban dalı fetch et; gönderilen GitHub Action bunu yapıyor. Yerelde
`git fetch origin main`.

### Yönlendirme

**`route` ve `pull` farklı söylüyor.** Söylememeleri gerekir ve artık bunu bir test
kapsıyor. İkisi de hub diskteyken hub'ın `policies/routing-policy.json`'unu okuyor ve
yalnızca orada olmadığında plugin varsayılanına düşüyor. Görürsen bildir.

**Riskli bir task için tier çok düşük görünüyor.** Yönlendirme iki girdi okuyor; ikisini de
kontrol et. Paketin `routing.signals` değerleri — Researcher bir kimlik doğrulama yeniden
yazımına `risk: low` koyduysa sorun o. Ve profilin — `critical_paths` yönlendirmeye bir
yolun yanlış yapılmasının pahalı olduğunu söyleyen şey, `test_maturity` ise testlerin ne
kadar yakalayacağını.

**Advisor başlatma komutunda yok.** Üç sebep, hepsi kasıtlı: ana model Haiku (advisor
alamaz), advisor ana modelden zayıf, ya da model advisor kabul etmiyor.

### Hub tarafı

**`hub validate` "doldurulmamış yer tutucu" listeliyor.** Amaçlandığı gibi çalışıyor.
İskelet hâlindeki bir paket, bir insan doldurana kadar kasten geçersiz. Her `{{…}}`'ı
doldur.

**`publish-prep` reddediyor.** Doğrulama hatası olan bir paketi yayınlamaz.
`/wizrelay:hub-validate <ID>` çalıştır ve her hatayı düzelt. Uyarılar engellemez.

**Bir yorum gönderilmedi.** Açık onay olmadan hiçbir şey gönderilmez. Onayladığın hâlde
görünmediyse: tracker'ın MCP sunucusu yetkili değil (`/mcp`), ya da adaptörün doğrulanmış
uç noktası yok ve `gh` CLI'ına ya da tracker'ın kendi arayüzüne ihtiyacın var.

**GitHub yorumundaki deep link tıklanabilir değil.** Beklenen. GitHub `claude-cli://`
bağlantılarını siliyor. Kod bloğunda olmasının sebebi bu — tarayıcına kopyala.

### Ortam

**Windows: hiçbir şey çalışmıyor.** `python3` çözümlenmek zorunda. Python 3.9+ kurulu Git
Bash desteklenen yol. `python3` olmayan yalnızca-PowerShell bir ortam en iyi çaba
düzeyinde, ve `doctor` bunu her şey yolundaymış gibi göstermek yerine hata olarak
raporluyor.

**`wizrelay: command not found`.** Claude Code içinde plugin'in `bin/` dizini, plugin
etkinken Bash aracının `PATH`'inde; bulunamıyorsa plugin etkin değil. Terminalde CLI'ı kur.
Başlatıcı yanlış yorumlayıcıyı seçiyorsa `WIZRELAY_PYTHON` ayarla.

**Var olan bir tracker için "Bilinmeyen tracker türü".** Pip ile kurulan CLI tracker
kataloğunu taşımıyor, çünkü katalog kütüphanenin içinde değil yanında duruyor. Bir
checkout'ta `WIZRELAY_TRACKERS_DIR`'ı `plugin/trackers` olarak ayarla. CI'ın buna ihtiyacı
yok — `audit` tracker'dan bağımsız.

## Yardım almak

1. `wizrelay doctor --json` — eklenmeye değen tek döküm. Kimlik bilgisi içermiyor.
2. `WIZRELAY_DEBUG=1` ile stderr'e tanılama ve yığın izi.
3. Bug şablonuyla bir issue aç; `doctor` çıktısını, Claude Code sürümünü ve platformu
   istiyor.

## Sonraki

[17. Sık sorulan sorular](17-faq.md).

<!-- nav:bottom -->
---

| ← | ↑ | → |
|:---|:---:|---:|
| [← 15. Örnek: bir task baştan sona](15-walkthrough.md) | [İçindekiler](README.md) | [17. Sık sorulan sorular →](17-faq.md) |
<!-- /nav:bottom -->
