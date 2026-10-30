# Documentation · Dokümantasyon

Choose a language. Her iki dilde aynı bölümler, aynı dosya adlarıyla.

| | |
|---|---|
| 🇬🇧 **English** | **[→ Documentation index](en/README.md)** |
| 🇹🇷 **Türkçe** | **[→ Dokümantasyon dizini](tr/README.md)** |

Both sets have the same sections under the same file names, so switching language is one
link on every page: `docs/en/08-developer-workflow.md` ↔ `docs/tr/08-developer-workflow.md`.

## Contributor documentation

[CONTRIBUTING.md](../CONTRIBUTING.md) has the setup, the standards and the definition of
done.

## How this set is maintained

`scripts/docs_nav.py` holds the section list and writes every navigation block and both
indexes from it. After adding, renaming or reordering a section:

```bash
python3 scripts/docs_nav.py           # rewrite navigation and indexes
python3 scripts/docs_nav.py --check   # fail if anything is stale (CI)
```

`tests/unit/test_docs.py` asserts that the two languages have the same sections, that every
internal link resolves, and that every page carries current navigation.
