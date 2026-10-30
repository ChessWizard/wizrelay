<!-- nav:top -->
[Dokümantasyon](README.md) › **2. Ne yapar, ne yapmaz** &nbsp;·&nbsp; [English](../en/02-scope.md)
<!-- /nav:top -->

# Ne yapar, ne yapmaz

Bu aracın sınırı: taahhüt ettiği hedefler, kasten dokunmadığı yerler ve verebildiği ile
veremediği garantiler.

## Ne için var

wizrelay, **bir kişinin analiz ettiği ve birkaç kişinin uyguladığı** bir ekip
için, ve her uygulayıcının bir AI kodlama oturumunda çalıştığı durum için.

Şunlardan en az ikisini tanıyorsan kurmaya değer:

- Bir developer analizin istemediği bir şeyi uyguladı ve bu review'a kadar farkedilmedi.
- İki rol bir arayüzün iki yanını uyguladı ve uymadılar.
- Bir developer yanıtsız bir soruya çarptı, tahmin etti ve tahmin canlıya çıktı.
- Riskli bir değişiklik zayıf bir modelde çalıştı, çünkü oturum öyle başlamıştı.
- Analiz bir dokümandaydı ve uzun bir oturumun ortasında artık konuşmada değildi.

Kendi analiz ettiği bir task üzerinde tek başına çalışan bir developer için kurmaya
**değmez**. Korunacak bir devir yok.

## Hedefler ve nasıl ölçülür

| # | Hedef | Çalıştığını nasıl anlarsın |
|---|---|---|
| G1 | Tek doğruluk kaynağı | Sürümlü paketler hub'da; developer repolarında hash'le doğrulanmış salt okunur kopya |
| G2 | Deterministik bağlam | Paket özeti her oturum başında **ve her sıkıştırmadan sonra** yeniden enjekte edilir |
| G3 | Kapsam koruması | Beş katman: izin kuralları, hook, tur sonu denetimi, doğrulama, CI |
| G4 | Soru döngüsü | Paketin yanıtlamadığı soru Researcher'a ulaşır ve yeni bir sürümde karar olarak döner |
| G5 | Model ve effort yönlendirmesi | Politika tabanlı; task'ın sinyalleri ve reponun profilinden hesaplanır |
| G6 | Doğrulama developer'da | Bağımsız doğrulayıcı her kriteri kanıtla eşler; rapor tracker'a gider |
| G7 | Her yerde kullanılabilir | Tracker adaptörleri, serbest roller, çapraz platform, İngilizce ve Türkçe, CI entegrasyonu |

## Kasten yapmadıkları

| Bu değil | Neden |
|---|---|
| **Tracker'ının yerine geçmek** | Tracker işin takip edildiği yer olarak kalır. Hub *analizi* tutar, task listesini değil |
| **OS seviyesinde sandbox sağlamak** | Hedef kazara sapmaya karşı bir korkuluk, hapishane değil. OS seviyesi zorlama için Claude Code'un kendi sandbox'ı var |
| **Sunucu ya da SaaS bileşeni çalıştırmak** | Barındırılacak bir şey yok. Hub bir git reposu; geri kalan her şey yerel |
| **Kendi LLM API çağrılarını yapmak** | Her şey Claude Code üzerinden, senin hesabında, senin modellerinle yürür |
| **GUI sağlamak** | Claude Code içinde komutlar ve bir CLI |
| **claude.ai sohbetinde ya da Cowork'te çalışmak** | Hedef yüzey Claude Code: terminal, IDE eklentileri ve masaüstü uygulamasının Code sekmesi |

## Neyi garanti eder, neyi etmez

Bu ayrım bu sayfadaki her şeyden önemli.

### Garanti eder

- Developer reposundaki bir researcher dosyası, Claude'un dosya araçlarıyla ya da Claude
  Code'un Bash'te tanıdığı dosya komutlarıyla (`sed`, `tee`, `>` yönlendirmesi)
  **düzenlenemez**. Hiçbir kapsam modunda.
