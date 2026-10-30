<!-- nav:top -->
[Dokümantasyon](README.md) › **13. Ekip ve kurum yönetimi** &nbsp;·&nbsp; [English](../en/13-team-and-enterprise.md)
<!-- /nav:top -->

# Ekip ve kurum yönetimi

Bunu bir ekibe yaymak ve developer'ın kapatamadığı iki katman.

## Dürüst özet

Kapsam korumasının 1–4. katmanları developer'ın kendi oturumunda duruyor ve developer
hepsini kapatabilir. İki şey, kısıtladığı kişi tarafından kapatılamaz:

- **CI kapısı** ([12. CI entegrasyonu](12-ci-integration.md))
- **Managed settings**, bir yönetici tarafından dağıtılan

Hiçbirini kurmazsan yardımcı bir asistanın olur, korkuluğun olmaz. Birini kurarsan CI kapısı
olsun: daha az müdahaleci ve önemli olanı yakalıyor — bir değişikliğin ana dala ulaşması.

## 1. Repo düzeyinde ekip ayarı

`.claude/settings.json`, commit edilir:

```json
{
  "extraKnownMarketplaces": {
    "wizrelay": { "source": { "source": "github", "repo": "ChessWizard/wizrelay" } }
  },
  "enabledPlugins": { "wizrelay@wizrelay": true },
  "permissions": {
    "deny": [
      "Edit(/.wizrelay/tasks/*/task.json)",
      "Edit(/.wizrelay/tasks/*/research.md)",
      "Edit(/.wizrelay/tasks/*/scope.md)",
      "Edit(/.wizrelay/tasks/*/acceptance.md)",
      "Edit(/.wizrelay/tasks/*/contracts.md)",
      "Edit(/.wizrelay/tasks/*/decisions.md)",
      "Edit(/.wizrelay/tasks/*/roles/**)",
      "Edit(/.wizrelay/tasks/*/.lock.json)"
    ]
  }
}
```

`wizrelay init` deny listesini eksiksiz yazar. Marketplace bloğunu otomatik eklemek için:

```bash
wizrelay init --marketplace ChessWizard/wizrelay
```

Repoyu açıp güven diyaloğunu onaylayan bir ekip arkadaşına plugin önerilir.

