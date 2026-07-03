# 第三方授權聲明 / Third-Party Licenses

本專案的建置產物（`fonts/` 目錄下的 `.woff2` 字型檔）來自以下第三方字型，各有獨立授權。

---

## Jigmo（包含 Jigmo.ttf、Jigmo2.ttf、Jigmo3.ttf）

- **作者**：神地康一（Kamichikoichi）
- **來源**：<https://kamichikoichi.github.io/jigmo/>
- **授權**：CC0 1.0 公共領域貢獻宣告（Creative Commons Zero v1.0 Universal）

  作者已放棄所有著作權及相關權利，將 Jigmo 字型貢獻至公共領域。
  在法律允許的範圍內，任何人均可自由複製、修改、散布及再利用，無需取得許可或標示來源。

  完整條款：<https://creativecommons.org/publicdomain/zero/1.0/>

---

## GlyphWiki data（Jigmo SC/TC 生成用）

- **來源**：<https://glyphwiki.org/>；dump：<https://glyphwiki.org/dump.tar.gz>
- **用途**：`build_jigmo_variants.py` 讀取 GlyphWiki dump 的 KAGE data 判定 `uXXXXX-g` / `uXXXXX-t` 的可用性；生成字型時需 SVG outlines，若本機 cache 不齊，需以 `--allow-remote-svg` 明確允許從 GlyphWiki SVG endpoint 補下載。
- **授權**：GlyphWiki data license

GlyphWiki dump 的授權文字聲明：

```
These data files are free software.
Unlimited permission is hereby granted to use, copy, and distribute
these files, with or without modification, either commercially
or non-commercially.

THIS DATA IS PROVIDED "AS IS" WITHOUT ANY WARRANTY.
License of this document is the same as the data files.

Copyright 2009 GlyphWiki Project.
```

---

## Jigmo build tools（Jigmo SC/TC 參考）

- **作者**：神地康一（Kamichikoichi）
- **來源**：<https://github.com/kamichikoichi/jigmo>
- **用途**：`build_jigmo_variants.py` 參照上游 Jigmo 的 FontForge 匯入 SVG、縮放、設定 advance width 與生成 TTF 流程；生成時以原始 Jigmo 字型為基底，只替換選定 glyph。
- **授權**：MIT（依上游 README 說明）

---

## Source Serif 4

- **作者**：Adobe（Frank Grießhammer 設計）
- **來源**：<https://github.com/adobe-fonts/source-serif>
- **版本**：透過 Google Fonts API 取得（`fonts.googleapis.com`）
- **授權**：SIL Open Font License 1.1（OFL-1.1）

  本字型依 SIL OFL 1.1 授權散布。您可以自由使用、研究、修改及再散布本字型，包括商業用途，但須遵守以下條件：

  1. 任何再散布的衍生版本均須以 SIL OFL 1.1 授權發行。
  2. 衍生字型不得單獨以字型檔形式販售。
  3. 不得使用原字型的保留名稱（Reserved Font Names）於衍生版本。

  完整條款見下方 OFL 原文，或：<https://openfontlicense.org>

### SIL Open Font License 1.1 全文

```
Copyright 2014-2023 Adobe (http://www.adobe.com/)

This Font Software is licensed under the SIL Open Font License, Version 1.1.
This license is copied below, and is also available with a FAQ at:
http://scripts.sil.org/OFL

-----------------------------------------------------------
SIL OPEN FONT LICENSE Version 1.1 - 26 February 2007
-----------------------------------------------------------

PREAMBLE
The goals of the Open Font License (OFL) are to stimulate worldwide
development of collaborative font projects, to support the font creation
efforts of academic and linguistic communities, and to provide a free and
open framework in which fonts may be shared and improved in partnership
with others.

The OFL allows the licensed fonts to be used, studied, modified and
redistributed freely as long as they are not sold by themselves. The
fonts, including any derivative works, can be bundled, embedded,
redistributed and/or sold with any software provided that any reserved
names are not used by derivative works. The fonts and derivatives,
however, cannot be released under any other type of license. The
requirement for fonts to remain under this license does not apply
to any document created using the fonts or their derivatives.

DEFINITIONS
"Font Software" refers to the set of files released by the Copyright
Holder(s) under this license and clearly marked as such. This may
include source files, build scripts and documentation.

"Reserved Font Name" refers to any names specified as such after the
copyright statement(s).

"Original Version" refers to the collection of Font Software components as
distributed by the Copyright Holder(s).

"Modified Version" refers to any derivative made by adding to, deleting,
or substituting -- in part or in whole -- any of the components of the
Original Version, by changing formats or by porting the Font Software to a
new environment.

"Author" refers to any designer, engineer, programmer, technical writer or
other person who contributed to the Font Software.

PERMISSION & CONDITIONS
Permission is hereby granted, free of charge, to any person obtaining
a copy of the Font Software, to use, study, copy, merge, embed, modify,
redistribute, and sell modified and unmodified copies of the Font
Software, subject to the following conditions:

1) Neither the Font Software nor any of its individual components,
in Original or Modified Versions, may be sold by itself.

2) Original or Modified Versions of the Font Software may be bundled,
redistributed and/or sold with any software, provided that each copy
contains the above copyright notice and this license. These can be
included either as stand-alone text files, human-readable headers or
in the appropriate machine-readable metadata fields within text or
binary files as long as those fields can be easily viewed by the user.

3) No Modified Version of the Font Software may use the Reserved Font
Name(s) unless explicit written permission is granted by the corresponding
Copyright Holder. This restriction only applies to the primary font name as
presented to the users.

4) The name(s) of the Copyright Holder(s) or the Author(s) of the Font
Software shall not be used to promote or endorse Modified Versions,
except to acknowledge the contribution(s) of the Copyright Holder(s).

5) The Font Software, modified or unmodified, in part or in whole,
must be distributed entirely under this license, and must not be
distributed under any other license. The requirement for fonts to
remain under this license does not apply to any document created
using the Font Software.

TERMINATION
This license becomes null and void if any of the above conditions are
not met.

DISCLAIMER
THE FONT SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO ANY WARRANTIES OF
MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT
OF COPYRIGHT, PATENT, TRADEMARK, OR OTHER RIGHT. IN NO EVENT SHALL THE
COPYRIGHT HOLDER BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,
INCLUDING ANY GENERAL, SPECIAL, INDIRECT, INCIDENTAL, OR CONSEQUENTIAL
DAMAGES, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
FROM, OUT OF THE USE OR INABILITY TO USE THE FONT SOFTWARE OR FROM
OTHER DEALINGS IN THE FONT SOFTWARE.
```
