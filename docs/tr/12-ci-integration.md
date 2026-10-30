<!-- nav:top -->
[Dokümantasyon](README.md) › **12. CI entegrasyonu** &nbsp;·&nbsp; [English](../en/12-ci-integration.md)
<!-- /nav:top -->

# CI entegrasyonu

PR kapısı: developer'ın kendi oturumunda çalışmayan tek katman.

## Ne yapar

PR'daki değişiklikleri, o PR'ın task'ının kapsamıyla karşılaştırır.

**Hub'a erişim gerekmez:** repodaki `.wizrelay/tasks/` kopyasını kullanır. Task klasörünü
commit etmenin önemi bu
([8. Developer akışı](08-developer-workflow.md)). Task'ın kendisi dal adındaki kimlikten
bulunur.

Bu kılavuzdan tek bir şey kuracaksan, bunu kur. Geri kalan her şey koruduğu kişi tarafından
kapatılabilir.

## GitHub Actions

Gönderilen action kısa biçim:

```yaml
name: Scope
on:
  pull_request:
    branches: [main]

jobs:
  scope:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
      - uses: ChessWizard/wizrelay/integrations/github-action@v1.0.0
        with:
          version: v1.0.0
          on-missing-task: skip
```

Ya da ne yaptığını görmek istiyorsan elle:

```yaml
name: wizrelay-scope-gate
on:
  pull_request:
    branches: [main]

jobs:
  scope:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - name: wizrelay kurulumu
        run: pip install "git+https://github.com/ChessWizard/wizrelay@v1.0.0"
      - name: Kapsam denetimi
        run: >
          wizrelay audit
          --branch "${{ github.head_ref }}"
          --base "origin/${{ github.base_ref }}"
          --format md | tee -a "$GITHUB_STEP_SUMMARY"
```

İki ayrıntı:

- **`fetch-depth: 0` önemli.** Denetim `base...HEAD` farkını alıyor ve shallow bir
  checkout'un merge base'i yok. Olmadan denetim çalışma ağacına düşüyor, ki CI'da o boş.
- GitHub'ın varsayılan bash kabuğu `pipefail` ile çalışıyor, bu yüzden bir ihlal adımı
  kırmızı yapıyor ve rapor iş özetinde görünüyor.

Sonra dal koruma kurallarında `wizrelay-scope-gate / scope` kontrolünü zorunlu yap, yoksa
kapı tavsiye niteliğinde kalır.

## Gönderilen action'ın girdileri

| Girdi | Varsayılan | Ne yapar |
|---|---|---|
| `version` | `v1.0.0` | Kurulacak wizrelay sürümü. Sabitle |
| `base` | PR'ın taban dalı | Karşılaştırılacak ref |
| `task` | dal adından, sonra PR başlığından | Task referansı |
| `on-missing-task` | `skip` | `skip` task bulunmazsa geçer; `fail` başarısız olur |
| `python-version` | `3.12` | wizrelay'i çalıştıran yorumlayıcı |

Çıktılar: `violations` (sayı, temiz ya da atlandığında `0`) ve `skipped`.

## GitLab CI

```yaml
wizrelay-scope-gate:
  image: python:3.12
  rules:
    - if: $CI_PIPELINE_SOURCE == "merge_request_event"
  script:
    - pip install "git+https://github.com/ChessWizard/wizrelay@v1.0.0"
    - git fetch origin "$CI_MERGE_REQUEST_TARGET_BRANCH_NAME"
    - wizrelay audit --branch "$CI_MERGE_REQUEST_SOURCE_BRANCH_NAME" --base "origin/$CI_MERGE_REQUEST_TARGET_BRANCH_NAME"
```

## Azure Pipelines

```yaml
steps:
  - checkout: self
    fetchDepth: 0
  - script: |
      pip install "git+https://github.com/ChessWizard/wizrelay@v1.0.0"
      wizrelay audit --branch "$(System.PullRequest.SourceBranch)" --base "origin/$(System.PullRequest.TargetBranchName)"
    displayName: wizrelay kapsam kapısı
```

`refs/heads/` öneki CLI tarafından atılıyor, bu yüzden Azure'un tam ref'i olduğu gibi
çalışıyor.

Üçü için de kopyalanmaya hazır dosyalar
[`integrations/`](../../integrations/) altında.

## Davranış ayarları

| Durum | Varsayılan | Değiştirmek için |
|---|---|---|
| Dal adında task kimliği yok | "Atlandı" der ve geçer | `--require-task` ile başarısız olur |
| `--base` çözümlenemiyor | Yalnızca çalışma ağacına bakar ve bunu söyler | `fetch-depth: 0` ile geçmişi çek |
| Rapor biçimi | `md` | `--format json` |

**Varsayılan atlamayla başla.** Bir repoda pakete bağlı olmayan dallar olur — bağımlılık
güncellemesi, dokümantasyon, hotfix — ve onları başarısız saymak insanlara kontrolü
yoksaymayı öğretir, ki bu yakalamaya çalıştığın dallardan daha pahalıya gelir. Her dalın
bir task taşıması beklendiğinde `--require-task`'a geç.

## Task nasıl bulunur

1. Verilmişse `task` girdisi.
2. Dal adı: `feature/CU-86c1abcd-quota` → `CU-86c1abcd`. `refs/heads/` öneki atılır ve
   eşleşme büyük/küçük harfe duyarsız.
3. Hiçbiri eşleşmedi: ayara göre atla ya da başarısız ol.

## Rapor nasıl görünür

```markdown
## Kapsam denetimi — CU-86c1abcd (backend)
İhlal yok. Değişen 6 yolun tamamı açıklanabilir.

### Açıkça yasaklanmış
- `app/billing/invoice.py` — `app/billing/**`

### Bu rolün kapsamı dışında
- `README.md`

### Kapsam içinde (1)
- `app/quota/service.py`

### Yan ürün (derleme çıktıları ve wizrelay kurulumu)
- `poetry.lock`
```

Çıkış kodları: `0` temiz ya da atlandı, `1` ihlal. `--no-fail` her zaman 0 ile çıkar — yalnız
rapor için böyle çalıştırılır.

## Kapı kırmızı, makinende temizse

Alışılmış sebep: CI PR'daki her commit'e bakıyor, sen çalışma ağacına baktın. Yerelde
tekrarla:

```bash
wizrelay audit --base origin/main
```

## Headless doğrulama

Tam `/wizrelay:verify`'ı CI'da — `claude -p` ile — çalıştırıp sonucu PR yorumuna yazmak yol
haritasında, v1'de değil. Doğrulamanın deterministik yarısı, yani kapsam ve bütünlük
denetimi, kapının bugün çalıştırdığı şey.

## Sonraki

[13. Ekip ve kurum yönetimi](13-team-and-enterprise.md).

<!-- nav:bottom -->
---

| ← | ↑ | → |
|:---|:---:|---:|
| [← 11. Kapsam koruması](11-scope-protection.md) | [İçindekiler](README.md) | [13. Ekip ve kurum yönetimi →](13-team-and-enterprise.md) |
<!-- /nav:bottom -->
