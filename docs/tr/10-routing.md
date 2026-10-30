<!-- nav:top -->
[Dokümantasyon](README.md) › **10. Model ve effort yönlendirmesi** &nbsp;·&nbsp; [English](../en/10-routing.md)
<!-- /nav:top -->

# Model ve effort yönlendirmesi

Bir task'ın sinyallerinin ve bir reponun profilinin nasıl modele, effort seviyesine ve
başlatma komutuna dönüştüğü.

## Neden var

Her task aynı modeli ya da aynı düşünme derinliğini gerektirmez. Basit bir değişiklikte
Opus'u yüksek effort'la çalıştırmak zaman ve kota israfı; kritik bir değişiklikte Sonnet'i
düşük effort'la çalıştırmak risk.

Daha derin gerekçe kimin neyi bildiğiyle ilgili. Oturumu açan kişi karar vermek için en
donanımsız olan: **Researcher** task'ın ne kadar riskli olduğunu bilir, **repo** ne kadar
iyi test edildiğini bilir. Yönlendirme kararı bilginin zaten bulunduğu yere taşır.

## Skor nasıl hesaplanır

```
skor = karmaşıklık + risk + belirsizlik       (low = 1, medium = 2, high = 3)
     + projeden gelen ekler                   (varsayılanda her biri +1)
         · kod tabanı büyük
         · test olgunluğu düşük
         · task kapsamı kritik alanlara dokunuyor
         · task kapsamı legacy koda dokunuyor
```

Sinyaller task'tan (Researcher), ekler projenin `profile.json`'ından gelir. Bu yüzden aynı
task backend ve frontend reposunda farklı skor alabilir.

## Tier'lar (varsayılan politika)

| Tier | Skor | Plan | Uygulama | Doğrulama | Başlatma |
|---|---|---|---|---|---|
| T0 mekanik | `kind: mechanical` | sonnet / low | haiku / medium | sonnet / medium | `--model haiku --effort medium` |
| T1 rutin | ≤ 4 | sonnet / medium | sonnet / medium | sonnet / medium | `--model sonnet --effort medium` |
| T2 standart | 5–6 | opus / high | sonnet / high | sonnet / high | `--model opusplan --effort high` |
| T3 kritik | 7–8 | opus / xhigh | opus / high | opus / high | `--model opus --effort high` |
| T4 yüksek risk | ≥ 9 | opus / xhigh | opus / high + advisor | opus / xhigh | `--model opus --effort high --advisor opus` |

Effort seviyeleri kısaca:

| Seviye | Ne için |
|---|---|
| `low` | Hızlı ve hafif işler |
| `medium` | Kapsamı net özellik işleri; Opus 5.5 ve Sonnet 5.5'in varsayılanı |
| `high` | Doğrulamanın ve kenar durumların önemli olduğu işler |
| `xhigh` | Daha derin düşünme |
| `max` | En derin seviye, ama aşırı düşünmeye yatkın; varsayılan politikada hiç kullanılmaz |

Varsayılanlardan iki kasıtlı eksik: **`max`**, aşırı düşünmeye yatkın olduğu ve açıkça
seçilmesi daha iyi olduğu için; ve **Fable**, bazı planlarda usage credit'ten
faturalandığı ve bunun başına gelen bir şey değil bir karar olması gerektiği için. İkisi de
override ile kullanılabilir.

## Researcher'ın kontrolü

Sinyalleri şöyle seç:

| Sinyal | low | medium | high |
|---|---|---|---|
| `complexity` | Tek dosya ya da fonksiyon, bilinen kalıp | Birkaç modül, yeni ama net mantık | Çok modüllü, yeni mimari kalıp, eşzamanlılık |
| `risk` | Hata maliyeti düşük, kolay geri alınır | Müşteri etkisi sınırlı | Para, güvenlik, veri bütünlüğü, tenant izolasyonu |
| `ambiguity` | Her şey kararlaştırılmış | Birkaç yorum alanı var | Önemli kararlar hâlâ açık (yayından önce kapatılmalı) |

**`ambiguity: high` ile yayın yapmak kapsam sapmasının tek en büyük kaynağı**, doğrulamanın
bunu uyarmasının sebebi de bu.

```json
{
  "routing": {
    "signals": { "complexity": "medium", "risk": "high", "ambiguity": "low" },
    "role_signals": { "frontend": { "complexity": "low", "risk": "low" } },
    "overrides": {
      "*": { "verify": { "model": "opus", "effort": "high" } },
      "backend": { "implement": { "advisor": "opus" } }
    }
  }
}
```

- **`role_signals`** sinyalleri rol bazında değiştirir — burada frontend işi basit.
- **`kind: "mechanical"`** yeniden adlandırma, çeviri dosyaları, boilerplate için.
- **`overrides`** tier ne olursa olsun belirli aşamaları zorlar. `*` tüm roller demek.

