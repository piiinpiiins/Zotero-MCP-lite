# Zotero-MCP-lite 快速設定

這是一個提供給支援 **Model Context Protocol (MCP)** 客戶端使用的伺服器軟體，讓 AI 能夠具備讀取與搜尋您本機 Zotero 書目資料庫的技能。目前主流多搭配 **Claude Desktop App** 使用。

## 快速安裝（PyPI 版，推薦）

不用下載任何資料夾，跟著下面四步做就好。就像幫 Claude 裝一個新玩具，裝好它就會讀你的 Zotero 書庫了。

**第 1 步：先裝一個叫 `uv` 的小幫手**

`uv` 是一個會自動幫你準備好程式的工具。打開「終端機」（Mac）或「PowerShell」（Windows），把下面這行貼進去，按 Enter，等它跑完：

- **Mac**：`curl -LsSf https://astral.sh/uv/install.sh | sh`
- **Windows**：`powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"`

**第 2 步：打開 Claude 的設定檔**

1. 打開 Claude Desktop，點左上角選單的 **Settings（設定）**。
2. 點 **Developer（開發者）**，再點 **Edit Config（編輯設定）** 按鈕。
3. 電腦會自動幫你打開一個叫 `claude_desktop_config.json` 的檔案。

**第 3 步：把這段程式碼貼進去**

把下面這段整個複製，貼到剛剛打開的檔案裡，然後存檔（按 `Cmd + S` 或 `Ctrl + S`）：

```json
{ "mcpServers": { "zotero": { "command": "uvx", "args": ["zotero-mcp-local"] } } }
```

> 小提醒：如果檔案裡本來就有別的字，不要刪掉它們，只要把 `"zotero": { ... }` 這部分加進 `mcpServers` 裡面就好。不確定怎麼合併的話，把整個檔案內容貼給 Claude，請它幫你改好再貼回來。
**第 4 步：把 Claude 關掉再打開**

完全關掉 Claude Desktop（不是縮小，是整個關掉），再重新打開一次。這樣 Claude 就會多出讀取你 Zotero 書庫的新本領了！

---

> 上面是最簡單的方式。如果你想自己下載整個專案資料夾來安裝，請看下面的章節。

---
## 教學影片

> 影片示範的是下方「自己下載資料夾」的手動安裝方式；若你已用上面的快速安裝裝好，可直接跳過。

### 如何安裝 Zotero MCP-lite
[![如何安裝 Zotero MCP-lite](https://img.youtube.com/vi/fpTDE3DQxp4/maxresdefault.jpg)](https://youtu.be/fpTDE3DQxp4)

## 前置需求

- **Python >= 3.10**：建議透過 Homebrew 安裝 (`brew install python`)，或至 [Python 官網](https://www.python.org/downloads/) 下載安裝檔。
- **[uv](https://docs.astral.sh/uv/) 套件管理工具**：打開終端機輸入 `curl -LsSf https://astral.sh/uv/install.sh | sh` 或 `brew install uv`
- **Zotero 資料夾**（含 `zotero.sqlite`）已放置在本機電腦上

> Windows 使用者請改看 [windows_install_guide.md](windows_install_guide.md)，裡面有完整的前置需求、安裝步驟與除錯說明。

## 安裝步驟（Mac）

> Windows 使用者請改看 [windows_install_guide.md](windows_install_guide.md)。

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

---

## 如何連接到 Claude Desktop（Mac）

> Windows 使用者請改看 [windows_install_guide.md](windows_install_guide.md)。

完成上方的「前置需求」與「安裝步驟」後，透過以下步驟將程式連接至 Claude：

1. 開啟 Claude Desktop 的設定檔 `claude_desktop_config.json`（二擇一）：

   **方法 A — 從 Claude Desktop App 內開啟（推薦）**：
   1. 開啟 Claude Desktop App
   2. 點擊左上角選單 **Claude → Settings**
   3. 點選左側的 **Developer**
   4. 點擊 **Edit Config** 按鈕，系統會自動用文字編輯器打開 `claude_desktop_config.json`

   **方法 B — 手動開啟檔案**：打開 Finder，按 `Cmd + Shift + G`，貼上 `~/Library/Application Support/Claude/`，找到 `claude_desktop_config.json` 並用文字編輯器開啟。若檔案不存在，請自行新建。

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

> Windows 常見問題請看 [windows_install_guide.md](windows_install_guide.md) 的除錯章節。

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
