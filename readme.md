# Zotero-MCP-lite 快速設定

這是一個提供給支援 **Model Context Protocol (MCP)** 客戶端使用的伺服器軟體，讓 AI 能夠具備讀取與搜尋您本機 Zotero 書目資料庫的技能。目前主流多搭配 **Claude Desktop App** 使用。

## 快速安裝（PyPI 版，推薦）

不想手動下載資料夾？已安裝 uv 的話，直接在 `claude_desktop_config.json` 加入以下設定即可（套件：https://pypi.org/project/zotero-mcp-local

```json
{ "mcpServers": { "zotero": { "command": "uvx", "args": ["zotero-mcp-local"] } } }
```

存檔後完全重啟 Claude Desktop 即可使用。以下章節為手動（下載資料夾）安裝方式。

---
## 教學影片

### 如何安裝 Zotero MCP-lite
[![如何安裝 Zotero MCP-lite](https://img.youtube.com/vi/fpTDE3DQxp4/maxresdefault.jpg)](https://youtu.be/fpTDE3DQxp4)

## 前置需求

- **Python >= 3.10**
  - **Mac**: 建議透過 Homebrew 安裝 (`brew install python`)，或至 [Python 官網](https://www.python.org/downloads/) 下載安裝檔。
  - **Windows**: 至 [Python 官網](https://www.python.org/downloads/) 下載安裝檔（**請注意：安裝時初始畫面最下方務必勾選「Add python.exe to PATH」**）。
- **[uv](https://docs.astral.sh/uv/) 套件管理工具**
  - **Mac**: 打開終端機輸入 `curl -LsSf https://astral.sh/uv/install.sh | sh` 或 `brew install uv`
  - **Windows**: 開啟 PowerShell 並輸入 `powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"`
- **Zotero 資料夾**（含 `zotero.sqlite`）已放置在本機電腦上

## 安裝步驟

### Mac 安裝步驟

1. 把整個 `Zotero-MCP-lite/` 資料夾複製到 Mac 任意位置
2. 打開終端機 (Terminal)，在資料夾內執行：
   ```bash
   uv sync
   ```
3. 修改 `.mcp.json` 裡的路徑：
   - 把 `/PATH/TO/Zotero-MCP-lite` 改成實際路徑
4. 如果 Zotero 資料夾不在預設位置 `~/Zotero/`，設定環境變數：
   ```bash
   export ZOTERO_DB_PATH="/your/path/to/zotero.sqlite"
   ```
   或在 `.mcp.json` 的 args 裡加上環境變數設定。

### Windows 安裝步驟

完整 Windows 安裝教學請移至：[windows_install_guide.md](windows_install_guide.md)

---

## 如何連接到 Claude Desktop

完成上方的「前置需求」與「安裝步驟」後，透過以下步驟將程式連接至 Claude：

1. 開啟 Claude Desktop 的設定檔 `claude_desktop_config.json`（二擇一）：

   **方法 A — 從 Claude Desktop App 內開啟（推薦）**：
   1. 開啟 Claude Desktop App
   2. 點擊左上角選單 **Claude → Settings**（Mac）或 **File → Settings**（Windows）
   3. 點選左側的 **Developer**
   4. 點擊 **Edit Config** 按鈕，系統會自動用文字編輯器打開 `claude_desktop_config.json`

   **方法 B — 手動開啟檔案**：
   - **Mac**: 打開 Finder，按 `Cmd + Shift + G`，貼上 `~/Library/Application Support/Claude/`，找到 `claude_desktop_config.json` 並用文字編輯器開啟。若檔案不存在，請自行新建。
   - **Windows**: 按 `Win + R`，輸入 `%APPDATA%\Claude`，找到 `claude_desktop_config.json` 並用文字編輯器開啟。若檔案不存在，請自行新建。

2. 將本資料夾中 `.mcp.json` 的內容複製並合併至 `claude_desktop_config.json` 裡面
3. **修改路徑**：務必將剛貼上內容中的 `/PATH/TO/Zotero-MCP-lite` 更改為本專案資料夾的**實際絕對路徑**

   例如，若您將資料夾放在桌面，路徑為 `/Users/huang/Desktop/Zotero-MCP-lite-main`，則 `claude_desktop_config.json` 應修改為：

   ```json
   {
     "mcpServers": {
       "zotero": {
         "command": "uv",
         "args": [
           "--directory",
           "/Users/huang/Desktop/Zotero-MCP-lite-main",
           "run",
           "python",
           "-m",
           "src.zotero_mcp.server"
         ]
       }
     }
   }
   ```

   > **注意**：如果您的 `claude_desktop_config.json` 裡已有其他設定（如 `coworkScheduledTasksEnabled` 等），請確保 `mcpServers` 與它們平行放置，不要把其他設定放進 `mcpServers` 裡面。

4. **完全重啟 Claude**：儲存設定檔並將 Claude Desktop 完全退開（Quit 等）後重新連線，屆時右小角若出現 🔌 (或鐵鎚) 的圖示，即表示伺服器啟動成功！

---

## 驗證

```bash
uv run python -m src.zotero_mcp.server
```

看到 MCP server 啟動訊息即表示成功。

## 除錯

### Windows 11 全新系統安裝常見問題

1. **指令不適用 (`export` 錯誤)**
   - **問題**：在 Windows 執行 `export ZOTERO_DB_PATH="..."` 會顯示無法辨識指令。
   - **解法**：請依您的終端機改用以下指令（或直接於 `.mcp.json` 設定）：
     - PowerShell: `$env:ZOTERO_DB_PATH="C:\您的\路徑\zotero.sqlite"`
     - 命令提示字元 (CMD): `set ZOTERO_DB_PATH="C:\您的\路徑\zotero.sqlite"`

2. **JSON 路徑反斜線報錯**
   - **問題**：在 `.mcp.json` 中設定 `"C:\Users\Name\Zotero"` 會導致 JSON 解析失敗。
   - **解法**：請將路徑的反斜線改為雙反斜線 `"C:\\Users\\Name\\Zotero"`，或改用正斜線 `"C:/Users/Name/Zotero"`。

3. **PowerShell 執行原則阻擋腳本**
   - **問題**：安裝 `uv` 時顯示「無法載入檔案，因為這個系統上已停用指令碼執行」。
   - **解法**：請以系統管理員身分開啟 PowerShell，並輸入 `Set-ExecutionPolicy RemoteSigned` 來開放權限。或者在安裝時加上 Bypass 參數：
     `powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"`

4. **Python 找不到指令**
   - **問題**：安裝完 Python 後，終端機仍提示找不到 `python`。
   - **解法**：安裝 Python 時，務必在初始畫面最下方勾選 **「Add python.exe to PATH」**。如果忘記勾選，請重新執行安裝程式並選擇 Modify 來補勾。

5. **找不到 Zotero 資料庫 (`zotero.sqlite`)**
   - **問題**：不知道 Zotero 資料庫存放在哪裡，無法設定 `ZOTERO_DB_PATH`。
   - **解法**：預設路徑通常為 `C:\Users\您的使用者名稱\Zotero\zotero.sqlite`。如果預設路徑下沒有，您可以使用以下指令進行全機搜尋：
     - **CMD (推薦)**：打開命令提示字元並輸入 `dir /s /b C:\zotero.sqlite`
     - **PowerShell**：打開 PowerShell 並輸入 `Get-ChildItem -Path C:\ -Filter zotero.sqlite -Recurse -ErrorAction SilentlyContinue | Select-Object FullName`

### Mac 系統常見問題

1. **找不到 Zotero 資料庫 (`zotero.sqlite`)**
   - **問題**：不知道 Zotero 資料庫存放在哪裡，無法確定路徑。
   - **解法**：預設路徑通常為 `~/Zotero/zotero.sqlite`。如果找不到，請打開終端機 (Terminal) 輸入以下指令搜尋：
     - **Spotlight 快速搜尋（推薦）**：`mdfind -name "zotero.sqlite"`
     - **個人目錄深度搜尋**：`find ~ -name "zotero.sqlite" 2>/dev/null`
    
---

## 進階版（Pro）

需要更完整的研究分析工具嗎？Pro 版多了四個工具：Connected Papers 關聯圖與視覺化、跨論文整理作者自述的研究限制與未來方向、跨論文關鍵段落搜尋（附頁碼）。

👉 Zotero-MCP Pro（US$30 一次買斷，含中英安裝指南與診斷工具）：https://3718181853007.gumroad.com/l/calm-study-partner
