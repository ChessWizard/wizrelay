<!-- nav:top -->
[Dokümantasyon](README.md) › **Ek D — Kontrol listeleri** &nbsp;·&nbsp; [English](../en/appendix-d-checklists.md)
<!-- /nav:top -->

# Ek D — Kontrol listeleri

Bunları bir issue'ya ya da wiki sayfasına kopyala. Her biri, adımlarının atlanması kolay ve
atlanması pahalı olduğu için var.

## Ekip kurulumu, bir kez

- [ ] `wizrelay` plugin'i kurulu ([4. bölüm](04-install-plugin.md))
- [ ] Hub reposu oluşturuldu, `/wizrelay:hub-init` çalıştı ve push edildi ([5. bölüm](05-set-up-hub.md))
- [ ] Tracker MCP bağlandı (`/mcp`)
- [ ] Hub'da `CODEOWNERS` ve dal koruması ayarlandı — **güven sınırı bu**
- [ ] Her proje reposunda `/wizrelay:init` çalıştı, `profile.json` gözden geçirildi ve commit edildi ([6. bölüm](06-connect-repository.md))
- [ ] CI kapısı eklendi, başlangıçta `on-missing-task: skip` ile ([12. bölüm](12-ci-integration.md))
- [ ] Geri kalanına yaymadan önce bir gerçek task tüm döngüden geçti

Son madde, insanların atladığı. İlk task, `roles` sözlüğünün ve `critical_paths`'in doğru
olup olmadığını öğrendiğin yer, ve bunu bir task'ta öğrenmek altı task'ta öğrenmekten ucuz.

## Yeni ekip üyesi

- [ ] Claude Code ≥ v2.1.295, `PATH`'te `python3` ile Python ≥ 3.9, git
- [ ] Hub reposuna okuma erişimi
- [ ] Plugin kurulu ve `/wizrelay:doctor` temiz
- [ ] Tracker'a giriş yapıldı (`/mcp`)
- [ ] [1. Genel bakış](01-overview.md), [8. Developer akışı](08-developer-workflow.md) ve [11. Kapsam koruması](11-scope-protection.md) okundu

## Researcher, yayından önce

- [ ] Her tracker gereksinimi en az bir kabul kriterine bağlı
- [ ] Her kriterin rolü, Given/When/Then'i ve bir komut adlandıran doğrulama satırı var
- [ ] Roller arası her arayüz `contracts.md`'de, kimliğiyle tanımlı
- [ ] Açık soru kalmadı; kararlar `decisions.md`'de
- [ ] Mevcut duruma dair her iddia bir yol gösteriyor
- [ ] Kapsam dar, testleri ve migration'ları içeriyor, kritik alanlar `deny`'da
- [ ] Sinyaller yüksek sesle söyleyebileceğin bir gerekçeyle seçildi
- [ ] `/wizrelay:hub-validate` engelleyici göstermiyor

## Developer, her gün

- [ ] Oturum başlangıcındaki uyarıları oku — yeni sürüm? bütünlük sorunu?
- [ ] Önerilen model ve effort ile çalış
- [ ] Planda olmayan bir şey yapma; emin değilsen `/wizrelay:ask`
- [ ] Bitti demeden `/wizrelay:verify`
- [ ] Commit mesajları kriter kimlikleri taşıyor; `.wizrelay/tasks/` commit edildi

## Developer, engellendiğinde

- [ ] Dosya Researcher'ın mı? → değişiklik talebi için `/wizrelay:ask`
- [ ] Değişiklik planda var mı? Yoksa planı tekrar oku
- [ ] Gerçekten gerekiyorsa: gerekçeyi `questions.md`'ye yaz, `/wizrelay:ask`, yeni sürümü
      bekle, `/wizrelay:sync`
- [ ] Kapsamı yerel olarak **genişletme**, ve engeli bir shell komutuyla dolaşma — CI kapısı
      aynı kapsamı kontrol ediyor

## Researcher, bir soruyu yanıtlarken

- [ ] Dört türden hangisi? ([9. Soru döngüsü](09-question-loop.md))
- [ ] Karar daha fazla yoruma gerek bırakmadan uygulanabilir
- [ ] `Etki` değişen her kriteri, sözleşmeyi ve kapsam girişini adlandırıyor
- [ ] Kararın çeliştiği her şey aynı sürümde değiştirildi
- [ ] Yayınlandı, ve `[WIZRELAY-A]` yanıtı karara işaret ediyor

## Korumaya güvenmeden önce

- [ ] Bir developer'ın makinesinde `/wizrelay:doctor` temiz
- [ ] Bağlı bir repoda `/wizrelay:status` `WIZRELAY_NO_GUARD` **göstermiyor**
- [ ] Bir researcher dosyasına yapılan düzenleme reddediliyor
- [ ] Kapsam dışı bir düzenleme reddediliyor
- [ ] Bilerek kapsam dışı bir PR, CI kontrolünü kırmızı yapıyor
- [ ] Bilerek kurulmuş ikinci bir `wizrelay` adlı plugin, `doctor`'a hata raporlatıyor

İşaretlediğin her satırın yanına Claude Code sürümünü ve sonucu yaz: sürümsüz bir kontrol
kanıt değildir, çünkü kanıtladığı davranış bir sonraki sürümde değişebilir.

<!-- nav:bottom -->
---

| ← | ↑ | → |
|:---|:---:|---:|
| [← Ek C — Tracker yorum etiketleri](appendix-c-tracker-tags.md) | [İçindekiler](README.md) | [Ek E — Sözlük →](appendix-e-glossary.md) |
<!-- /nav:bottom -->
