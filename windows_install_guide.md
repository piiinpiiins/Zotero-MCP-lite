# Windows 安裝指南

## 快速安裝（推薦，最簡單）

不用下載任何資料夾，跟著下面四步做就好。就像幫 Claude 裝一個新玩具，裝好它就會讀你的 Zotero 書庫了。

**第 1 步：先裝一個叫 `uv` 的小幫手**

`uv` 是一個會自動幫你準備好程式的工具。在開始功能表搜尋「PowerShell」並打開它，把下面這行整個貼進去，按 Enter，等它跑完：

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

**第 2 步：打開 Claude 的設定檔**

1. 打開 Claude Desktop，點左上角選單的 **File → Settings（設定）**。
2. 點左側的 **Developer（開發者）**，再點 **Edit Config（編輯設定）** 按鈕。
3. 電腦會自動幫你打開一個叫 `claude_desktop_config.json` 的檔案。

**第 3 步：把這段程式碼貼進去**

把下面這段整個複製，貼到剛剛打開的檔案裡，然後存檔（按 `Ctrl + S`）：

```json
{ "mcpServers": { "zotero": { "command": "uvx", "args": ["zotero-mcp-local"] } } }
```

> 小提醒：如果檔案裡本來就有別的字，不要刪掉它們，只要把 `"zotero": { ... }` 這部分加進 `mcpServers` 裡面就好。不確定怎麼合併的話，把整個檔案內容貼給 Claude，請它幫你改好再貼回來。
**第 4 步：把 Claude 關掉再打開**

完全關掉 Claude Desktop（不是縮小，是整個關掉），再重新打開一次。這樣 Claude 就會多出讀取你 Zotero 書庫的新本領了！

---

## 進階安裝（自己下載資料夾）

如果你想自己下載整個專案資料夾來安裝，再看這一段就好。

### 先準備這三樣東西

- **Python（3.10 以上）**：到 [Python 官網](https://www.python.org/downloads/) 下載安裝。**最重要**：安裝畫面最下面那個「Add python.exe to PATH」一定要打勾，不然之後會找不到 Python。
- **`uv` 小幫手**：打開 PowerShell，貼上這行按 Enter：
  ```powershell
  powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
  ```
- **Zotero 資料夾**：確認電腦裡有 Zotero（裡面有一個 `zotero.sqlite` 檔案）。

### 開始安裝

1. 把整個 `Zotero-MCP-lite/` 資料夾複製到電腦任意位置（例如桌面）。
2. 打開 PowerShell，進到那個資料夾裡，輸入這行讓它自己準備好：
   ```powershell
   uv sync
   ```
3. 打開資料夾裡的 `.mcp.json`，把裡面的 `/PATH/TO/Zotero-MCP-lite` 改成這個資料夾的真實位置。
   - Windows 的路徑要用兩條斜線，例如 `"C:\\Users\\Name\\Zotero-MCP-lite"`，或用相反方向的斜線 `"C:/Users/Name/Zotero-MCP-lite"`。
4. 如果你的 Zotero 不在預設位置，告訴程式它在哪：
   - PowerShell：`$env:ZOTERO_DB_PATH="C:\你的\路徑\zotero.sqlite"`
   - 命令提示字元 (CMD)：`set ZOTERO_DB_PATH="C:\你的\路徑\zotero.sqlite"`
   - 或直接寫進 `.mcp.json` 的 args 裡。

### 連接到 Claude Desktop

1. 打開 Claude 的設定檔 `claude_desktop_config.json`（兩種方法選一個）：
   - **方法 A（推薦）**：在 Claude Desktop 點 **File → Settings → Developer → Edit Config**，電腦會自動打開這個檔案。
   - **方法 B（手動）**：按 `Win + R`，輸入 `%APPDATA%\Claude`，找到 `claude_desktop_config.json` 打開。沒有的話就自己新建一個。
2. 把資料夾裡 `.mcp.json` 的內容複製貼進去，記得把 `/PATH/TO/Zotero-MCP-lite` 改成真實路徑。
3. 完全關掉 Claude Desktop 再重新打開。右下角出現 🔌（或鐵鎚）圖示，就代表成功了！

---

## 遇到問題怎麼辦（常見狀況）

1. **打 `export` 出現錯誤**
   - Windows 不認得 `export` 這個指令。請改用：
     - PowerShell：`$env:ZOTERO_DB_PATH="C:\你的\路徑\zotero.sqlite"`
     - 命令提示字元 (CMD)：`set ZOTERO_DB_PATH="C:\你的\路徑\zotero.sqlite"`

2. **路徑裡的斜線害 JSON 壞掉**
   - 在 `.mcp.json` 寫 `"C:\Users\Name\Zotero"` 會出錯。請改成兩條斜線 `"C:\\Users\\Name\\Zotero"`，或相反方向的斜線 `"C:/Users/Name/Zotero"`。

3. **PowerShell 說「已停用指令碼執行」，不讓你裝 `uv`**
   - 用滑鼠右鍵以「系統管理員身分」打開 PowerShell，輸入 `Set-ExecutionPolicy RemoteSigned` 開放權限。
   - 或安裝時直接用這行（已經加了通關密語）：
     ```powershell
     powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
     ```

4. **裝完 Python 卻說找不到 `python`**
   - 多半是安裝時忘了勾「Add python.exe to PATH」。重新執行 Python 安裝程式，選 **Modify** 把那個勾補上。

5. **找不到 Zotero 的資料庫 `zotero.sqlite`**
   - 預設通常在 `C:\Users\你的使用者名稱\Zotero\zotero.sqlite`。
   - 找不到的話，用指令全機搜尋：
     - 命令提示字元 (CMD，推薦)：`dir /s /b C:\zotero.sqlite`
     - PowerShell：`Get-ChildItem -Path C:\ -Filter zotero.sqlite -Recurse -ErrorAction SilentlyContinue | Select-Object FullName`
