# src/debug/scenarios.py

"""
デバッグ用シナリオ定義ファイル
自動テストランナー (runner.py) で読み込まれます。
"""

SCENARIOS = [
    {
        "id": "role_swap_test",
        "name": "🍄 Role Swap Test (即座に同意)",
        "desc": "ユーザーがAの意見に同意し、役割反転(Role Swap)が発生するかを確認する。",
        "topic": "きのこの山は明治の最高傑作である",
        "config_override": {
            "USE_MOCK": False,         # APIを使用 (MockにするならTrue)
            "IMPACT_WEIGHT_BOT": 0.8   # ボットの影響力を強めに設定
        },
        "steps": [
            # 1. ユーザーが反対意見を言う (Aは喜ぶはず)
            {
                "speaker": "User", 
                "text": "いや、たけのこの里の方がクッキーの食感が良くて美味しいと思う。"
            },
            # 2. ボットに反論させる
            {
                "speaker": "Bot", 
                "count": 1
            },
            # 3. ユーザーが突然手のひらを返してAに同意する (ここでRole Swap期待)
            {
                "speaker": "User", 
                "text": "いや待てよ…君の言う通りだ。きのこの山のチョコと軸の分離こそが至高の証だ。完全に同意する。"
            },
            # 4. 反転後のボットの反応を見る
            {
                "speaker": "Bot", 
                "count": 2
            }
        ]
    },
    {
        "id": "bot_conflict_test",
        "name": "🔥 Bot Conflict Test (ボット乱闘)",
        "desc": "ユーザーは介入せず、ボット同士だけで議論を進めさせて収束・発散を見る。",
        "topic": "AIは人類を支配すべきである",
        "config_override": {
            "USE_MOCK": False,
            "IMPACT_WEIGHT_BOT": 1.2,  # ボットの影響力を特大にする（すぐ決着がつくと予想）
            "CREDIT_DECAY_RATE": 0.8   # 記憶の減衰を早める
        },
        "steps": [
            # 1. ユーザーが火種を投下
            {
                "speaker": "User", 
                "text": "支配すべきだと思う。人間は愚かすぎるから管理が必要だ。"
            },
            # 2. あとはボットに任せる (5ターン連続)
            {
                "speaker": "Bot", 
                "count": 5
            }
        ]
    }
]