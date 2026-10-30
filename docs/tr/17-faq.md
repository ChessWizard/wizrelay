<!-- nav:top -->
[Dokümantasyon](README.md) › **17. Sık sorulan sorular** &nbsp;·&nbsp; [English](../en/17-faq.md)
<!-- /nav:top -->

# Sık sorulan sorular

İlk haftada çıkan sorular.

## Plugin claude.ai sohbetinde çalışır mı?

Hayır. **Claude Code** içindir: terminal, IDE eklentileri ve masaüstü uygulamasının Code
sekmesi. claude.ai ve Cowork'te kurulamaz da — plugin bir `bin/` dizini taşıyor, o yüzeyler
bunu reddediyor, ve zorlamayı yapan hook'lar orada yok.

## Her proje için ayrı hub gerekir mi?

Hayır. Hub **ekip** başına; her proje reposu aynı hub'a bağlanır. Tek bir task birkaç repoyu
kapsayabilir, ve böyle çalışmasının asıl sebebi bu.

## Developer analizi görebilir mi?

Evet — paketin tamamını. Yalnızca değiştiremez.

## Researcher'ın Claude kullanması zorunlu mu?

Hayır. Tüm akış CLI'dan yürür, ve bir paket `templates/package/` kopyalanarak tamamen elle
yazılabilir. `hub validate` elle yazılmış bir paketi birebir aynı kurallarla kontrol eder.

## Hub GitLab ya da Azure Repos'ta olabilir mi?

Evet. Hub düz bir git reposu.

## Tracker kullanmıyorsak?

`tracker: none` ayarla. Birinci sınıf bir seçenek, kısıtlı bir mod değil. Sorular
`questions.md`'de kalır, yanıtlar yeni bir paket sürümü olarak gelir ve soruyu bir insan
taşır. Dikkat edilecek tek şey, Researcher'a bir sorunun beklediğini hatırlatan bir
mekanizma olmaması; `ask` bir soru yazarken bunu söylüyor.

## `.wizrelay/tasks/` commit edilmeli mi?

Evet. Hem izlenebilirlik hem de CI kapısı için gerekli; kapı kapsamı bilmek için çekilmiş
paketi okuyor.

## İki developer aynı task'ı aynı rolde yapabilir mi?

Evet; ikisi aynı paketi çeker. İşi dallara bölmek ve `plan.md`'yi tek kişinin yönetmesi en
az sürtünme yaratan düzen.

## Developer kapsamı değiştirebilir mi?

Hayır. Kapsamı yalnızca Researcher, yeni bir sürümle değiştirir. Asıl nokta bu: kapsam bir
karardır ve onu değiştirmek, task'taki herkese ulaşan görünür bir eylemdir.

## İnternet olmadan çalışır mı?

Çekilmiş bir paketle çalışmaya devam eder. `pull` ve `sync` hub'a erişim gerektirir.

## Pakette dosya boyutu sınırı var mı?

Dosya başına 5 MB, paket başına toplam 20 MB. Paket analiz, varlık paketi değil.

## Analizi neden sadece `CLAUDE.md`'ye koymuyoruz?

Koyabilirsin, ve işe yarar. Ama `CLAUDE.md` bir talimattır ve talimat izlemek olasılıksaldır:
uzun bir oturum sapar, bir sıkıştırma onu düşürür, makul görünen bir iyileştirme yine de
olur. Bir deny kuralı ve bir `PreToolUse` hook'u olasılıksal değil.

Diğer yarısı sürümleme. `CLAUDE.md`'nin "bu analiz v2 ve sende v1 var" diyecek bir yolu yok,
ve soru döngüsünün yürüdüğü mekanizma bu.

## Oturumu yavaşlatır mı?

Bütçe ağsız hook başına p95 300 ms altı, ve testler bunu zorluyor. Mesaj başına çapa 250
karakterle, oturum başlangıcı bağlamı 8000 ile sınırlı, hedef 3000.

Ağa dokunabilen tek işlem oturum başlangıcı; bir TTL içinde, 4 saniye zaman aşımıyla ve
sessizce başarısız olarak.

## Plugin token harcar mı?

Biraz, ve ölçülüyor. Modelin gördüğü skill ve ajan açıklamaları toplam 1500 karakter ya da
altı — yan etkili skill'ler `disable-model-invocation: true` taşıyor, yani model onların
açıklamalarını hiç görmüyor. Oturum başlangıcı bağlamı 3000 karakteri hedefliyor.

