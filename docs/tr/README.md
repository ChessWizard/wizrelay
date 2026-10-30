<!-- nav:top -->
**Dokümantasyon** &nbsp;·&nbsp; [English](../en/README.md)
<!-- /nav:top -->

# wizrelay — dokümantasyon

Tek bir kılavuz, bölüm başına bir dosya. Her sayfa önceki bölüme, sonraki bölüme,
bu dizine ve İngilizce karşılığına bağlanır.

## Nereden başlamalı

| Rolün | Şu sırayla oku | Yaklaşık |
|---|---|---|
| Ekip için kuran kişi | [1](01-overview.md) → [2](02-scope.md) → [3](03-prerequisites.md) → [4](04-install-plugin.md) → [5](05-set-up-hub.md) → [6](06-connect-repository.md) → [13](13-team-and-enterprise.md) | 50 dk |
| Researcher | [1](01-overview.md) → [7](07-researcher-workflow.md) → [9](09-question-loop.md) → [10](10-routing.md) → [11](11-scope-protection.md) | 40 dk |
| Developer | [1](01-overview.md) → [6](06-connect-repository.md) → [8](08-developer-workflow.md) → [11](11-scope-protection.md) → [16](16-troubleshooting.md) | 30 dk |
| Platform / DevOps | [12](12-ci-integration.md) → [13](13-team-and-enterprise.md) → [16](16-troubleshooting.md) | 20 dk |
| Sadece çalıştığını görmek isteyen | [15](15-walkthrough.md) | 15 dk |

## Anlama

| # | Bölüm | Ne anlatır |
|---|---|---|
| 1 | [Genel bakış](01-overview.md) | wizrelay'in ne olduğu, çözdüğü problem ve oluştuğu üç parça |
| 2 | [Ne yapar, ne yapmaz](02-scope.md) | Bu aracın sınırı: taahhüt ettiği hedefler, kasten dokunmadığı yerler ve verebildiği ile veremediği garantiler |
| 3 | [Ön koşullar](03-prerequisites.md) | Hiçbir şey kurulmadan önce her kişinin neye ihtiyacı olduğu ve nasıl kontrol edileceği |

## Kurulum

| # | Bölüm | Ne anlatır |
|---|---|---|
| 4 | [Plugin'i kurmak](04-install-plugin.md) | `wizrelay`'i kurmak, çalıştığını kontrol etmek ve kapsam korumasının bir oturumda gerçekten aktif olduğunu doğrulamak |
| 5 | [Ekip hub'ını kurmak](05-set-up-hub.md) | Ekibinin analizini tutan repoyu oluşturmak ve onu güvenilir kılan iki ayar |
| 6 | [Bir repoyu bağlamak](06-connect-repository.md) | Bir proje reposunu hub'a bağlamak ve profilini doğru yapmak — çünkü yönlendirme o profili okuyor |

## Kullanım

| # | Bölüm | Ne anlatır |
|---|---|---|
| 7 | [Researcher: hazırlamak ve yayınlamak](07-researcher-workflow.md) | Bir task paketini dosya dosya yazmak ve developer'lar çekebilmeden önce geçtiği iki kapı |
| 8 | [Developer: task'ı uygulamak](08-developer-workflow.md) | Paketi çekmek, ona göre planlamak, kontroller devredeyken uygulamak ve kanıtla doğrulamak |
| 9 | [Soru ve sürüm döngüsü](09-question-loop.md) | Bir developer sorduktan sonra Researcher'ın ne yaptığı ve yanıtın neden bir yorum değil bir sürüm olması gerektiği |

## Mekanizma

| # | Bölüm | Ne anlatır |
|---|---|---|
| 10 | [Model ve effort yönlendirmesi](10-routing.md) | Bir task'ın sinyallerinin ve bir reponun profilinin nasıl modele, effort seviyesine ve başlatma komutuna dönüştüğü |
| 11 | [Kapsam koruması](11-scope-protection.md) | Beş katman, her birinin gerçekten neyi durdurduğu, glob sözdizimi ve gizlenmek yerine belgelenen atlatma yolları |
| 12 | [CI entegrasyonu](12-ci-integration.md) | PR kapısı: developer'ın kendi oturumunda çalışmayan tek katman |

## İşletme

| # | Bölüm | Ne anlatır |
|---|---|---|
| 13 | [Ekip ve kurum yönetimi](13-team-and-enterprise.md) | Bunu bir ekibe yaymak ve developer'ın kapatamadığı iki katman |
| 14 | [Özelleştirme](14-customisation.md) | Her ayar, nerede durduğu ve ikisi çeliştiğinde hangi katmanın kazandığı |

## Örnek

| # | Bölüm | Ne anlatır |
|---|---|---|
| 15 | [Örnek: bir task baştan sona](15-walkthrough.md) | Tek bir task, tracker kaydından merge edilmiş PR'a kadar; her adımda gerçek dosya içerikleri ve gerçek komut çıktılarıyla |

## Referans

| # | Bölüm | Ne anlatır |
|---|---|---|
| 16 | [Sorun giderme](16-troubleshooting.md) | Belirti, neden, çözüm |
| 17 | [Sık sorulan sorular](17-faq.md) | İlk haftada çıkan sorular |
| A | [Ek A — Komut referansı](appendix-a-commands.md) | Her komut, kimin kullandığı ve CLI karşılığı |
| B | [Ek B — Dosya referansı](appendix-b-files.md) | Sistemin oluşturduğu ya da okuduğu her dosya, sahibi ve commit edilip edilmediği |
| C | [Ek C — Tracker yorum etiketleri](appendix-c-tracker-tags.md) | Dört etiket, tam ilk satırları ve yorum yazma kuralları |
| D | [Ek D — Kontrol listeleri](appendix-d-checklists.md) | Bunları bir issue'ya ya da wiki sayfasına kopyala |
| E | [Ek E — Sözlük](appendix-e-glossary.md) | Bu dokümantasyonun bildiğini varsayarak kullandığı her terim ve birbirine karıştırılması kolay terim çiftleri |

## Katkıda bulunanlar için

[CONTRIBUTING.md](../../CONTRIBUTING.md) kurulumu, standartları ve bitmişlik
tanımını anlatıyor.
