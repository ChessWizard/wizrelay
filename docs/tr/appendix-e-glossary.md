<!-- nav:top -->
[Dokümantasyon](README.md) › **Ek E — Sözlük** &nbsp;·&nbsp; [English](../en/appendix-e-glossary.md)
<!-- /nav:top -->

# Ek E — Sözlük

Bu dokümantasyonun bildiğini varsayarak kullandığı her terim ve birbirine karıştırılması
kolay terim çiftleri.

| Terim | Anlamı |
|---|---|
| **Plugin** | Claude Code'a komut, kontrol ve ajan ekleyen araç (`wizrelay`). Hiçbir ekip içeriği taşımaz |
| **Hub** | Bir ekibin analiz paketlerini tutan özel git reposu. Kod yok; içindeki hiçbir dosya çalıştırılmaz. **Ekip başına bir tane** |
| **Paket** | Bir task'ın tüm analizi: `tasks/<ID>-<slug>/` |
| **Researcher dosyası** | Pakette nokta ile başlamayan ve developer adlarından biri olmayan her dosya. Developer reposunda salt okunur |
| **Developer dosyası** | `plan.md`, `questions.md`, `verification.md`, `notes/`. Hub'dan hiç gelmez, hiç ezilmez |
| **AC** | Kabul kriteri (`AC-1`, `AC-2` …). "Bitti"nin ne demek olduğu ve doğrulamanın neyi kanıtladığı |
| **D-nnn** | `decisions.md` içinde bir karar. Hiç silinmez; yenisiyle geçersiz kılınır |
| **Q-nnn** | `questions.md` içinde bir soru. Bir karar yanıtlayana kadar açık |
| **C-n** | `contracts.md` içinde bir sözleşme. Bir alan adının ya da hata kodunun tanımlandığı tek yer |
| **Rol** | Reponun bir task içindeki adı (`backend`, `frontend` …). Serbest metin; sözlüğü hub belirler |
| **Kapsam** | Rol başına, dokunulabilecek (`allow`) ve dokunulamayacak (`deny`) dosyalar |
| **Kapsam modu** | `strict`, `ask` ya da `off`. Task başına Researcher ayarlar |
| **Sinyal** | Bir task'ın `complexity`, `risk` ve `ambiguity` değerleri, her biri low/medium/high, artı isteğe bağlı `kind: mechanical` |
| **Profil** | Reponun nasıl olduğu: komutları, büyüklüğü, test olgunluğu, kritik ve legacy yolları |
| **Politika** | Bir skoru tier'a, tier'ı aşama başına model ve effort'a çeviren JSON |
| **Tier** | Model ve effort önerisinin seviyesi (T0–T4) |
| **Kilit** (`.lock.json`) | Hangi sürümün hangi hub commit'inden geldiğinin, dosya başına hash'le kaydı |
| **Hub kimliği** | Bir hub için normalize edilmiş, hash'li ad. Aynı makinedeki iki hub'ı ayrı tutan şey |
| **Hook** | Claude Code'un belirli bir olayda otomatik çalıştırdığı kontrol |
| **Heartbeat** | Bir oturumun hook'larının çalıştığının kaydı. Olmasa kapsam korumasını kaybetmek sessiz olurdu |
| **Persona** | Nerede olduğun: developer (`.wizrelay/config.json`), hub (`wizrelay-hub.json`), ya da hiçbiri — o zaman plugin sessiz |
| **Yan ürün** | Kapsam ihlali olmadan değişebilen bir yol: bir lockfile, üretilmiş bir client, `init`'in yazdığı dosyalar |
| **MCP** | Claude'un ClickUp gibi bir dış servise ulaştığı protokol |
| **Advisor** | Claude'un kritik anlarda daha güçlü bir modele danıştığı deneysel özellik. Yalnızca Anthropic API |
| **`opusplan`** | Bir model takma adı: plan modunda Opus, yürütmede Sonnet |
| **Değişmez (invariant)** | Uygulamanın ihlal etmesine izin verilmeyen bir özellik. On üç tane, her birinin bir testi var |

## Benzer görünen ama olmayan şeyler

**Kapsam modu ile kapsam.** Kapsam *hangi dosyalar*; mod ise başka bir şeye dokunulduğunda
*ne olacağı*.

**Mod olarak `ask` ile komut olarak `/wizrelay:ask`.** Mod, kapsam dışı bir düzenlemeden
önce sana sorar. Komut, pakete bir soru sorar — ve pakette yanıt yoksa Researcher'a.

**`KAPSANMADI` ile `KALDI`.** `KALDI`, kriterin kontrol edildiği ve kodun yanlış olduğu
anlamına gelir. `KAPSANMADI`, repoda kriteri kanıtlayan bir şey olmadığı — genellikle testin
henüz var olmadığı anlamına gelir.

**Doğrulama (validation) ile doğrulama (verification).** Validation, Researcher'ın yayından
önce pakete uyguladığı kapı. Verification, developer'ın bitti demeden önce işe uyguladığı
kapı.

**Hub ile tracker.** Tracker task'ı tutar. Hub task'ın analizini tutar. Farklı şeyler ve hub
tracker'ın yerine geçmez.

**`doctor` ile `status`.** `doctor` yapılandırmayı kontrol eder. `status` bu oturumu. Bir
yapılandırma kusursuz olabilirken hook'lar burada çalışmamış olabilir.

<!-- nav:bottom -->
---

| ← | ↑ | → |
|:---|:---:|---:|
| [← Ek D — Kontrol listeleri](appendix-d-checklists.md) | [İçindekiler](README.md) | &nbsp; |
<!-- /nav:bottom -->
