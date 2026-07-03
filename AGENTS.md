# AGENTS 指南 — jigmo-webfonts

本文件記錄此專案的架構決策、已踩過的坑，以及 AI 代理繼續維護時需知道的背景。

## 專案目的

為 CBDB（中國歷代人物傳記資料庫）等需要顯示罕見 CJK 字元（尤其是 Extension B 以上，如 𡨅、𪘏）的網站提供自托管 webfont 服務。使用 **Jigmo**（CC0 1.0）字型，分塊輸出 woff2，讓瀏覽器透過 CSS `unicode-range` 只下載頁面實際用到的區塊。

## 部署架構

兩個 Cloudflare Pages 專案，各自低於 25 MB 限制：

| 專案 | 域名 | 內容 | 大小 |
|------|------|------|------|
| `jigmo` | `jigmo.digitalhumanities.dev` | Plane 2–3（Extension B–J，≥U+20000）+ Source Serif 4 + 主頁 | ~21 MB |
| `jigmo2` | `jigmo2.digitalhumanities.dev` | Plane 0–1（URO + Extension A，<U+20000） | ~7 MB |

`jigmo` 是主站（有 `index.html` landing page）；`jigmo2` 只有字型檔與一個自動跳轉到 `jigmo` 的 stub `index.html`。

CSS 從 `jigmo.digitalhumanities.dev/jigmo.css` 統一引用，包含兩個部署的絕對 URL，以及 Source Serif 4 的相對 URL。

## 工作流程

```bash
# 第一次或字型版本升級時
python build.py                  # 下載 Jigmo zip、生成 woff2 chunks、下載 SS4、輸出 jigmo.css

# 只重建 CSS（字型檔已存在）
python build.py --no-dl

# 跳過 SS4 下載（純 Jigmo 用途）
python build.py --no-dl --no-ss4

# 分割並準備部署目錄
python split.py --clean

# 部署（需先 wrangler login）
wrangler pages deploy dist/jigmo  --project-name jigmo  --branch main
wrangler pages deploy dist/jigmo2 --project-name jigmo2 --branch main
```

## 分塊策略

- `CHUNK_SIZE = 0x100`（256 codepoints），與 Google Noto CJK 相同。
- 塊名格式：`jigmo-{chunk_start:06x}.woff2`，例如 `jigmo-021b00.woff2`。
- 三個來源字型（Jigmo.ttf / Jigmo2.ttf / Jigmo3.ttf）各自掃描 cmap，以 **先到先得** 去重（`seen: set[str]`），避免 Jigmo.ttf 與 Jigmo2.ttf 在 U+20000+ 重疊時產生重複 CSS 規則。

## Source Serif 4 自托管

- `build.py` 的 `download_source_serif_4()` 用桌面版 Chrome UA 呼叫 Google Fonts CSS API，取回 woff2 URL 後逐一下載到 `fonts/ss4-01.woff2` … `ss4-12.woff2`，並將 CSS 中的 URL 改為相對路徑 `fonts/ss4-XX.woff2`。
- SS4 woff2 只部署到 `dist/jigmo/`（主站），`dist/jigmo2/` 不需要。
- `split.py` 的 URL 改寫邏輯會把 `ss4-` 開頭的 URL 保持相對路徑（不加主站前綴）。
- `index.html` **不應** 有 Google Fonts `<link>` 標籤；SS4 已透過 `jigmo.css` 自托管載入。

## 已知坑

### Cloudflare Pages 25 MB 限制
直接部署整個 `fonts/` 會超過限制（原始約 28 MB）。解法是 `split.py` 拆成兩個部署。

### jigmo2 顯示為 Preview 而非 Production
無 git 連線的 Pages 專案，即使加 `--branch main`，wrangler 直接上傳仍被視為 Preview。  
修正方式：Dashboard → 專案設定 → 將 production branch 改為 `main`，再重新部署。

### FFTM 表警告
Jigmo 字型由 FontForge 製作，包含私有 `FFTM` 表，fontTools 不認識時會大量輸出警告。  
`build.py` 已加 `logging.getLogger("fontTools").setLevel(logging.ERROR)` 壓制。

### Jigmo.ttf 與 Jigmo2.ttf 的 U+20000+ 重疊
兩個字型的 cmap 在 U+20000+ 區段有部分重疊，`build_font()` 會各自輸出同名塊。  
`build_all()` 用 `seen: set[str]` 確保同一塊只保留第一個（Jigmo.ttf 優先）。

## 授權

| 範圍 | 授權 |
|------|------|
| 本專案原始碼與網頁（build.py、split.py、index.html 等） | MIT © 2026 Frank Lin |
| Jigmo 字型（神地康一） | CC0 1.0（公共領域） |
| Source Serif 4 字型（Adobe） | OFL-1.1 |

詳見 `LICENSE`（MIT）與 `THIRD_PARTY_LICENSES.md`（CC0 / OFL 全文）。

## 在 CBDB 網站引入

```html
<link rel="stylesheet" href="https://jigmo.digitalhumanities.dev/jigmo.css">
```

建議 CSS `font-family` 排列順序（Source Han / Noto 先覆蓋常用字，Jigmo 補 Ext-B+）：

```css
font-family: 'Source Serif 4', 'Source Han Serif TC', 'Noto Serif CJK TC', 'Jigmo', 'STSong', 'SimSun', serif;
```

## 相關資源

- Jigmo 字型官網：<https://kamichikoichi.github.io/jigmo/>
- Cloudflare Pages 文件：<https://developers.cloudflare.com/pages/>
- CSS `unicode-range` 原理（同 Google Noto 做法）：MDN / CSS Fonts Level 4
