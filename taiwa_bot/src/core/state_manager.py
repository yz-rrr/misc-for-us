import copy
import random
from src.config import DebateConfig
from src.core.models import ArgumentItem


class DebateStateManager:
    """議論のモード、進行、役割変容を管理するマネージャ"""
    def __init__(self, mode="proposition", active_agents=None):
        self.config = DebateConfig()
        self.mode = mode
        self.topic = "未設定"
        self.arguments = {} 
        self.turn_count = 0
        self.history = [] # 会話履歴
        # self.user_presence_credit = 0.0
        self.presence_credits = {name: 0.0 for name in self.config.DEFAULT_ROLES.keys()}
        self.presence_credits["User"] = 0.0 # ユーザー用も追加
        self.proposer = "User" 
        # self.current_roles = copy.deepcopy(DEFAULT_ROLES)
        # ★変更: アクティブなエージェントをフィルタリング
        # active_agents=["A", "B", "C"] のように指定可能にする
        full_roles = copy.deepcopy(self.config.DEFAULT_ROLES)
        if active_agents:
            self.current_roles = {k: v for k, v in full_roles.items() if k in active_agents}
        else:
            self.current_roles = full_roles

        # 最終発言からのターン数を記録（沈黙防止用）
        self.silence_counter = {k: 0 for k in self.current_roles.keys()}


    def set_topic(self, topic, initial_arg="ユーザー提案", proposer="User"):
        """議論のセットアップ（再初期化）"""
        self.topic = topic
        self.arguments = {}
        self.turn_count = 0
        self.history = []
        self.proposer = proposer
        
        # ロールをリセット
        self.current_roles = copy.deepcopy(self.config.DEFAULT_ROLES)
        
        # 論点オブジェクト作成
        self.arguments["main"] = ArgumentItem("main", initial_arg)
        arg = self.arguments["main"]

        if self.mode == "proposition":
            if proposer == "User":
                # パターンA: ユーザー提案 (通常)
                arg.scores = {"A": -7, "B": 7, "C": -5, "D": 0, "E": 0}
                
            elif proposer == "Bot_A":
                # パターンB: Bot A提案 (ユーザー様子見)
                # Aは自分の案なので自信満々。CもAにつられる。他は様子見。
                arg.scores = {"A": 7, "B": 0, "C": 3, "D": 0, "E": 0}

    def swap_roles_on_agreement(self):
        """ユーザーがBot Aの提案に同意した場合、役割と陣営を反転させる"""
        arg = self.arguments["main"]
        
        # 1. スコア反転
        arg.scores["A"] = 7   # Aは味方
        arg.scores["B"] = -7  # Bは敵に転向
        arg.scores["C"] = -7  # Cも敵
        
        # 2. ★役割定義の動的書き換え（辞書形式を維持！）
        self.current_roles["A"] = {
            "desc": "【ユーザーの相棒】あなたの提案にユーザーが同意しました。ユーザーと協力して自説を守ってください。",
            "logic_weight": 1.0, "rhetoric_weight": 1.5, "agree_bias": 1.5, "disagree_bias": 0.3
        }
        self.current_roles["B"] = {
            "desc": "【批判的吟味役】ユーザーはAの意見に安易に同調しました。本来は支援役でしたが、この癒着には批判的になり、リスクを指摘してください。",
            "logic_weight": 1.5, "rhetoric_weight": 0.5, "agree_bias": 0.5, "disagree_bias": 1.5
        }
        self.current_roles["C"] = {
            "desc": "【徹底抗戦】ユーザーとAの結託を崩すため、論理的な欠陥を攻撃してください。",
            "logic_weight": 1.8, "rhetoric_weight": 0.2, "agree_bias": 0.2, "disagree_bias": 1.8
        }

        return "ROLES_SWAPPED"

    def update_scores(self, eval_data, impact_weight: float=1.0, speaker: str="User") -> dict:
        """
        評価に基づいてボットのスコアを更新（重み付けロジック版）
        impact_weight: 全体的な影響度調整用。userとbotの発言の影響度調整などに使用。
        """
        # 1. 基礎スコアの抽出
        rat_val = sum(eval_data['rationality'].values())
        rhe = eval_data['rhetoric']
        rhe_val = sum(eval_data['rhetoric'].values())
        current_presence = rhe['negative_politeness'] + rhe['positive_politeness'] + rhe['receptivity']
        
        # ★修正: 話者ごとの信用度を取得・更新
        current_credit = self.presence_credits.get(speaker, 0.0)

        # 第一印象的効果（すぐに効く）
        self.presence_credits[speaker] = (self.presence_credits.get(speaker, 0.0) * self.config.CREDIT_DECAY_RATE) + (current_presence * self.config.CREDIT_WEIGHT_PRIMACY)
        trust_multiplier = max(0.1, 1.0 + (self.presence_credits[speaker] / 2.0))
        rhe_impact = rhe_val * trust_multiplier

        print(f"Debug: rat_val={rat_val}, rhe_val={rhe_val}, presence={current_presence}, credit={self.presence_credits[speaker]}, multiplier={trust_multiplier}, rhe_impact={rhe_impact}")
        # ★追加: スコア変動の「方向」を決定
        # デフォルトは中立
        direction = 0

        try:
            st = eval_data.get('stance', 0)
            if isinstance(st, str):
                if st.upper() == "AGREE": direction = 1
                elif st.upper() == "DISAGREE": direction = -1
                else: direction = 0
            else:
                direction = int(st)
        except:
            direction = 0


        # 2. ボットごとの適用ループ
        target_arg = self.arguments["main"]
        
        for name in self.current_roles.keys():
            # ★追加: 発言者本人のスコアは変動させない
            if name == speaker:
                continue

            role = self.current_roles[name]
            current_s = target_arg.scores[name]
            
            # ★ここがデモの肝：ボットごとの感度計算
            # Impact = (Logic * Weight) + (Rhetoric * Weight)
            impact = (rat_val * role["logic_weight"]) + (rhe_impact * role["rhetoric_weight"])
            
            # バイアス適用
            base_delta = 0
            if impact > 0:
                base_delta = impact * role["agree_bias"]
            else:
                base_delta = impact * role["disagree_bias"]

            # ★修正: ここで方向を掛け合わせる
            # # もし「発言者本人」のスコアは変動させない、としたいならここで分岐する。
            # 反対(-1)なら、良い意見(Positive Impact)ほどスコアを下げる
            # impact_weightも掛ける
            final_delta = base_delta * direction * impact_weight

            # 更新 & クリップ
            target_arg.scores[name] = max(-10, min(10, current_s + final_delta))

        # 3. 信頼度（Presence Credit）更新
        # 事後定着的効果（ゆっくり効く）
        self.presence_credits[speaker] = (self.presence_credits.get(speaker, 0.0) * self.config.CREDIT_DECAY_RATE) + (current_presence * self.config.CREDIT_WEIGHT_CONSOLIDATION)

        # 分析用に計算過程の変数をすべて返す
        return {
            "presence": current_presence,
            "credit": self.presence_credits.get(speaker, 0.0),
            "multiplier": trust_multiplier,
            "rat_sum": rat_val,
            "rhe_sum": rhe_val,
            "rhe_impact": rhe_impact,
            "scores": target_arg.scores
        }

    def check_convergence(self):
        """議論終了判定"""
        scores = self.arguments["main"].scores.values()
        print(scores)
        avg = sum(scores) / len(scores)
        
        if all(s >= 2 for s in scores):
            return "AGREED", f"全員の賛成が得られました (Avg: {avg:.1f})"
        elif all(s <= -2 for s in scores):
            return "REJECTED", f"全員が反対で一致しました (Avg: {avg:.1f})"
        return "ONGOING", f"議論継続中 (Avg: {avg:.1f})"


    def select_next_speaker(self, mode="random", last_speaker="User"):
        """次の発話者を決定する"""
        candidates = list(self.current_roles.keys())
        
        # 直前の発言者は候補から外す（連続発言防止）
        if last_speaker in candidates and len(candidates) > 1:
            candidates.remove(last_speaker)

        # --- Mode 1: Random ---
        if mode == "random":
            # ただし、3ターン以上黙っているボットがいたら優先的に指名
            silence_limit = 3
            silent_bots = [k for k in candidates if self.silence_counter[k] >= silence_limit]
            
            if silent_bots:
                next_char = random.choice(silent_bots)
            else:
                next_char = random.choice(candidates)
            
            return next_char

        # --- Mode 2: Context-aware (LLM) ---
        # ※ここはコストがかかるので、簡易的には「スコアが最も乖離している人」などのルールベースも可
        # 本格的にやるなら別途 generate_next_speaker_by_llm() を呼ぶ
        return self.select_next_speaker_heuristic(candidates)

    def select_next_speaker_heuristic(self, candidates):
        """(Mode 2簡易版) 現在の議論状況に基づいてルールベースで選択"""
        # 例: 直前の発言に対して、最も反対スコアを持っているボットを選ぶ（議論を活性化させるため）
        # 本来はLLMで「誰が反論すべきか？」を判定するのがベスト
        target_arg = self.arguments["main"]
        
        # スコアの絶対値が低い（＝態度が未定）順、あるいは
        # 極端なスコアのボットを選ぶなど
        # ここではランダムにフォールバック（実装例として）
        return random.choice(candidates)

    def update_silence_counter(self, speaker):
        """発言した人は0リセット、他は+1"""
        for k in self.silence_counter:
            if k == speaker:
                self.silence_counter[k] = 0
            else:
                self.silence_counter[k] += 1

