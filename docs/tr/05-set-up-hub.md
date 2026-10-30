<!-- nav:top -->
[Dokümantasyon](README.md) › **5. Ekip hub'ını kurmak** &nbsp;·&nbsp; [English](../en/05-set-up-hub.md)
<!-- /nav:top -->

# Ekip hub'ını kurmak

Ekibinin analizini tutan repoyu oluşturmak ve onu güvenilir kılan iki ayar.

## Kaç hub gerekir?

| Durum | Yeni hub? |
|---|---|
| Ekibe yeni bir proje reposu katıldı | **Hayır** — mevcut hub'a bağlanır |
| Aynı ekipte yeni bir task | **Hayır** — hub'a yeni bir paket eklenir |
| Kişisel projelerin | Evet — ayrı, kişisel bir hub |
| Başka bir şirket ya da ekip bu ürünü kullanacak | Evet — kendi hub'ını açar, seninkini görmez |
| Şirket içinde erişimi ayrılması gereken bir ekip | Evet |

## 1. Repoyu oluştur

GitHub'da (ya da GitLab, Azure Repos) **özel** bir repo aç, örneğin `acme/research-hub`.

| Kim | Erişim |
|---|---|
| Researcher(lar) | Yazma |
| Developer'lar | Okuma |
| CI | Gerekmez — CI projedeki kopyayı kullanır |

Klonla ve Claude Code'u içinde aç:

```bash
git clone git@github.com:acme/research-hub.git
cd research-hub
claude
```

## 2. `/wizrelay:hub-init` çalıştır

```
/wizrelay:hub-init
```

Claude şunları sorar (parantez içinde örnek yanıtlar):

1. Hub adı (`acme-research-hub`)
2. Dil (`tr`)
3. Tracker türü (`clickup`) ve ID öneki (`CU-`)
4. Ekipteki roller (`backend, frontend, infra, mobile`)
5. Yeni paketlerde varsayılan kapsam modu (`strict`)
6. Tracker MCP bağlantısı bu repoya eklensin mi (`evet`)

Sonuçta oluşan yapı:

```
research-hub/
├── wizrelay-hub.json           ← hub kimliği ve ekip varsayılanları
├── CLAUDE.md                   ← bu repoda Claude'un nasıl çalışacağı (Researcher protokolü)
├── .mcp.json                   ← tracker bağlantısı
├── policies/
│   └── routing-policy.json     ← ekibin model/effort politikası (varsayılanın kopyası)
├── templates/
│   └── package/                ← ekibe özel paket şablonları (isteğe bağlı)
└── tasks/                      ← paketler burada birikecek
```

## 3. `wizrelay-hub.json`

```json
{
  "schema_version": 1,
  "name": "acme-research-hub",
  "language": "tr",
  "tracker": { "type": "clickup", "id_prefix": "CU-" },
  "roles": ["backend", "frontend", "infra", "mobile"],
  "default_branch": "main",
  "base_ref": "origin/main",
  "default_enforcement": "strict"
}
```

| Alan | Anlamı | Değiştirince ne olur |
|---|---|---|
| `language` | Şablonların ve mesajların varsayılan dili | Yeni bağlanan projeler bu dili alır |
| `tracker` | Tracker türü ve ID öneki | `/wizrelay:hub-new 86c1abcd` paketi `CU-86c1abcd` olarak adlandırır |
| `roles` | Ekipte kullanılan rol adları | `init` ve `validate` bu listeyi kullanır. Küçük harf; tire kullanılabilir |
| `default_branch` | Hub'ın yayın dalı | Projeler paketleri bu daldan çeker |
| `base_ref` | Projelerde kapsam denetiminin karşılaştırma tabanı | `audit`'in varsayılanı olur |
| `default_enforcement` | Yeni paketlerin kapsam modu | `strict`, `ask` ya da `off` |

`roles`, taahhüt etmeden önce üzerinde konuşulmayı hak eden alan. Her paketin çekeceği
sözlük bu, bu yüzden şimdi anlaşmak task başına isim uydurmaktan iyi.

## 4. Tracker bağlantısı

ClickUp seçtiysen `/wizrelay:hub-init` resmi ClickUp MCP sunucusunu `.mcp.json`'a ekler.
Elle eklemek için:

```bash
claude mcp add --scope project --transport http clickup https://mcp.clickup.com/mcp
```

Sonra Claude Code'da `/mcp` yaz, ClickUp'ı seç ve tarayıcıda açılan OAuth akışını tamamla.
ClickUp sunucusu API anahtarı değil OAuth kullanır.

Diğer tracker'lar için [Ek A](appendix-a-commands.md)'ya ve
[16. Sorun giderme](16-troubleshooting.md)'ye bak. **Resmi uç noktası doğrulanmamış bir
tracker seçersen `hub-init` hiçbir dosyaya bir şey yazmaz** — yalnızca nasıl bağlanacağını
anlatır. Bu kasıtlı: yapılandırmandaki tahmin edilmiş bir uç nokta, plugin bozukmuş gibi
görünen bir şekilde başarısız olur ve kimlik bilgilerini yanlış host'a yöneltebilir.

## 5. Ekip politikası (isteğe bağlı)

`policies/routing-policy.json`, hangi durumda hangi model ve effort'un önerileceğini
belirler ([10. Yönlendirme](10-routing.md)). İlk haftalarda varsayılanı olduğu gibi bırak;
birkaç task gördükten sonra eşikleri ayarla.

Dosyayı silersen plugin'in kendi varsayılanı kullanılır.

## 6. Erişim ve koruma

Bu iki ayar, hub'ı paylaşılan bir klasör değil *doğruluk kaynağı* yapan şey.

**`CODEOWNERS`:**

```
/tasks/      @acme/research
/policies/   @acme/research
```

**`main` dal koruması:** birden fazla Researcher varsa PR zorunlu olsun ve CODEOWNERS onayı
istensin.

**Yayın modeli:** tek Researcher varsa doğrudan `main`'e göndermek sorun değil. Birden
fazlaysa PR daha güvenli — `/wizrelay:hub-publish` hangisini istediğini sorar.

Bunlar olmadan, push edebilen herkes kendi analizini yayınlayabilir ve tek doğruluk kaynağı
tek olmaktan çıkar.

## 7. İlk commit

```bash
git add -A && git commit -m "chore: araştırma hub'ı kurulumu" && git push
```

## Aynı makinede birden fazla hub

Kendi projelerin için ikinci bir hub tutabilirsin, örneğin `~/code/personal-hub`. Her proje
reposu yalnızca bağlı olduğu hub'ı görür.

Aynı makinedeki iki hub, normalize edilmiş hub kimliğine göre anahtarlanmış ayrı önbellekler
tutar; aynı task kimliğinin iki hub'da da bulunması içerikleri karıştırmaz. Her projedeki
kilit dosyası kopyasının hangi hub'dan geldiğini kaydeder.

## Sonraki

[6. Bir repoyu bağlamak](06-connect-repository.md) — repo başına bir kez.

<!-- nav:bottom -->
---

| ← | ↑ | → |
|:---|:---:|---:|
| [← 4. Plugin'i kurmak](04-install-plugin.md) | [İçindekiler](README.md) | [6. Bir repoyu bağlamak →](06-connect-repository.md) |
<!-- /nav:bottom -->
