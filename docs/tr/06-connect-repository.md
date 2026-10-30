<!-- nav:top -->
[Dokümantasyon](README.md) › **6. Bir repoyu bağlamak** &nbsp;·&nbsp; [English](../en/06-connect-repository.md)
<!-- /nav:top -->

# Bir repoyu bağlamak

Bir proje reposunu hub'a bağlamak ve profilini doğru yapmak — çünkü yönlendirme o profili
okuyor.

## 1. Rolü seç

Rol, bu reponun bir task'ın hangi kısmını uyguladığını söyler ve hub'ın `roles` listesindeki
adlardan biri olmalıdır. Örnekte `api-service` → `backend`, `web-app` →
`frontend`.

v1'de bir repo **tek** role sahip. Birden çok rolü olan bir monorepo için iki seçenek var:
repoya tek bir rol adı ver (örneğin `fullstack`) ve kapsamı alt klasör glob'larıyla ifade et,
ya da paketleri o tek role göre yaz. Çoklu rol desteği yol haritasında.

## 2. `/wizrelay:init` çalıştır

Claude Code repo kökünde açıkken:

```
/wizrelay:init backend git@github.com:acme/research-hub.git
```

Sırasıyla şunlar olur:

1. Hub'a bağlanılır ve ekip varsayılanları okunur — dil, tracker, `base_ref`.
2. `.wizrelay/` oluşturulur.
3. `CLAUDE.md` dosyasının sonuna `@.wizrelay/PROTOCOL.md` eklenir. Mevcut içerik korunur;
   dosya yoksa oluşturulur.
4. Researcher dosyalarını koruyan izin kuralları `.claude/settings.json`'a eklenir. Mevcut
   ayarların korunur.
5. Kişisel dosyalar `.gitignore`'a eklenir: `.wizrelay/.active-task`,
   `.wizrelay/config.local.json`.
6. Tracker için proje `.mcp.json` girişi önerilir; onaylarsan yazılır.
7. Claude repoyu okur, `profile.json` taslağını çıkarır ve onayına sunar.

Sonuç:

```
api-service/
├── CLAUDE.md                 ← sonuna @.wizrelay/PROTOCOL.md eklendi
├── .claude/settings.json     ← deny kuralları eklendi
├── .gitignore                ← iki satır eklendi
└── .wizrelay/
    ├── config.json           ← hub, rol, tracker, dil (commit edilir)
    ├── profile.json          ← repo profili (commit edilir)
    ├── PROTOCOL.md           ← Claude'un bu repoda task'larla çalışma kuralları
    └── tasks/                ← çekilen paketler burada olacak
```

Komut **idempotent**: ikinci kez çalıştırırsan "değişiklik yok" der ve hiçbir dosyaya
dokunmaz.

### `.claude/settings.json`'a eklenen kurallar

```json
{
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

Bu kurallar Claude'un dosya araçlarını **ve** Claude Code'un tanıdığı shell biçimlerini
kapsar — `sed`, `tee`, `>` yönlendirmesi. Başka bir ayar seviyesindeki bir "izin ver"
kuralı bunları açamaz.

Böyle kuralları kendin yazarsan yanlış yapması kolay iki ayrıntı:

- **Her kural `Edit(...)`.** Bir `Write(path)` kuralı hiçbir şeyle eşleşmez; Claude Code
  dosya izinlerini yalnızca `Edit` ve `Read` kurallarına karşı kontrol eder.
- **Tek baştaki eğik çizgi ayar kaynağına demirler**, ki proje ayarları için bu repo
  köküdür. Dosya sistemi kökünden mutlak bir yol değil — o `//` olurdu.

## 3. `profile.json` — repoyu tanıtmak

Claude taslağı çıkarır, sen doğrularsın. Bu dosya iki şeyi etkiler: `/wizrelay:verify`'ın
hangi komutları çalıştıracağını ve hangi modelin önerileceğini.

Python / FastAPI backend:

```json
{
  "schema_version": 1,
  "stack": "Python 3.12 / FastAPI / PostgreSQL / Azure Service Bus",
  "commands": {
    "test": "pytest -q",
    "test_targeted": "pytest -q {path}",
    "lint": "ruff check .",
    "typecheck": "mypy app"
  },
  "codebase_size": "medium",
  "test_maturity": "medium",
  "critical_paths": ["app/auth/**", "app/billing/**", "app/tenancy/**", "alembic/versions/**"],
  "legacy_paths": ["app/legacy/**"],
  "incidental_allow": ["openapi.json"]
}
```

React frontend:

```json
{
  "schema_version": 1,
  "stack": "React 19 / TypeScript / Vite",
  "commands": {
    "test": "npm test -- --run",
    "test_targeted": "npm test -- --run {path}",
    "lint": "npm run lint",
    "typecheck": "npx tsc --noEmit"
  },
  "codebase_size": "medium",
  "test_maturity": "low",
  "critical_paths": ["src/features/billing/**", "src/lib/auth/**"],
  "legacy_paths": [],
  "incidental_allow": ["src/api/generated/**"]
}
```

