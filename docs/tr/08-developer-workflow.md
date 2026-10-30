<!-- nav:top -->
[Dokümantasyon](README.md) › **8. Developer: task'ı uygulamak** &nbsp;·&nbsp; [English](../en/08-developer-workflow.md)
<!-- /nav:top -->

# Developer: task'ı uygulamak

Paketi çekmek, ona göre planlamak, kontroller devredeyken uygulamak ve kanıtla doğrulamak.

## Akış

```
/wizrelay:pull → (önerilen model) → /wizrelay:plan → uygula → (/wizrelay:ask) → /wizrelay:verify → PR
```

## 1. Task'ı çekmek

Tracker'da `[WIZRELAY-PUBLISH]` yorumunu gördüğünde kendi reponda:

```
/wizrelay:pull CU-86c1abcd
```

Ham kimlik de kabul edilir: `/wizrelay:pull 86c1abcd`. Task URL'si de, paket klasörünün adı
da.

Aldığın çıktı:

```text
CU-86c1abcd v1 — Tenant bazlı günlük API istek kotası
8 researcher dosyası kopyalandı.
Sizin için oluşturuldu: plan.md, questions.md
Kapsam içi: app/quota/**, app/api/limits.py, tests/quota/**

Yönlendirme: T2-standard (skor 6)
  plan       opus / high
  implement  sonnet / high
  verify     sonnet / high
  ask        sonnet / low

Bu task'ın oturumunu şununla başlatın:
  claude --model opusplan --effort high --name 'CU-86c1abcd Tenant bazlı günlük API istek kotası'
```

Task başlığı bir mesaj değil, paket verisi: Researcher nasıl yazdıysa, hangi dilde yazdıysa
öyle görünür. Etrafındaki etiketler `--lang` ile değişir, başlık değişmez. Buradaki çıktı,
[`examples/`](../../examples/) içindeki örnek paketin gerçek çıktısıdır; İngilizce
dokümandaki aynı örnek başlığı çevrilmiş gösterir.

Ardından Claude 15 satırı geçmeyen bir brifing verir: hedef, **senin** kriterlerin, kapsam,
bağlayıcı kararlar, sözleşmeler ve riskler. Bu aşamada kod yazmaz — kasıtlı, ve sapmanın
genellikle başladığı adım bu.

O brifingin değerli kısmı sonu: pakette belirsiz, çelişkili ya da eksik olan her şey. Oku.
"AC-2'nin doğrulama komutu yok" şimdi beş dakika, sonra bir öğleden sonra eder.

Projende oluşan dosyalar:

```
.wizrelay/tasks/CU-86c1abcd-tenant-bazli-gunluk-api-istek-kotasi/
├── task.json, research.md, scope.md, acceptance.md, contracts.md, decisions.md
├── roles/backend.md, roles/frontend.md   ← diğer rolü de görürsün (bağlam için)
├── .lock.json                            ← sürüm, hub commit'i, dosya hash'leri, yönlendirme
├── plan.md                               ← senin
└── questions.md                          ← senin
```

Claude researcher dosyalarını değiştiremez. **Sen** elle değiştirirsen her oturum açılışında
"yerelde değiştirilmiş" uyarısı görürsün ve `/wizrelay:sync` dosyayı geri yükler.

**Dal adı:** task kimliğini içeren bir ad kullan, örneğin
`feature/CU-86c1abcd-tenant-kota`. Böylece aktif task daldan otomatik bulunur — worktree'ler
dahil — ve CI kapısı task'ı tanır.

## 2. Doğru model ve effort ile çalışmak

İki yol:

1. **Önerilen komutla yeni oturum başlat (önerilir):**
   ```bash
   claude --model opusplan --effort high --name 'CU-86c1abcd Tenant kota'
   ```
2. **Mevcut oturumu ayarla:** `/model` ile modeli seç (seçicide `s` tuşu yalnızca bu oturuma
   uygular) ve `/effort high` yaz.

Terimler:

- `opusplan` — plan modunda Opus, yürütmede Sonnet.
- `--advisor opus` — yüksek riskli task'larda görülür. Claude kritik anlarda Opus'a
  danışır. Deneysel ve yalnızca Anthropic API'de.

Önerilenden zayıf bir modele geçmeye çalışırsan plugin onay ister. Bu bir yasak değil;
seçimi bilinçli yapmaya yönelik bir dürtme.

## 3. Planlamak

```
/wizrelay:plan
```

1. Claude plan moduna geçer; bu modda dosya değiştirmez. Plan moduna Shift+Tab ile sen de
   geçebilirsin.
