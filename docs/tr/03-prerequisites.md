<!-- nav:top -->
[Dokümantasyon](README.md) › **3. Ön koşullar** &nbsp;·&nbsp; [English](../en/03-prerequisites.md)
<!-- /nav:top -->

# Ön koşullar

Hiçbir şey kurulmadan önce her kişinin neye ihtiyacı olduğu ve nasıl kontrol edileceği.

## Liste

| Gereksinim | Kimde | Kontrol |
|---|---|---|
| Claude Code ≥ v2.1.295 | Herkes | `claude --version` · güncelleme: `claude update` |
| Python ≥ 3.9 ve `PATH` üzerinde `python3` | Herkes | `python3 --version` |
| git | Herkes | `git --version` |
| Hub reposuna erişim | Researcher: yazma · Developer: okuma | `git ls-remote <hub-url>` |
| Tracker hesabı ve MCP yetkisi | Researcher, ve soru ya da rapor gönderecek developer'lar | Claude Code'da `/mcp` bağlı gösteriyor |
| Model erişimi | Herkes | `/model` seçicisinde Opus ve Sonnet görünüyor |

## Başlamadan önce bilinmesi gerekenler

### Hangi Claude

Plugin **Claude Code** içindir: terminal, VS Code ve JetBrains eklentileri ya da masaüstü
uygulamasının Code sekmesi. claude.ai sohbet arayüzünde çalışmaz, ve claude.ai ile Cowork'te
kurulamaz — plugin bir `bin/` dizini taşıyor, o yüzeyler bunu reddediyor, ve zorlamayı yapan
hook'lar orada yok.

### `python3` isteğe bağlı değil

Hook'lar `python3 <script>` olarak çalışıyor. Çözümlenebilir bir `python3` olmadan
**hook'lar hiç çalışmaz** — ve bu, her komut çalışıyor görünürken kapsam korumasının sessizce
yok olması demek.

`wizrelay doctor` bunu tam bu yüzden **hata** olarak raporluyor, uyarı olarak değil.
Tetiklenirse [16. Sorun giderme](16-troubleshooting.md)'ye bak.

### Windows

Git for Windows kur, böylece Git Bash olsun, ve orada `python3`'ün çözümlendiğinden emin ol.
Yalnızca-PowerShell bir ortam v1'de en iyi çaba düzeyinde: plugin'in komutları çalışır ama
hook'lar çalışmaz, çünkü exec biçimli bir hook gerçek bir çalıştırılabilir ister ve Windows'ta
bir shell script'i o değil.

### Modeller ve faturalama

- **Fable** isteğe bağlı ve bazı planlarda usage credit'ten faturalanıyor. Varsayılan
  yönlendirme politikası onu hiç seçmiyor; Researcher bir override ile açıkça seçebilir.
- **Advisor** deneysel ve yalnızca Anthropic API'de çalışıyor. Claude Code'u Amazon Bedrock,
  Google Cloud'un Agent Platform'u ya da Microsoft Foundry üzerinde çalıştırıyorsan,
  plugin'in önerdiği başlatma komutundan `--advisor` kısmını çıkar.

### Klasöre güven ver

Claude Code bir klasörü ilk açtığında güvenmeni ister. **Proje ayarları ve plugin önerisi
ancak bundan sonra devreye girer**, bu yüzden bağlı görünmeyen bir repo genellikle sadece
yanıtlanmamış bir güven istemine sahiptir.

## Beş dakikalık kontrol

Bir şey kurmadan önce bunları çalıştır. Dördü de başarılı olmalı:

```bash
claude --version          # ≥ 2.1.295
python3 --version         # ≥ 3.9
git --version
git ls-remote <hub-url>   # hub'ın, oluşturulduktan sonra
```

Ve bir Claude Code oturumunda:

```
/mcp        # tracker'ın, bağlı
/model      # Opus ve Sonnet listede
```

## Sonraki

[4. Plugin'i kurmak](04-install-plugin.md).

<!-- nav:bottom -->
---

| ← | ↑ | → |
|:---|:---:|---:|
| [← 2. Ne yapar, ne yapmaz](02-scope.md) | [İçindekiler](README.md) | [4. Plugin'i kurmak →](04-install-plugin.md) |
<!-- /nav:bottom -->