.NET, yalnızca komutlar:

```json
{ "commands": { "test": "dotnet test", "test_targeted": "dotnet test --filter {path}", "lint": "dotnet format --verify-no-changes", "typecheck": "" } }
```

| Alan | Ne yazılır | Neyi etkiler |
|---|---|---|
| `commands.test` | Tüm testleri çalıştıran komut | `/wizrelay:verify` |
| `commands.test_targeted` | Tek dosya ya da klasörü test eden komut, `{path}` yer tutucusuyla | `/wizrelay:verify`'da kriter bazlı kanıt |
| `commands.lint`, `commands.typecheck` | Boş bırakılabilir | `/wizrelay:verify` |
| `codebase_size` | `small` / `medium` / `large` | `large` → yönlendirme skoruna +1 |
| `test_maturity` | `low` / `medium` / `high` | `low` → +1 |
| `critical_paths` | Hata maliyeti yüksek alanlar: kimlik doğrulama, ödeme, tenant izolasyonu, migration | Task kapsamı bunlara dokunuyorsa +1 |
| `legacy_paths` | Eski, testsiz ya da başka sebeplerle riskli kod | Task kapsamı bunlara dokunuyorsa +1 |
| `incidental_allow` | Task'tan bağımsız olarak değişmesi doğal dosyalar: üretilen client, snapshot | Kapsam kontrolünde serbest. Lockfile'lar zaten serbest |

**Komutları repodan al, hafızadan değil.** `Makefile`, `package.json` script'leri,
`pyproject.toml`, bir `justfile` ya da CI workflow'undan gelmeli. Gerçekte çalışmayan bir
`test_targeted` komutu her doğrulama raporunu işe yaramaz kılar.

Ve `test_maturity` konusunda dürüst ol. İyimser ayarlanması en muhtemel alan bu, ve riskli
bir task'ın güçlü bir model alıp almayacağına karar veren iki alandan biri.

## 4. `config.json` ve kişisel ayarlar

```json
{
  "schema_version": 1,
  "hub": { "repo": "git@github.com:acme/research-hub.git", "branch": "main" },
  "role": "backend",
  "tracker": { "type": "clickup", "id_prefix": "CU-" },
  "language": "tr",
  "base_ref": "origin/main",
  "prompt_anchor": true,
  "session_title": true,
  "fetch_ttl_minutes": 10,
  "researcher_mention": ""
}
```

| Alan | Açıklama |
|---|---|
| `hub` | Bağlı hub ve yayın dalı |
| `role` | Bu reponun rolü |
| `prompt_anchor` | Her mesaja tek satırlık task hatırlatıcısı ekler (kapatılabilir) |
| `session_title` | Oturum adını task'a göre koyar |
| `fetch_ttl_minutes` | Oturum açılışında hub'ın kaç dakikada bir yoklanacağı (`0` = her açılışta, ve gerçekten her açılışta) |
| `researcher_mention` | Soru yorumlarında etiketlenecek tracker kullanıcı adı |

Kişisel ayarlar `.wizrelay/config.local.json`'a yazılır; gitignore'dadır. Alışılmış tek
kullanımı: Researcher'ın hub'ı yerel bir çalışma kopyasından okuması.

```json
{ "hub": { "path": "~/code/research-hub" } }
```

`hub.path` ayarlıyken **hiçbir şey önbelleğe alınmaz ve çalışma kopyası asla fetch edilmez
ya da reset'lenmez**, yani hub'ı bir editörde açık tutmak güvenli.

## 5. Commit

```bash
git add CLAUDE.md .claude/settings.json .gitignore .wizrelay/
git commit -m "chore: wizrelay bağlantısı (rol: backend)"
git push
```

## 6. Ekip arkadaşı katılırken

1. Repoyu çeker.
2. Claude Code'u repoda açar ve **çalışma alanı güven diyaloğunu onaylar**. Proje ayarları
   ve plugin önerisi ancak bundan sonra devreye girer.
3. Plugin önerilirse kabul eder. Önerilmezse
   [4. Plugin'i kurmak](04-install-plugin.md)'taki iki komutu çalıştırır.
4. `/wizrelay:doctor` ile kontrol eder.
5. Soru ya da doğrulama raporu gönderecekse `/mcp` ile tracker'a giriş yapar.

## Sonraki

[7. Researcher: hazırlamak ve yayınlamak](07-researcher-workflow.md), ya da birisi zaten
yayınladıysa [8. Developer: task'ı uygulamak](08-developer-workflow.md).

<!-- nav:bottom -->
---

| ← | ↑ | → |
|:---|:---:|---:|
| [← 5. Ekip hub'ını kurmak](05-set-up-hub.md) | [İçindekiler](README.md) | [7. Researcher: hazırlamak ve yayınlamak →](07-researcher-workflow.md) |
<!-- /nav:bottom -->