**Onboarding notlarına yazılmaya değen çekince:** bazı Claude Code sürümlerinde bu öneri
gelmiyor. [4. Plugin'i kurmak](04-install-plugin.md)'taki manuel kurulumu belgelenmiş geri
düşüş olarak tut — insanların reponun bozuk olduğu sonucuna varmasından iyi.

## 2. Managed settings ile kurumsal zorlama

Managed settings bir yönetici tarafından dağıtılır ve kullanıcının kendi
`settings.json`'uyla geçersiz kılınamaz. Bununla:

- Plugin'i herkes için etkinleştirebilirsin
- Researcher dosyası koruma kurallarını kullanıcıların kaldıramayacağı yere koyabilirsin
- İzinli modelleri sınırlayabilirsin
- Effort seviyesine üst sınır koyabilirsin

Uyarlanmaya hazır dosyalar
[`integrations/managed-settings/`](../../integrations/managed-settings/) altında, her
anahtarın kullanıcıya neye mal olduğunu gösteren bir tabloyla. **Dağıtmadan önce o tabloyu
oku.** Maliyetten iki örnek: `bypassPermissions`'ı engellemek konteynerlerde gerçekten
yararlı bir modu kaldırıyor, ve sabit bir `disableAllHooks: false` kullanıcıların **başka**
plugin'lerin hook'larını kapatmasını da engelliyor.

```json
{
  "extraKnownMarketplaces": {
    "wizrelay": { "source": { "source": "github", "repo": "ChessWizard/wizrelay" } }
  },
  "enabledPlugins": { "wizrelay@wizrelay": true },
  "permissions": {
    "deny": [
      "Edit(/.wizrelay/tasks/*/research.md)",
      "Edit(/.wizrelay/tasks/*/task.json)"
    ],
    "disableBypassPermissionsMode": "disable"
  }
}
```

**Dağıtmadan önce anahtar adlarını güncel Claude Code managed-settings dokümanından
doğrula.** Özellikle modelleri sınırlayan ve effort'a sınır koyan anahtarların adları
sürümler arasında değişti, ve yanlış anahtarlı bir managed settings dosyası sessizce
etkisizdir — güvendiğin bir kontrol için en kötü sonuç.

Temel dosyayla başla. Model ya da effort tabanını bir sebebin olduğunda ekle: her repodaki
her task'a uygulanıyor, yalnızca wizrelay'in yönlendirdiklerine değil.

## 3. Erişim matrisi

| Kaynak | Researcher | Developer | CI |
|---|---|---|---|
| Hub reposu | Yazma | Okuma | — |
| Proje repoları | Okuma (isteğe bağlı) | Yazma | Okuma |
| Tracker | Okuma + yorum | Okuma + yorum | — |
| `wizrelay` ürün reposu | — | — | pip ile okuma |

## 4. Yayma sırası

1. **Hub**, `CODEOWNERS` ve dal korumasıyla
   ([5. Hub'ı kurmak](05-set-up-hub.md)). Bunlar olmadan push edebilen herkes kendi
   analizini yayınlayabilir.
2. **CI kapısı**, başlangıçta `on-missing-task: skip` ile.
3. **Repo ayarları**, yeni ekip arkadaşlarına plugin önerilsin diye.
4. **Bir repo bağlı**, ve geri kalanına yaymadan önce tüm döngüden geçmiş **bir gerçek
   task**. İlk task, `roles` sözlüğünün ve `critical_paths`'in doğru olup olmadığını
   keşfettiğin yer.
5. **Ekip politikası**, yalnızca birkaç task varsayılan yönlendirmenin nerede yanlış
   olduğunu gösterdikten sonra.
6. **Managed settings**, en son, ve yalnızca ihtiyacın varsa.

## 5. Yaymayı doğrulamak

Bir developer'ın makinesinde:

```
/wizrelay:doctor
```

Sonra plugin'in hiç kurulmadığı bir makinede
[4. Plugin'i kurmak](04-install-plugin.md) bölümündeki komutların çalıştığını ve
`/wizrelay:doctor`'ın temiz olduğunu doğrula.

Bir kontrolü bilerek yapmaya değer: manifest adı da `wizrelay` olan ikinci bir plugin kur ve
`doctor`'ın bunu hata olarak raporladığını doğrula. Aynı adlı iki plugin varken **yalnızca
biri hook'larını kaydeder ve kapsam koruması sessizce yok olur.** Heartbeat uyarısının var
olma sebebi bu, ve çalıştığını bilmenin tek yolu bir kez buna sebep olmak.

## 6. Ekibine ne söylemeli

Üç şey, daha fazlası değil:

1. **Planlamadan önce çek.** `/wizrelay:pull`, sonra `/wizrelay:plan`.
2. **Tıkandığında sor — genişletme.** `/wizrelay:ask`. Kapsam Researcher'ın kararıdır ve
   etrafından dolaşmak sorunu PR'a taşır.
3. **Bitti demeden doğrula.** `/wizrelay:verify`.

Geri kalanını plugin'in kendi ürettiği mesajlardan öğrenirler.

## Güncelleme

Marketplace girişinde ve CI'daki `pip install`'da bir sürüm sabitle. `wizrelay doctor` eski
şemayı raporlar ve `wizrelay migrate` dönüştürür; eski sürümlerin yazdığı kilit dosyaları
okunabilir kalır.

## Sonraki

[14. Özelleştirme](14-customisation.md).

<!-- nav:bottom -->
---

| ← | ↑ | → |
|:---|:---:|---:|
| [← 12. CI entegrasyonu](12-ci-integration.md) | [İçindekiler](README.md) | [14. Özelleştirme →](14-customisation.md) |
<!-- /nav:bottom -->
