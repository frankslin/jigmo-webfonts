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

### 部署架構

單一 Cloudflare Pages 專案。Cloudflare Pages 限制為 **25 MB per file**（不是總大小），所有分片個別最大 ~128 KB，全部字型（~36 MB）可放入同一個專案。

---

## 授權 / License

| 範圍 | 授權 |
|------|------|
| 本 repo 原始碼與網頁（build.py、split.py、index.html 等） | [CC0 1.0 公共領域](https://creativecommons.org/publicdomain/zero/1.0/) |
| Jigmo 字型（神地康一 / Kamichi Koichi） | CC0 1.0 |
| Source Serif 4（Adobe） | [OFL-1.1](https://openfontlicense.org) |

第三方字型完整授權條款見 [THIRD_PARTY_LICENSES.md](./THIRD_PARTY_LICENSES.md)。