2. Paketin tamamını okur ve kod eşlemesini — kriter → dosya/sembol → test —
   `codebase-mapper` yardımcısına yaptırır.
3. Planı sunar: hedef, kriter eşlemesi, adımlar (her biri bir kritere bağlı ve yalnızca
   kapsam içi dosyalara dokunan), riskler, açık sorular.
4. Onaylarsan planı `plan.md`'ye yazar.
5. Uygulama için kopyalayabileceğin bir `/goal` satırı önerir:

```
/goal backend rolünün AC-1…AC-4 kriterlerinin her biri için ilgili test bu konuşmada geçti olarak gösterildi, plan.md'deki adımların hepsi [x] ve kapsam dışı dosya değişmedi; ya da 30 turda dur
```

`/goal` ile Claude koşul sağlanana kadar turları kendisi sürdürür; her tur sonunda ayrı bir
değerlendirici model koşulu kontrol eder.

Planda açık soru çıktıysa uygulamaya geçmeden önce `/wizrelay:ask` ile sor.

## 4. Uygulamak ve kontrolleri tanımak

Normal çalışırsın — "plan.md'deki 1. adımı uygula". Arka planda:

| Ne zaman | Ne olur |
|---|---|
| Her oturum açılışında | Aktif task'ın özeti Claude'a verilir. Sıkıştırmadan sonra yeniden verilir |
| Her mesajda | Tek satırlık hatırlatıcı eklenir: `[WIZRELAY] Aktif task CU-86c1abcd · research v1 · rol backend · kapsam modu strict · açık soru 0` |
| Her dosya düzenlemesinden önce | Kapsam kontrol edilir |
| Her tur sonunda | Git durumu taranır |

Karşılaşabileceğin mesajlar:

| Durum | Mesaj, plugin'in kendi ifadesiyle | Ne yapmalı |
|---|---|---|
| Researcher dosyası düzenlenmek istendi | `acceptance.md Researcher'a aittir ve burada salt okunurdur (CU-86c1abcd). /wizrelay:ask ile sorun; yanıt yeni bir paket sürümü olarak gelir.` | Değişiklik gerekiyorsa `/wizrelay:ask` |
| Açıkça yasak alan (`deny`) | `app/billing/invoice.py, CU-86c1abcd kapsamı tarafından açıkça yasaklanmış (app/billing/** kalıbı).` | Gerçekten gerekiyorsa gerekçeyi `questions.md`'ye yaz ve `/wizrelay:ask` |
| Kapsam dışı, `strict` | `README.md, CU-86c1abcd kapsamının dışında. Kapsam içi: app/quota/**, … Kapsamı yerel olarak genişletmek yerine /wizrelay:ask ile soru açın.` | Aynısı |
| Kapsam dışı, `ask` modu | Aynı ilk cümle, ret yerine onay istemi olarak | Bilinçli onay ya da ret; onaylarsan `/wizrelay:verify` bunu raporlar |
| Tur sonu uyarısı | `wizrelay: bu tur CU-86c1abcd kapsamının dışındaki dosyaları değiştirdi.` ardından dosya başına bir satır | Geri al ya da sor |

Engellenen bir değişikliği shell komutu ya da script ile yapmaya çalışmak hem protokole
aykırı hem de sonradan yakalanıyor — tur sonu denetimi, `/wizrelay:verify` ve CI
tarafından.

## 5. Sormak

```
/wizrelay:ask Retry-After başlığı saniye mi tarih mi olmalı?
```

Claude yalnızca paketten yanıt verir ve kaynağını gösterir:

```text
Saniye cinsinden. acceptance.md#AC-1, Retry-After'ın bir sonraki UTC gece yarısına kalan
saniye olduğunu söylüyor; roles/backend.md#Tuzaklar da bunun tarih değil saniye olduğunu
vurguluyor.
Repodaki karşılığı: app/core/errors.py içindeki ApiError şu an başlık desteklemiyor;
eklenmesi gerekecek.
Kaynaklar: acceptance.md#AC-1, roles/backend.md#Tuzaklar
```

Bu skill'i elle çağırmana gerek yok. "Bu kriter ne demek" ya da "bu kapsamda mı" diye
sorduğunda Claude onu kendiliğinden kullanır. Öğrenmek için de işe yarar: "kota sayacının
neden atomik upsert ile yapıldığını açıkla".

Pakette yanıt yoksa:

1. **Claude karar uydurmaz.** Soruyu `questions.md`'ye `Q-001` olarak kaydeder — gördüğü
   seçeneklerle ve yanıt olmadığında ne yapacağıyla birlikte.
