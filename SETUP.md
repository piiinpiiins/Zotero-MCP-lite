# Zotero-MCP-lite 快速設定

## 前置需求
- Python >= 3.10
- [uv](https://docs.astral.sh/uv/) 套件管理工具
- Zotero 資料夾（含 `zotero.sqlite`）已放在 Mac 上

## 安裝步驟

1. 把整個 `Zotero-MCP-lite/` 資料夾複製到 Mac
2. 在資料夾內執行：
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

## 驗證

```bash
uv run python -m src.zotero_mcp.server
```

看到 MCP server 啟動訊息即表示成功。