Sinyalleri dürüst ayarla. Riski düşük göstermek tehlikeli bir task'ı zayıf bir modele
yönlendirir ve aşağıda kimse farketmez.

## Projenin etkisi

`profile.json`'daki `codebase_size`, `test_maturity`, `critical_paths` ve `legacy_paths`
skoru artırır. `critical_paths` listesinde `app/api/**` bulunan ve `test_maturity: low` olan
bir repoda aynı task T2 yerine T3 olur.

### Gönderilen örneklerden çalışan bir gösterim

Kendin çalıştır:

```bash
cd examples/dev-backend  && wizrelay pull CU-86c1abcd && wizrelay route
cd ../dev-frontend       && wizrelay pull CU-86c1abcd && wizrelay route
```

**`examples/dev-backend`** — paketin sinyalleri medium/high/low = 6. Profil
`test_maturity: low` ve bir `critical_paths` kesişimi ekliyor. Örnek hub'ın politikası
bunları 2'ye ağırlıklandırıyor, yani skor 10: **T4-high-risk**. Plugin'in varsayılanlarıyla,
her biri 1 olarak, 8 olurdu: **T3-critical**.

**`examples/dev-frontend`** — paket frontend rolünün sinyallerini low/low/low = 3'e
düşürüyor ve o profilde hiçbir ek tetiklenmiyor: **T1-routine**.

Aynı task, aynı hub, iki rol, iki tier. Yönlendirmenin task başına değil rol başına
hesaplanmasının tüm sebebi bu.

## Developer bununla ne yapar

[8. Developer: task'ı uygulamak](08-developer-workflow.md)'ta. Başlatma komutunun ötesinde,
plugin aşama başına kendi effort'unu da ayarlıyor:

| Komut / ajan | Çalıştığı seviye |
|---|---|
| `/wizrelay:plan` | Yüksek effort |
| `/wizrelay:verify` | Yüksek effort |
| `/wizrelay:ask` | Orta effort |
| `/wizrelay:hub-new` | Çok yüksek effort |
| Yardımcı ajanlar | Kendi tanımlı modelleri |

## Ekip politikasını değiştirmek

Hub'daki `policies/routing-policy.json` dosyasında eşikleri (`max_score`), aşama modellerini
ve ek ağırlıklarını (`modifiers`) düzenle ve commit et. Projeler bir sonraki `pull` ya da
`sync`'te yeni politikayı kullanır.

İlk uzanılacak kol ağırlıklar. Genel olarak test kapsaması zayıf bir ekip
`test_maturity_low`'u 2'ye çıkarıp her az test edilmiş task'ı bir tier yukarı taşıyabilir —
tek bir pakete dokunmadan.

Bir hub politikası plugin varsayılanını birleştirmek yerine **tamamen değiştirir**, bu yüzden
her tier'ı listele. Kısmen geçersiz kılınmış bir tier tablosu, eksiksiz olandan daha zor
anlaşılır.

## Maliyet ve erişim

- **Fable** bazı planlarda usage credit'ten faturalanıyor. İstiyorsan bir override ile
  bilinçli seç.
- **Advisor** deneysel, ek token harcıyor ve yalnızca Anthropic API'de çalışıyor.
- **Kurumsal sınırlar:** kurumun model ya da effort sınırı koyduysa
  ([13. Ekip ve kurum](13-team-and-enterprise.md)) bu sınırları Claude Code uygular.
  Önerilen model izinli değilse Claude Code izinli bir modelle devam eder.

## Dürüst çekinceler

- **Bir skill'in `model` alanı yalnızca kendi turu için geçerli.** Aşama bazlı model seçimi
  bu nedenle tavsiye niteliğinde: sana başlatma komutuyla ve subagent parametreleriyle
  ulaşır, oturumunu sessizce değiştirerek değil.
- **Model aileleri arasındaki sıralama bir proje kabulü.** Doküman advisor'ın ana modelle
  aynı ya da daha güçlü olması gerektiğini ve Haiku'nun advisor olamayacağını söylüyor, ama
  aileler arası tam bir sıralama yayınlamıyor. Burada kullanılan sıra
  haiku < sonnet < fable < opus ve muhafazakâr: belirsiz bir eşleşme önerilmek yerine
  düşürülüyor.

## Sonraki

[11. Kapsam koruması](11-scope-protection.md).

<!-- nav:bottom -->
---

| ← | ↑ | → |
|:---|:---:|---:|
| [← 9. Soru ve sürüm döngüsü](09-question-loop.md) | [İçindekiler](README.md) | [11. Kapsam koruması →](11-scope-protection.md) |
<!-- /nav:bottom -->
