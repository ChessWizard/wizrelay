# wizrelay protokolü

Bu reponun `CLAUDE.md` dosyasına içe aktarılır. Etkin bir task paketi varken geçerlidir.

## 1. Sahiplik

Researcher dosyaları burada salt okunurdur: `task.json`, `research.md`, `scope.md`,
`acceptance.md`, `decisions.md`, `contracts.md`, `roles/*.md` ve `.lock.json`.
Developer dosyaları size aittir: `plan.md`, `questions.md`, `verification.md`, `notes/`.
Bir researcher dosyasının değişmesi gerekiyorsa `/wizrelay:ask` ile sorulur; yanıt yeni
bir paket sürümü olarak gelir.

## 2. Kaynaklar çeliştiğinde öncelik

`decisions.md` (en yeni karar) > `task.json` + `scope.md` (kapsam) >
`contracts.md` (arayüzler) > `acceptance.md` (davranış) > `roles/<rol>.md` >
`research.md` (gerekçe).

## 3. Kapsam

Yalnızca bu rolün `allow` kalıplarının kapsadığı yerler değiştirilir. Korumanın
engellediği bir değişiklik başka yoldan denenmez — ne shell komutuyla ne script ile.
Kapsam yanlışsa bu, etrafından dolaşılacak bir engel değil, Researcher'a sorulacak bir
sorudur.

## 4. Belirsizlik

Önce `/wizrelay:ask` çalıştırılır; yanıtı paketten verir ve kullandığı dosyayı gösterir.
Pakette yanıt yoksa soru Researcher'a gider. Yanıta bağlı olmayan işlere devam edilir.
Varsayım zorunluysa varsayım olduğu etiketlenir ve kullanıcıya söylenir.

## 5. Kabul kriterleri

Her değişiklik bir kabul kriterine bağlıdır. Plan adımları ve commit mesajları kriterin
kimliğini taşır.

## 6. Sözleşmeler

`contracts.md` yazıldığı gibi uygulanır. Değişmesi gereken bir sözleşme soru olarak
açılır, yerel olarak düzeltilmez.

## 7. Kapsam dışı fikirler

Uygulanmaz. Researcher'a ulaşsın diye `questions.md` içinde "Öneri" başlığı altına
kaydedilir.

## 8. Doğrulama

İş bitti denmeden önce `/wizrelay:verify` çalıştırılır. Testler ve doğrulama
developer'ın sorumluluğundadır, Researcher'ın değil.

## 9. Güncellemeler

Oturum yeni bir research sürümü olduğunu söylediğinde, devam etmeden önce
`/wizrelay:sync` çalıştırılır.

## 10. Komutlar

`/wizrelay:pull` `/wizrelay:plan` `/wizrelay:ask` `/wizrelay:verify` `/wizrelay:sync`
`/wizrelay:status` `/wizrelay:doctor`
