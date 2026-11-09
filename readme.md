# OrangeJudgeLangs

這個repo是用來處理動態安裝可用語言的問題

在部署資料夾（有 `langs/` 的位置）執行安裝腳本，例如 `python3 OrangeJudgeLangs/go.py`，依提示輸入要安裝的版本（逗號分隔）。
重複執行同一個腳本會保留已安裝的版本，只新增/更新選擇的版本。安裝後需重啟服務。

| 腳本 | 語言 | 來源 | 備註 |
|---|---|---|---|
| `python.py` | CPython 3.x | python.org 原始碼，在 `littleorange666/builder` 容器內編譯 | 需要 docker |
| `pypy.py` | PyPy | downloads.python.org | |
| `java.py` | Java | Adoptium Temurin JDK | |
| `rust.py` | Rust | static.rust-lang.org，在 builder 容器內安裝 | 需要 docker |
| `go.py` | Go | go.dev（驗證 sha256） | |
| `javascript.py` | JavaScript（Node.js） | nodejs.org（驗證 sha256） | |
| `typescript.py` | TypeScript | npm registry（typescript + @types/node） | 需要 Node.js，未安裝 JavaScript 時會自動下載最新 LTS |

腳本需要 `requests`、`beautifulsoup4`、`tqdm`。

## 注意事項

- Go、Node.js（JavaScript / TypeScript）、Java 的執行環境啟動時會預留大量虛擬記憶體（Go 約 700MB、Node.js 約 1.3GB），
  無法在 `RLIMIT_AS = 2 × 記憶體限制` 下執行，因此設定檔帶有 `"memory_limit_check_only": true`：
  評測時改為比較實際使用量（RSS），位址空間上限放寬為 `2 × 記憶體限制 + 4GB`。
  這需要 judge_server 與 orange_judge 支援 `memory_limit_check_only` 的版本，舊版會忽略此欄位導致這些語言無法執行。
- 腳本安裝的語言（Python、PyPy、Java、Rust、Go、JavaScript、TypeScript）都使用 `runtime` seccomp 規則：
  允許多執行緒，但禁止建立子程序、執行其他程式、建立 socket、以寫入模式開檔、對其他程序送 signal。
  被禁止的呼叫會回傳錯誤（程式可以捕捉，通常結果為 RE），不會像 `general`/`golang`/`node` 那樣直接終止執行緒。
  需要支援 `runtime` 規則的 judge_server 版本。
- TypeScript 以 `tsc` 編譯（型別錯誤視為 CE，`--strict false`），再以 Node.js 執行；TypeScript 7 以上使用原生編譯器。
- JavaScript 編譯階段為 `node --check`，語法錯誤會顯示為 CE。