- Bir developer dosyası — `plan.md`, `questions.md`, `verification.md`, `notes/` — `pull`
  ya da `sync` tarafından **asla ezilmez**.
- Hub paketindeki nokta ile başlayan bir dosya developer reposuna **asla ulaşmaz**.
- Yalnızca `published` bir paket çekilebilir; açık bir bayrak geçilmedikçe.
- Kilit dosyası hangi research sürümünün hangi hub commit'inden geldiğini, dosya başına
  hash'le kaydeder; değiştirilmiş bir kopya tespit edilebilir.
- İşaretçi dosyası olmayan bir dizin **hiçbir şey** almaz: çıktı yok, yazılan dosya yok, ağ
  yok.

### Garanti etmez

- Bir developer'ın plugin'i kapatamayacağını, `.claude/settings.json`'u düzenleyemeyeceğini
  ya da izin istemlerini atlayan bir modda çalışamayacağını.
- Oturumun yazıp çalıştırdığı bir Python ya da Node script'inin istediği dosyaya
  dokunamayacağını. Claude Code'un deny kuralları kendi dosya araçlarını ve tanıdığı
  komutları kapsar — rastgele bir alt süreci değil.
- Analizin *doğru* olduğunu. Herkesin aynı analizden çalıştığını ve ona katılmamanın sessiz
  değil görünür bir eylem olduğunu garanti eder.

Geri kalanı atlatan bir developer'ın karşısında ayakta kalan iki katman **CI kapısı** ve
**managed settings**. Bunu önemseyen bir ekip en azından CI kapısını çalıştırır.
[11. Kapsam koruması](11-scope-protection.md) katman katman anlatıyor.

## Neye mal olur

Dürüst hesap, çünkü her oturuma bağlam ekleyen bir araç senin token'ını harcıyor:

| Maliyet | Büyüklük |
|---|---|
| Modelin gördüğü skill ve ajan açıklamaları | ≤ 1500 karakter |
| Oturum başlangıcı bağlamı | ≤ 8000 karakter, hedef ≤ 3000 |
| Mesaj başına çapa | ≤ 250 karakter |
| Hook gecikmesi, ağsız | p95 300 ms altı |
| Hub yenilemesiyle oturum başlangıcı | 5 sn altı; ağ çağrısı 4 sn'de zaman aşımına uğrar ve sessizce atlanır |

Yan etkili skill'ler `disable-model-invocation: true` taşıyor, yani model onların
açıklamalarını hiç görmüyor — ona yalnızca `ask` sunuluyor.

Buna karşılık: rutin bir task'ı Opus yerine Sonnet'te çalıştırmak genellikle bağlamın
maliyetinden fazlasını kurtarıyor.

## Taahhüt etmeden önce bilmen gereken sınırlar

- **v1'de repo başına tek rol.** Birden çok rolü olan bir monorepo ya tek bir rol adı ve alt
  klasör glob'ları kullanır, ya da paketler o tek role göre yazılır.
- **Repo başına tek aktif task.** `wizrelay activate` ile ya da adında task kimliği olan bir
  dala geçerek değiştirilir.
- **Windows, `python3` erişilebilir olan Git Bash ile tier-1.** `python3` olmayan
  yalnızca-PowerShell bir ortamda hook'lar çalışmaz, ve `wizrelay doctor` bunu her şey
  yolundaymış gibi göstermek yerine hata olarak raporlar.
- **Jira, Linear ve Azure DevOps v1'de beta:** kimlik işleme ve URL üretimi test edilmiş,
  ama okuma ve yorum yazma senin erişimine bağlı.

## Sonraki

[3. Ön koşullar](03-prerequisites.md) — hiçbir şey kurulmadan önce kimin neye ihtiyacı
olduğu.

<!-- nav:bottom -->
---

| ← | ↑ | → |
|:---|:---:|---:|
| [← 1. Genel bakış](01-overview.md) | [İçindekiler](README.md) | [3. Ön koşullar →](03-prerequisites.md) |
<!-- /nav:bottom -->
