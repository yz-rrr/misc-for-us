import os



# =============================================================================
# CONSTANTS & CONFIGURATION
# =============================================================================


class DebateConfig:

    def __init__(self, **kwargs):
        """
        Configuration class for debate settings.
        """
        # Environment variables
        self.DISCORD_TOKEN = os.getenv('DISCORD_BOT_TOKEN')
        self.OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
        self.MODEL_NAME = os.getenv('OPENAI_MODEL_NAME', 'gpt-4o-mini')
        self.GAS_APP_URL = os.getenv('GAS_APP_URL', "https://script.google.com/macros/s/xxxxxxxxx/exec")

        # フラグ
        self.USE_MOCK = kwargs.get("use_mock", False) # APIを使わないモード

        # スコアリングパラメータ (デフォルト値)
        # --- 信頼度（Presence Credit）更新用パラメータ ---
        self.CREDIT_WEIGHT_PRIMACY = 0.15       # 第一印象（直感的判断）の重み
        self.CREDIT_WEIGHT_CONSOLIDATION = 0.065 # 事後定着（経験の固定化）の重み
        self.CREDIT_DECAY_RATE = 0.9            # 記憶の維持率
        # 0.15*0.9 + 0.065 = 0.2
        self.IMPACT_WEIGHT_BOT = 0.5

        # 入力がある場合の上書き適用（デバッグで値を調整するときに向けて）
        for k, v in kwargs.items():
            if hasattr(self, k):
                setattr(self, k, v)

        # デフォルトのロール設定
        # "User"という名前をキーに入れてはいけない！
        self.DEFAULT_ROLES = {
        "A": {
            "desc": "【ユーザー反対派】論理・合理性重視。ユーザーの提案に批判的。論理的弱点を突き、安易な妥協をしない。",
            "logic_weight": 1.5,    # 論理・合理性を超重視
            "rhetoric_weight": 0.2, # 態度はあまり見ない
            "agree_bias": 0.3,      # なかなかデレない
            "disagree_bias": 1.5    # ミスには容赦ない
        },
        "B": {
            "desc": "【ユーザー支援派】感情重視。ユーザーに好意的。共感し、論理を補強する。",
            "logic_weight": 0.5,    # 論理はそこそこでいい
            "rhetoric_weight": 1.5, # 態度や熱意を高く評価
            "agree_bias": 1.5,      # すぐ褒める
            "disagree_bias": 0.4    # 多少のミスは許す
        },
        "C": {
            "desc": "【懐疑派】バランス型。Aに同調しつつ、リスクを強調する。",
            "logic_weight": 1.2,
            "rhetoric_weight": 0.5,
            "agree_bias": 0.8,
            "disagree_bias": 1.2
        },
        "D": {
            "desc": "【風見鶏】中立的・客観的。",
            "logic_weight": 1.0,
            "rhetoric_weight": 1.0,
            "agree_bias": 1.0,
            "disagree_bias": 1.0
        },
        "E": {
            "desc": "【調停役】議論を整理し、共通点を探す。",
            "logic_weight": 0.8,
            "rhetoric_weight": 1.2,
            "agree_bias": 1.2,
            "disagree_bias": 0.8
        }
    }