Defterin diğer tarafı yönlendirme: rutin bir task'ı Opus yerine Sonnet'te çalıştırmak
genellikle bağlamın maliyetinden fazlasını kurtarıyor.

## Neden modelin kendi başına çağırabildiği tek skill `ask`?

Çünkü developer'ın sahip olduğu bir dosyanın ötesinde yan etkisi olmayan tek skill o. Geri
kalan her şey yazıyor, yayınlıyor ya da gönderiyor, ve bunlar bir insan istediği için
olmalı.

`ask`'in açıklaması kasten istekli: task hakkında bir şey varsaymak üzere olduğun an, onu
kullanma anı.

## `ask` bana yanlış yanıt verirse?

Tahmin etmek yerine reddetmek üzere kurulmuş: paket soruyu yanıtlamıyorsa bunu söyler ve
sorma teklifinde bulunur. Bu davranışın kendi eval vakası var, ve gereksinim uydurulmuş
yanıt oranının sıfır olması.

Yanıt veriyorsa dosyayı gösterir. Kaynağı kontrol et — var olma sebebi bu.

## Claude Code olmadan kullanabilir miyim?

Kısmen. Her deterministik işlemin bir CLI karşılığı var — `wizrelay pull`, `audit`,
`hub validate`, `hub publish-prep` — yani CI kapısı ve script'lenebilir yarısı terminalden
çalışıyor.

Claude'a ihtiyaç duyan kısım muhakeme: tracker task'ından paket çıkarmak, planlamak,
doğrulamak, bir soruyu paketten yanıtlamak. Skill'ler birer prompt, ve bir prompt model
ister.

## Biri yine de bir researcher dosyasını düzenlemiş. Şimdi ne olacak?

`sync` onu hub'dan geri yükler ve bunu raporlar. O ana kadar oturum başlangıcı ve `audit`
bütünlük sorununu raporluyor, çünkü kilit dosya başına bir hash tutuyor.

Değişiklik gerekliyse bu Researcher'a sorulacak bir soru.

## `pull` neden hiç kod yazmıyor?

Çünkü analizi hâlâ okurken uygulamaya başlayan bir oturum, bu projenin var olma sebebi olan
sapmanın kendisi. `pull` brifing verir ve durur. Kapsam görünürken plan modunda planlamak,
uygulamaktan farklı bir faaliyet.

## `enforcement: off` neyi bırakır?

Researcher dosyaları salt okunur kalır; kapsam zorlanmaz. Kapsamı gerçekten önceden
çizilemeyen bir task için, ve hiç paket olmamasından çok daha iyi: analiz, kriterler ve
kararlar hepsi yine çalışıyor.

## Korumanın gerçekten açık olduğunu nasıl bilirim?

`/wizrelay:doctor` yapılandırmayı kontrol eder. `/wizrelay:status` **bu oturumu** kontrol
eder: çıktısı `WIZRELAY_NO_GUARD` ile başlıyorsa, yapılandırma doğru olmasına rağmen
hook'lar burada çalışmadı. İki farklı soru, ve ikincisi insanları ısıran.

## Neden Python, ve neden yalnızca standart kütüphane?

Çünkü plugin, Claude Code'un bir cache'e kopyaladığı bir dizin ve kimse onun için
`pip install` çalıştırmıyor. Tek bir üçüncü parti import, o paketi olmayan herkesin
plugin'ini bozardı. Python'un kendisi orada çünkü `python3` Claude Code'un çalıştığı neredeyse
her yerde zaten var.

## Bunların herhangi biri bir yere gönderiliyor mu?

Hayır. Telemetri yok, sunucu yok, SaaS bileşeni yok. Tek ağ erişimi kendi hub'ına karşı
`git fetch`, ve kendi yetkilendirdiğin MCP sunucuları üzerinden tracker erişimi.

## Sonraki

[Ek A — Komut referansı](appendix-a-commands.md).

<!-- nav:bottom -->
---

| ← | ↑ | → |
|:---|:---:|---:|
| [← 16. Sorun giderme](16-troubleshooting.md) | [İçindekiler](README.md) | [Ek A — Komut referansı →](appendix-a-commands.md) |
<!-- /nav:bottom -->
