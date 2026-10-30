<!-- nav:top -->
[Dokümantasyon](README.md) › **11. Kapsam koruması** &nbsp;·&nbsp; [English](../en/11-scope-protection.md)
<!-- /nav:top -->

# Kapsam koruması

Beş katman, her birinin gerçekten neyi durdurduğu, glob sözdizimi ve gizlenmek yerine
belgelenen atlatma yolları.

## Katmanlar

| Katman | Ne zaman | Ne yapar |
|---|---|---|
| 1. İzin kuralları (`.claude/settings.json`) | Her düzenleme | Researcher dosyalarını kesin korur; `sed`, `tee` ve shell yönlendirmeleri dahil |
| 2. Düzenleme kontrolü (`PreToolUse` hook'u) | Her düzenleme | Kapsamı uygular ve nedenini hem Claude'a hem sana açıklar |
| 3. Tur sonu denetimi (`Stop` hook'u) | Her yanıtın sonunda | Git'teki her değişikliği tarar ve uyarır |
| 4. `/wizrelay:verify` | İş bittiğinde | İhlalleri rapora işler |
| 5. CI kapısı | PR'da | Merge'ü engeller |

Tek bir katman yetmez ve her biri üstündekinin kaçırdığını yakalar. Katman 1 kesin ama
statik — hangi task'ın aktif olduğunu bilemez. Katman 2 canlı kapsamı bilir ama yalnızca
Claude'un dosya araçlarını görür. Katman 3 git'in gördüğü her şeyi görür ama olaydan sonra.
Katman 5, developer'ın kendi oturumunda çalışmayan tek katman.

## Modlar

| Mod | Davranış |
|---|---|
| `strict` | Kapsam dışı düzenleme engellenir |
| `ask` | Kapsam dışı düzenleme onay ister; `deny` listesi yine kesin engeller |
| `off` | Kapsam kontrolü yok; researcher dosyaları **yine** korunur |

Modu task başına Researcher seçer
([7. Researcher akışı](07-researcher-workflow.md)).

`off`'un researcher dosyalarını yine korumaması kasıtlı. `off` *kapsamı* kapatır; düzenlenmiş
bir `acceptance.md` "bitti"nin ne demek olduğunu sessizce değiştirir ve kilidi hub'la
çelişkiye düşürür.

## Karar sırası

Katman 2 şu sırayla karar verir, ve sıra tasarımın kendisi:

```
1. repo dışı yol                     → karar yok
2. researcher dosyası                 → deny, her modda
3. developer dosyası ya da .wizrelay/ → karar yok
4. aktif task yok, ya da mod `off`    → karar yok
5. rol için kapsam tanımlı değil      → ask
6. açık bir `deny` eşleşmesi          → deny, her modda
7. `allow` ya da yan ürün eşleşmesi   → karar yok
8. geri kalan                         → `strict`'te deny, `ask`'ta ask
```

Adım 2 kasten adım 4'ün üstünde, ve "off yine researcher dosyalarını korur" ifadesini doğru
kılan şey bu. Adım 5 tahmin etmek yerine soruyor: rolün hakkında hiçbir şey söylemeyen bir
task, bir yapılandırma boşluğudur, izin değil.

"Karar yok", Claude Code'un normal izin akışının dokunulmadan bırakıldığı anlamına gelir.
Hook asla "izin ver" döndürmez, çünkü bu senin hiç vermediğin bir izni **vermek** olurdu.

## Glob kopya kağıdı

| Kalıp | Eşleşir | Eşleşmez |
|---|---|---|
| `app/quota/**` | `app/quota/service.py`, `app/quota/x/y.py` | `app/quota`'nın kendisi, `app/quotas/a.py` |
| `app/quota` | `app/quota` ve altındaki her şey | `app/quotas/a.py` |
| `src/*.ts` | `src/a.ts` | `src/b/a.ts` |
| `tests/**/test_*.py` | `tests/test_x.py`, `tests/a/b/test_x.py` | `tests/a/x_test.py` |
| `alembic/versions/*.py` | `alembic/versions/0012_quota.py` | `alembic/env.py` |
| `poetry.lock` (eğik çizgisiz) | **Her derinlikte** `poetry.lock` | — |
| `build/` | `build` altındaki her şey | — |

Kurallar:

- Yollar repo köküne göredir.
- `**` klasörler arası geçer; `*` asla `/` geçmez.
- `..`, mutlak yol ve sürücü harfi reddedilir.
- Eğik çizgi içermeyen bir kalıp, gitignore satırı gibi, o adı her derinlikte eşler.

## Her zaman serbest

- Developer'a ait task dosyaları: `plan.md`, `questions.md`, `verification.md`, `notes/`
- Her derinlikteki lockfile'lar: `poetry.lock`, `uv.lock`, `package-lock.json`,
  `pnpm-lock.yaml`, `yarn.lock`, `go.sum`, `Cargo.lock`, `composer.lock`, `Gemfile.lock`,
  `packages.lock.json`, `Pipfile.lock`
- `wizrelay init`'in kendi yazdığı dosyalar: `CLAUDE.md`, `.gitignore`,
  `.claude/settings.json`, `.claude/settings.local.json`, `.mcp.json`
- `.wizrelay/` altındaki her şey
- `profile.json`'daki `incidental_allow` listesi
- Repo dışındaki dosyalar — plugin karar vermez; Claude Code'un normal izinleri geçerli

Üçüncü grup belirli bir sebeple orada. Olmasa, `init` sonrası ilk denetim dört ihlal
raporlardı — hem de developer'ın güvenmek için henüz bir sebebi olmadığı tek raporda.
Hariç tutmak yerine *yan ürün* olarak raporlanıyorlar, böylece bir inceleyici onları yine
görüyor.

## Neyi korur, neyi korumaz

**Bu, kazara sapmaya karşı bir korkuluk, güvenlik sınırı değil.** Plugin'i kapatan,
ayarları düzenleyen ya da bir script'le dosya yazan biri etrafından dolaşabilir.

| Katman | Durdurmadığı |
|---|---|
| İzin kuralları | Dosyaları kendi açan bir Python ya da Node script'i |
| Düzenleme hook'u | Aynı alt süreç boşluğu |
| Tur sonu denetimi | Hiçbir şey — yalnızca raporlar |
| `/wizrelay:verify` | Onu çalıştırmayan bir developer |
| CI kapısı | Zorunlu kontrolü olmayan bir dala doğrudan push |

Belgelenmiş atlatma yolları, açıkça yazılı çünkü sınırları belgelenmemiş bir korkuluk
yapmadığı şeyler için güvenilir hâle gelir:

- Plugin'i `/plugin`'den ya da repo ayarlarından kapatmak.
- `.claude/settings.json`'u düzenleyip deny kurallarını kaldırmak.
- Dosyaları bir alt süreçten yazmak. Claude Code'un kendi dokümanı, Read ve Edit deny
  kurallarının dosyaları adlandırmadan açan bir komutu kapsamadığını söylüyor.
- `bypassPermissions` modunda çalışmak.

Bunları daraltanlar: **CI kapısı** ([12. CI entegrasyonu](12-ci-integration.md)) ve
**managed settings** ([13. Ekip ve kurum](13-team-and-enterprise.md)). Alt süreçleri de
kapsayan bir zorlama için Claude Code'un kendi sandbox'ını bununla birlikte etkinleştir.

## Bütünlük, kapsamdan ayrı olarak

Kilit dosyası researcher dosyası başına bir sha256 kaydeder. Bu ikinci ve bağımsız bir
kontrol verir: "kapsam dışında bir şey mi düzenledin" değil, "analiz kopyan hâlâ yayınlanan
şey mi".

Değişmiş, eksik ya da kayıtsız bir researcher dosyası oturum başlangıcında, tur sonu
denetiminde ve `/wizrelay:verify`'da raporlanır. `/wizrelay:sync` geri yükler.

Hash'leme CRLF'yi LF'ye normalize eder, böylece hub'ın Windows checkout'u ile aynı commit'in
macOS checkout'u anlaşır. Bu olmadan `sync` her çalıştırmada tüm paketi bozuk raporlardı.

## Hata politikası ve neden asimetrik

| Bileşen | Hata durumunda |
|---|---|
| Düzenleme hook'u (`PreToolUse`) | **Fail-closed.** Çökme ya da zaman aşımı düzenlemeyi engeller; iç hata onay ister |
| Geri kalan her şey | **Fail-open.** Hata yutulur ve oturum devam eder |

Fail-open bir koruma koruma değildir. Ama bir oturum wizrelay yüzünden asla kullanılamaz
hâle gelmemeli: bozuk bir oturum başlangıcı bağlama mal olur, oturumu iptal eden bozuk bir
oturum başlangıcı kullanıcının işine mal olur.

## Engellendiğinde

```
Engellendim
 ├─ Dosya Researcher'ın mı? ── evet ──► /wizrelay:ask (değişiklik talebi)
 ├─ Bu değişiklik planda var mı? ── hayır ──► planı tekrar oku; gerçekten gerekiyorsa ↓
 └─ Gerekçeyi questions.md'ye yaz → /wizrelay:ask → Researcher kapsamı genişletir
    → /wizrelay:sync → devam
```

## Korumanın aktif olduğunu doğrulamak

İki farklı soru, ve ikincisi insanları ısıran:

- **`/wizrelay:doctor`** yapılandırmayı kontrol eder.
- **`/wizrelay:status`** *bu oturumu* kontrol eder. Çıktısı bir `WIZRELAY_NO_GUARD`
  uyarısıyla başlıyorsa, yapılandırma doğru olmasına rağmen hook'lar burada çalışmadı.

Bunun nasıl olduğu ve çözümleri [16. Sorun giderme](16-troubleshooting.md)'de.

## Sonraki

[12. CI entegrasyonu](12-ci-integration.md) — developer'ın oturumunda çalışmayan katman.

<!-- nav:bottom -->
---

| ← | ↑ | → |
|:---|:---:|---:|
| [← 10. Model ve effort yönlendirmesi](10-routing.md) | [İçindekiler](README.md) | [12. CI entegrasyonu →](12-ci-integration.md) |
<!-- /nav:bottom -->
