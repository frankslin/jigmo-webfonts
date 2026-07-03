# Jigmo Webfonts

基於 [Jigmo](https://kamichikoichi.github.io/jigmo/)（CC0）的 CJK 生僻字 woff2 分片字型服務，涵蓋 Unicode Extension A–J（U+3400–U+323AF）。

Chunked woff2 webfonts for CJK rare ideograph display — covering Unicode Extensions A through J (U+3400–U+323AF). Based on [Jigmo](https://kamichikoichi.github.io/jigmo/) (CC0).

**Demo：** https://jigmo.digitalhumanities.dev

---

## 快速上手 / Quick Start

在 `<head>` 加入一個樣式表：

```html
<link rel="stylesheet" href="https://jigmo.digitalhumanities.dev/jigmo.css">
```

將 `Jigmo` 放在 font stack 末段作為備援——瀏覽器只下載頁面實際出現字符所在的分片：

```css
body {
  font-family:
    'Source Serif 4',        /* 拉丁文 / Latin — pairs with Source Han Serif */
    'Source Han Serif TC',   /* 常用漢字 / common CJK */
    'Noto Serif CJK TC',     /* 常用漢字備援 / common CJK fallback */
    'Jigmo',                 /* 生僻字 / rare ideographs (Ext A–J) */
    serif;
}
```

就這樣。沒有生僻字的頁面下載零位元組；含一個 Ext-B 字符的頁面只下載一個分片（約 10–40 KB）。

---

## 原理 / How It Works

`jigmo.css` 包含數百條 `@font-face` 規則，每條對應一個 256 碼位的分片：

```css
@font-face {
  font-family: 'Jigmo';
  font-display: swap;
  src: url('fonts/jigmo-02a600.woff2') format('woff2');
  unicode-range: U+2A600-U+2A6FF;
}
```

瀏覽器讀取 `unicode-range` 描述符，**只在頁面包含該範圍字符時才下載對應分片**。此技術與 Google 大規模提供 Noto CJK 時所用的方式相同。

---

## 覆蓋範圍 / Coverage

| 字符區塊 | Unicode 範圍 | 來源字型 |
|---------|-------------|---------|
| CJK URO + 相容表意文字 | U+3000–U+9FFF, U+F900–U+FAFF | Jigmo.ttf |
| CJK Extension A | U+3400–U+4DBF | Jigmo.ttf |
| CJK Extension B | U+20000–U+2A6DF | Jigmo2.ttf |
| CJK Extension C–F, I | U+2A700–U+2EE5F | Jigmo2.ttf |
| CJK Extension G–J | U+30000–U+323AF | Jigmo3.ttf |
| **合計** | **約 145,975 字符（Unicode 17.0）** | |

---

## 自架與建置 / Self-Hosting / Build

```bash
# 1. 安裝 Python 依賴
pip install -r requirements.txt

# 2. 建置：下載所有字型、切片為 woff2、生成 jigmo.css
python build.py

# 3. 部署
python split.py --clean
wrangler pages deploy dist/jigmo --project-name jigmo --branch main
```

常用選項：

```bash
python build.py --no-dl    # 跳過下載（src/*.ttf 已存在）
python build.py --no-ss4   # 跳過 Source Serif 4 下載
python build.py --force    # 強制重建所有分片
python build.py --jobs 8   # 指定平行 worker 數（預設：CPU 核心數）
```

升級 Jigmo 新版本：修改 `build.py` 頂部的 `JIGMO_URL`，刪除 `src/` 與 `fonts/` 後重新執行。

### Jigmo SC / TC 來源優先變體

GlyphWiki 同一 Unicode 字常有不同來源字形，例如 `u21a05-g`、`u21a05-t`、`u21a05-j`。本 repo 可從最新 GlyphWiki dump 生成兩套完整替換版字型：

- `Jigmo SC`：以原始 Jigmo 為底，能替換時採用 `G -> T -> original Jigmo`
- `Jigmo TC`：以原始 Jigmo 為底，能替換時採用 `T -> G -> original Jigmo`

這兩套字型保留原始 Jigmo 的完整覆蓋；只在 GlyphWiki 有對應 G/T 來源字形時替換局部 glyph。

```bash
# 1. 先確保 src/Jigmo.ttf / Jigmo2.ttf / Jigmo3.ttf 存在
python build.py --no-ss4 --no-sht

# 2. 從 GlyphWiki dump 建立替換 mapping；dump 內是 KAGE data，不是 SVG
python build_jigmo_variants.py --prepare-only

# 3. 從 KAGE data 本地生成缺少的 SVG outlines，然後生成 src/JigmoSC*.ttf / src/JigmoTC*.ttf
#    第一次會把 GPL-3.0 kage-engine 下載到 ignored 的 src/glyphwiki/kage-engine/
python build_jigmo_variants.py --render-kage-svg --download-kage-engine

#    若需要對既有 SVG cache 做 byte-level cross-check，可加：
python build_jigmo_variants.py --render-kage-svg --kage-cross-check-limit 500

#    備用：若要從 glyphwiki.org/glyph/*.svg 補下載缺口，需明確 opt-in
#    下載只會補缺的 SVG；中斷後重跑同一命令即可續補
python build_jigmo_variants.py --allow-remote-svg --jobs 8

# 4. 切成 woff2，CSS family 會是 'Jigmo SC' 或 'Jigmo TC'
python build.py --variant sc --no-dl
python build.py --variant tc --no-dl
```

除錯/預覽可先跑小樣本：

```bash
python build_jigmo_variants.py --limit 1 --render-kage-svg --download-kage-engine
python build_jigmo_variants.py --limit 1 --allow-remote-svg
python build_jigmo_variants.py --prepare-only
```

生成過程會在 `src/glyphwiki/variant-glyph-map.tsv` 記錄每個 Unicode codepoint 實際替換用的 GlyphWiki glyph name；未列入的 codepoint 保留原始 Jigmo glyph。
本地 KAGE 生成會讀取 dump 的 KAGE data 並寫入 `src/glyphwiki/glyph/` SVG cache；kage-engine 只作為 build-time tool 使用，不 vendoring 到本 repo。注意 KAGE data 會引用 `foo@版本` 形式的歷史部件，因此 renderer cache 會以 `dump_newest_only.txt` 為主，並從 `dump_all_versions.txt` 補齊被引用到的 versioned components。

也可以生成 G/T/J 來源覆蓋查詢表：

```bash
python glyphwiki_sources_csv.py --only-source-coded
```

預設輸出 `src/glyphwiki/glyphwiki-sources-g-t-j.csv`，欄位包含 `has_g`、`has_t`、`has_j`、`missing_sources`、各來源 glyph name，以及 KAGE data 的短 SHA1（用於快速判斷不同來源是否實際同形）。

### 部署架構

單一 Cloudflare Pages 專案。Cloudflare Pages 限制為 **25 MB per file**（不是總大小），所有分片個別最大 ~128 KB，全部字型（~36 MB）可放入同一個專案。

---

## 授權 / License

| 範圍 | 授權 |
|------|------|
| 本 repo 原始碼與網頁（build.py、split.py、index.html 等） | MIT |
| Jigmo 字型（神地康一 / Kamichi Koichi） | CC0 1.0 |
| Jigmo SC/TC 生成用 GlyphWiki glyph data | GlyphWiki data license（自由使用、修改、再散布；無保證） |
| Source Serif 4（Adobe） | [OFL-1.1](https://openfontlicense.org) |

第三方字型完整授權條款見 [THIRD_PARTY_LICENSES.md](./THIRD_PARTY_LICENSES.md)。
