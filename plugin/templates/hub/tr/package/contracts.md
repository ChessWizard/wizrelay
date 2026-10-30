# Sözleşmeler — {{TASK_ID}}

Paket birden çok rol kapsıyorsa zorunludur. Yazıldığı gibi uygulanır; değişmesi gereken
bir sözleşme soru olarak açılır, tek tarafta düzeltilmez.

Her sözleşmeye bir kimlik ver. Kabul kriterleri ve rol dosyaları ona `contracts.md#C-1`
olarak atıf yapar, böylece bir alan adı ya da hata kodu **yalnızca** burada tanımlanır.

## C-1 {{Sözleşme adı}}

- Üreten: {{rol}}
- Tüketen: {{rol}}

### Biçim

```json
{{ "alan": "tip" }}
```

### Kurallar

- {{durum kodları, hata biçimleri, idempotans, sıralama}}

### Sürümleme

{{Bu değiştiğinde mevcut bir istemciye ne olur.}}
