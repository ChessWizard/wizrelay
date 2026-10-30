<!-- lang -->
[English](README.md) &nbsp;·&nbsp; **Türkçe**
<!-- /lang -->

# wizrelay

Researcher'ın task analizini tek bir doğruluk kaynağından her developer'ın Claude Code
oturumuna taşır — deterministik olarak.

[![Lisans](https://img.shields.io/badge/lisans-Apache--2.0-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.9%2B-blue.svg)](pyproject.toml)
[![Claude Code](https://img.shields.io/badge/Claude%20Code-%E2%89%A5%20v2.1.295-5A3FD6.svg)](https://code.claude.com/docs)

---

## Problem

AI-native bir ekipte bir analist task'ın ne gerektirdiğini çıkarır. Her developer ise kendi
AI kodlama oturumunda çalışır. O oturumlar aynı analizi okur ve farklı yorumlar — sonuç:
kapsam dışına çıkma, roller arası sözleşme uyumsuzlukları ve buglar.

Analizi paylaşmak bunu tek başına çözmez. **Talimat izlemek olasılıksaldır; kural uygulamak
deterministik olmak zorundadır.** wizrelay ikincisidir.

## Ne yapar

| | |
|---|---|
| **Tek doğruluk kaynağı** | Researcher sürümlü bir task paketini özel bir ekip hub'ına yayınlar. Developer'lar salt okunur, hash'le doğrulanmış bir kopya çeker. |
| **Deterministik bağlam** | Paket özeti her oturum başında ve her sıkıştırmadan sonra yeniden enjekte edilir; analiz konuşmadan kayıp gitmez. |
| **Katmanlı kapsam koruması** | İzin deny kuralları, bir `PreToolUse` hook'u, tur sonu denetimi, doğrulama adımı ve CI kapısı. Beş katman, çünkü her biri üstündekinin kaçırdığını yakalar. |
| **Model ve effort yönlendirmesi** | Bir politika, task'ın sinyallerini ve reponun profilini bir tier'a, tier'ı da aşama başına model ve effort seviyesine çevirir. |
| **Soru döngüsü** | Paketin yanıtlamadığı bir soru tracker üzerinden Researcher'a gider ve yeni bir paket sürümünde karar olarak geri döner. |
| **Doğrulama developer'da** | Dosya düzenleyemeyen bağımsız bir doğrulayıcı her kabul kriterini bir kanıtla eşler. |

Tracker'dan, rolden ve projeden bağımsızdır: plugin'in kendisi hiçbir ekip içeriği taşımaz.

## Parçalar nasıl birleşir

```
                PLUGIN (wizrelay) — herkesin Claude Code'unda kurulu
                                │  okur / yazar
                                ▼
                 EKİP HUB'I  (acme/research-hub, özel git)
                 tasks/CU-86c1abcd-…/    tasks/CU-91f2aa10-…/
                                │  /wizrelay:pull
          ┌─────────────────────┼─────────────────────┐
          ▼                     ▼                     ▼
          api-service           web-app               deploy-infra
          rol: backend          rol: frontend         rol: infra
          .wizrelay/            .wizrelay/            .wizrelay/
```

**Ekip** başına bir hub, proje başına değil. Ekibe yeni bir repo eklemek yeni hub
gerektirmez.

## Hızlı başlangıç

**Kurulum**, makine başına bir kez:

```
/plugin marketplace add ChessWizard/wizrelay
/plugin install wizrelay@wizrelay
```

**Researcher**, ekip başına bir kez, sonra task başına:

```
/wizrelay:hub-init
/wizrelay:hub-new 86c1abcd backend,frontend
/wizrelay:hub-validate CU-86c1abcd
/wizrelay:hub-publish CU-86c1abcd
```

**Developer**, repo başına bir kez, sonra task başına:

```
/wizrelay:init backend git@github.com:acme/research-hub.git
/wizrelay:pull CU-86c1abcd
/wizrelay:plan
/wizrelay:verify
```

Baştan sona örnek: [docs/tr/15-walkthrough.md](docs/tr/15-walkthrough.md).

## Dokümantasyon

**[→ Dokümantasyon dizini](docs/tr/README.md)** · tek bir kılavuz, bölüm başına bir dosya.

| Buradan başla | |
|---|---|
| [1. Genel bakış](docs/tr/01-overview.md) | Ne olduğu ve neden böyle kurulduğu |
| [2. Ne yapar, ne yapmaz](docs/tr/02-scope.md) | Kapsam, kapsam dışı, kim ne yapar |
| [15. Örnek](docs/tr/15-walkthrough.md) | Bir task, tracker'dan merge edilmiş PR'a |

| Kurulum | |
|---|---|
| [3. Ön koşullar](docs/tr/03-prerequisites.md) · [4. Plugin'i kurmak](docs/tr/04-install-plugin.md) · [5. Hub](docs/tr/05-set-up-hub.md) · [6. Repoyu bağlamak](docs/tr/06-connect-repository.md) | |

| Kullanım | |
|---|---|
| [7. Researcher](docs/tr/07-researcher-workflow.md) · [8. Developer](docs/tr/08-developer-workflow.md) · [9. Soru döngüsü](docs/tr/09-question-loop.md) | |

| Mekanizma | |
|---|---|
| [10. Yönlendirme](docs/tr/10-routing.md) · [11. Kapsam koruması](docs/tr/11-scope-protection.md) · [12. CI](docs/tr/12-ci-integration.md) | |

| İşletme | |
|---|---|
| [13. Ekip ve kurum](docs/tr/13-team-and-enterprise.md) · [14. Özelleştirme](docs/tr/14-customisation.md) | |

| Referans | |
|---|---|
| [16. Sorun giderme](docs/tr/16-troubleshooting.md) · [17. SSS](docs/tr/17-faq.md) · [Komutlar](docs/tr/appendix-a-commands.md) · [Dosyalar](docs/tr/appendix-b-files.md) · [Sözlük](docs/tr/appendix-e-glossary.md) | |

## Gereksinimler

- Claude Code ≥ v2.1.295
- Python ≥ 3.9 ve `PATH` üzerinde `python3` — hook'lar buna ihtiyaç duyar
- git

Çalışma zamanı yalnızca Python standart kütüphanesini kullanır. Bir plugin için kimse
bağımlılık kurmaz, bu yüzden tek bir üçüncü parti import, o paketi olmayan herkesin
plugin'ini bozardı.

## CLI kurulumu

CI için ya da Claude Code olmadan kullanmak için:

```bash
pip install "git+https://github.com/ChessWizard/wizrelay@v1.0.0"
```

Her deterministik işlemin bir CLI karşılığı var — `wizrelay pull`, `audit`,
`hub validate`, `hub publish-prep` — böylece aynı davranış terminalde ve CI'da da elde
edilir.

## Hub olmadan denemek

Repo çalışan bir hub ve ona bağlı iki proje içeriyor:

```bash
cd examples/dev-backend && wizrelay pull CU-86c1abcd && wizrelay route
```

Aynı paket `examples/dev-frontend` içinde farklı bir tier'a gidiyor, çünkü yönlendirme rol
başına hesaplanıyor. Bkz. [examples/README.md](examples/README.md).

## Proje durumu

Yayın öncesi. Neyin tamamlandığı [CHANGELOG.md](CHANGELOG.md)'de. Uygulama planı bu
reponun dışında tutuluyor.

## Gizlilik

Hiçbir servis, hiçbir telemetri yok; makineden çıkan tek şey senin yapılandırdığın repo ve
tracker'a gidiyor. Tam metin: [PRIVACY.md](PRIVACY.md) (İngilizce).

## Güvenlik

wizrelay bir **korkuluk, hapishane değil**. Her katmanın neyi durdurduğu ve
neyi durdurmadığı için [11. Kapsam koruması](docs/tr/11-scope-protection.md), tehdit modeli
ve güvenlik bildirimi için [SECURITY.md](SECURITY.md).

## Katkı

[CONTRIBUTING.md](CONTRIBUTING.md). Katkıda bulunarak
[Davranış Kuralları](CODE_OF_CONDUCT.md)'nı kabul etmiş olursun.

## Lisans

[Apache-2.0](LICENSE)
