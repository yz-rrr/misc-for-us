# Google Colab デバッグ手順 🔬

## 1️⃣ コア機能のテスト (Discord不要)

```python
# 1. ライブラリインストール
!pip install openai python-dotenv requests

# 2. ファイルアップロード
from google.colab import files
# debate_core.py をアップロード
# debug_cli.py をアップロード

# 3. API キー設定 (セキュリティ注意)
import os
os.environ['OPENAI_API_KEY'] = 'your_openai_api_key_here'
os.environ['OPENAI_MODEL_NAME'] = 'gpt-4o-mini'
os.environ['GAS_APP_URL'] = 'your_gas_app_url_here'  # オプション

# 4. デバッグ実行
import asyncio
import sys
import importlib

# Colab環境での非同期実行
import nest_asyncio
nest_asyncio.apply()

# ⚠️ 重要: モジュール更新時の強制リロード
# ファイルを更新した場合は以下を実行してリロード
if 'debate_core' in sys.modules:
    importlib.reload(sys.modules['debate_core'])
if 'debug_cli' in sys.modules:
    importlib.reload(sys.modules['debug_cli'])

# debug_cli.py をインポートして実行
from debug_cli import main
asyncio.run(main())
```

## 2️⃣ Google Apps Script 連携 (オプション)

GAS_APP_URL を設定すると、Google Sheet にログが記録されます：

```python
os.environ['GAS_APP_URL'] = 'https://script.google.com/macros/s/YOUR_SCRIPT_ID/exec'
```

## 3️⃣ 使用方法

1. 議題入力: `AIの倫理`
2. 議論開始: あなたの意見を入力
3. コマンド:
   - `quit`: 終了
   - `scores`: スコア表示
   - `history`: 履歴表示

## 4️⃣ トラブルシューティング

- **API キーエラー**: OpenAI API キーを再確認
- **非同期エラー**: `nest_asyncio.apply()` を実行
- **モジュールエラー**: ファイルが正しくアップロードされているか確認
- **古いモジュール問題**: ファイル更新後は必ずリロード処理を実行（上記参照）

### 📝 モジュール更新ワークフロー

Colabでコードを修正する場合の手順：

1. **ファイル編集**: `debate_core.py` や `debug_cli.py` を修正
2. **ファイル再アップロード**: 修正版をColabにアップロード
3. **強制リロード**: 上記のリロードコードを実行
4. **テスト実行**: `asyncio.run(main())` で動作確認

⚠️ **注意**: リロードを忘れると古いバージョンが実行されます！

## 5️⃣ Discord版との違い

| 機能 | Discord版 | CLI版 |
|------|-----------|-------|
| ユーザー入力 | Discord メッセージ | 標準入力 |
| ボット応答 | Discord チャンネル | 標準出力 |
| リアクション | Discord 絵文字 | テキスト表示 |
| 履歴管理 | 同一 | 同一 |
| 評価システム | 同一 | 同一 |

完全に同一のロジックで動作します！ 🎯