2. Göndermek için onayını ister. Onaylarsan task'a
   `[WIZRELAY-Q] Q-001 — CU-86c1abcd — backend` yorumu düşer ve Researcher etiketlenir.
3. Bu sırada soruya bağlı olmayan adımlarla devam edersin.

O birinci madde bu sistemdeki en önemli davranış. Researcher'ın hiç vermediği makul bir
yanıt karar gibi görünür, uygulanır ve kimse uydurulduğunu bilmez.

## 6. Yeni sürüm geldiğinde

Researcher v2 yayınlarsa bir sonraki oturum açılışında şunu görürsün:

```text
WIZRELAY: Hub'da research v2 yayınlandı (sizde v1). Devam etmeden önce /wizrelay:sync
çalıştırın.
```

```
/wizrelay:sync
```

Değişen dosyaları ve farkı gösterir. Claude etkiyi analiz eder ve onayınla:

- `plan.md`'de etkilenen adımları işaretler ve gerekeni ekler,
- yanıtlanan sorunun durumunu `YANITLANDI (D-004)` yapar,
- daha önce yazılmış kodda yeni sürümle çelişen yerleri listeler.

Önce `decisions.md`'yi oku. Yeni bir karar, zaten yaptığın bir şeyi tersine çevirebilecek
türde bir değişiklik.

## 7. Doğrulamak

```
/wizrelay:verify
```

Bağımsız bir doğrulayıcı (`test-engineer`) ayrı bir bağlamda çalışır. Kodu yazan konuşmayı
görmez; yalnızca kanıta bakar:

1. Proje komutlarını çalıştırır — önce kriterlere karşılık gelen hedefli testler, sonra tüm
   paket.
2. Her kriter için hüküm verir: `GEÇTİ`, `KALDI` ya da `KAPSANMADI`.
3. Deterministik kapsam ve bütünlük denetimini rapora ekler.
4. `verification.md`'yi yazar. Koda dokunmaz — dokunamaz; düzenleme araçları
   yapılandırmayla kaldırılmış.
5. `[WIZRELAY-VERIFY]` yorumunu göndermek için onay ister.

Örnek özet:

```text
Genel sonuç: KISMİ
- AC-1 GEÇTİ — pytest tests/quota/test_quota_exceeded.py (3 passed)
- AC-2 GEÇTİ — pytest tests/quota/test_quota_concurrency.py (1 passed)
- AC-3 KAPSANMADI — idempotency için test yok (önerilen: tests/quota/test_quota_idempotency.py)
- AC-4 GEÇTİ — pytest tests/api/test_messages_quota.py (2 passed)
Kapsam denetimi: temiz · Research bütünlüğü: temiz
```

`KALDI` ya da `KAPSANMADI` varsa ana oturuma dön ve Claude'dan eksiği gidermesini iste —
"AC-3 için önerilen testi yaz" — sonra `/wizrelay:verify`'ı tekrar çalıştır.

Bir kapsam ihlali, testler ne kadar iyi geçerse geçsin genel sonucu `KISMİ` ile sınırlar.
Kapsam içi bir uygulama üstüne başka bir şeyi de değiştirdiyse, o task bitmiş değildir.

## 8. Bitirmek

- **Commit mesajlarında kriter kimlikleri kullan:**
  `feat(quota): idempotency kaydı (AC-3)`.
- **`.wizrelay/tasks/<klasör>/` klasörünü commit et:** paket kopyası, `plan.md`,
  `questions.md`, `verification.md`. Bu, PR'ın hangi research sürümüne göre yazıldığını
  gösterir ve CI kapısı buna ihtiyaç duyar.
- **PR aç;** CI kapsam denetimini çalıştırır ([12. CI entegrasyonu](12-ci-integration.md)).

## Birden fazla task

- `/wizrelay:status` aktif task'ı, sürümü, plan ilerlemesini, açık soruları ve uyarıları
  gösterir.
- Aktif task dal adından bulunur, yani dal değiştirmek task değiştirmek demektir.
- Elle seçmek için: `wizrelay activate <klasör>`.

## Sonraki

[9. Soru ve sürüm döngüsü](09-question-loop.md) — sorduktan sonra Researcher tarafında ne
olduğu.

<!-- nav:bottom -->
---

| ← | ↑ | → |
|:---|:---:|---:|
| [← 7. Researcher: hazırlamak ve yayınlamak](07-researcher-workflow.md) | [İçindekiler](README.md) | [9. Soru ve sürüm döngüsü →](09-question-loop.md) |
<!-- /nav:bottom -->
