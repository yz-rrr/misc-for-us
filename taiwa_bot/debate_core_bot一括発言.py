# 最新コードはColab 0124


# =============================================================================
# DEBATE CORE MODULE - Discord非依存のコア機能
# 将来的には複数論点でどれがいいか選ぶタイプの会話も実装したいが、今は賛成/反対タイプ
# =============================================================================

import copy
import requests
import json
import threading
import asyncio
from openai import OpenAI
from datetime import datetime


# =============================================================================
# CONSTANTS & CONFIGURATION
# =============================================================================

# ★修正: 感度パラメータを含む詳細なロール定義に変更
DEFAULT_ROLES = {
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

# --- 信頼度（Presence Credit）更新用パラメータ ---
CREDIT_WEIGHT_PRIMACY = 0.15       # 第一印象（直感的判断）の重み
CREDIT_WEIGHT_CONSOLIDATION = 0.065 # 事後定着（経験の固定化）の重み
CREDIT_DECAY_RATE = 0.9            # 記憶の維持率


# =============================================================================
# CLASS DEFINITIONS
# =============================================================================

class ArgumentItem:
    """個々の論点（提案/候補）を管理するクラス"""
    def __init__(self, id, content):
        self.id = id
        self.content = content
        # 各ボットの支持スコア (-10:完全反対 ~ +10:完全賛成)
        self.scores = {name: 0 for name in DEFAULT_ROLES.keys()}

class DebateStateManager:
    """議論のモード、進行、役割変容を管理するマネージャ"""
    def __init__(self, mode="proposition"):
        self.mode = mode
        self.topic = "未設定"
        self.arguments = {} 
        self.turn_count = 0
        self.history = [] # 会話履歴
        self.user_presence_credit = 0.0
        self.proposer = "User" 
        self.current_roles = copy.deepcopy(DEFAULT_ROLES)

    def set_topic(self, topic, initial_arg="ユーザー提案", proposer="User"):
        """議論のセットアップ（再初期化）"""
        self.topic = topic
        self.arguments = {}
        self.turn_count = 0
        self.history = []
        self.proposer = proposer
        
        # ロールをリセット
        self.current_roles = copy.deepcopy(DEFAULT_ROLES)
        
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

    def update_scores(self, eval_data):
        """評価に基づいてボットのスコアを更新（重み付けロジック版）"""
        # 1. 基礎スコアの抽出
        rat_val = sum(eval_data['rationality'].values())
        rhe = eval_data['rhetoric']
        rhe_val = sum(eval_data['rhetoric'].values())
        current_presence = rhe['negative_politeness'] + rhe['positive_politeness'] + rhe['receptivity']
        
        # 第一印象的効果（すぐに効く）
        self.user_presence_credit = (self.user_presence_credit * CREDIT_DECAY_RATE) + (current_presence * CREDIT_WEIGHT_PRIMACY)
        trust_multiplier = max(0.1, 1.0 + (self.user_presence_credit / 2.0))
        rhe_impact = rhe_val * trust_multiplier

        # 2. ボットごとの適用ループ
        target_arg = self.arguments["main"]
        
        for name in self.current_roles.keys():
            role = self.current_roles[name]
            current_s = target_arg.scores[name]
            
            # ★ここがデモの肝：ボットごとの感度計算
            # Impact = (Logic * Weight) + (Rhetoric * Weight)
            impact = (rat_val * role["logic_weight"]) + (rhe_impact * role["rhetoric_weight"])
            
            # バイアス適用
            final_delta = 0
            if impact > 0:
                final_delta = impact * role["agree_bias"]
            else:
                final_delta = impact * role["disagree_bias"]
            
            # 更新 & クリップ
            target_arg.scores[name] = max(-10, min(10, current_s + final_delta))

        # 3. 信頼度（Presence Credit）更新
        # 事後定着的効果（ゆっくり効く）
        self.user_presence_credit = (self.user_presence_credit * CREDIT_DECAY_RATE) + (current_presence * CREDIT_WEIGHT_CONSOLIDATION)

        # 分析用に計算過程の変数をすべて返す
        return {
            "presence": current_presence,
            "credit": self.user_presence_credit,
            "multiplier": trust_multiplier,
            "rat_sum": rat_val,
            "rhe_sum": rhe_val,
            "rhe_impact": rhe_impact,
            "scores": target_arg.scores
        }

    def check_convergence(self):
        """議論終了判定"""
        scores = self.arguments["main"].scores.values()
        avg = sum(scores) / len(scores)
        
        if all(s >= 1 for s in scores):
            return "AGREED", f"全員の賛成が得られました (Avg: {avg:.1f})"
        elif all(s <= -1 for s in scores):
            return "REJECTED", f"全員が反対で一致しました (Avg: {avg:.1f})"
        return "ONGOING", f"議論継続中 (Avg: {avg:.1f})"


# =============================================================================
# AI FUNCTIONS
# =============================================================================

def evaluate_input(client, model_name, user_text, context, topic):
    """ユーザーの入力を評価する関数"""
    prompt = f"""
    Evaluate user's argument strictly. Output JSON only.
    Analyze the user's input in the context of the debate topic.

    Topic: "{topic}"
    Input: "{user_text}"
    Context: "{context}"
    
    ## Answer of the Topic
    - valid_answer: (true, false)
    Determine if the user's input functions as a valid argument.
    [VALID INPUTS -> true]
       - Explicit answer: "I think X is good for this topic."
       - Hypothetical counter-example
       - Rhetorical question: "Wouldn't it be bad to do X?" (Implies X is bad)
       - Conditional argument: "If X happens, we should do Y."

       [INVALID INPUTS -> false]
       - Pure information seeking: "What is the definition of X?"
       - Meta-discussion: "Can we change the topic?"
       - Simple backchannel: "I see.", "Okay."
       - Greeting: "Hello."

    ## Stance towards the previous speaker's proposal
    - stance: (1, -1, 0)
       - 1: Explicit agreement, supporting the idea, or synonymous expressions.
       - -1: Explicit disagreement, counter-argument, or skepticism.
       - 0: Questions, asking for clarification, simple backchanneling, or unclear position.

    ## Rationality
    - logic: (-1:Contradiction, 1:Consistent)
    - factuality: (-1:Error, 1:Valid)
    - relevance: (-1:Irrelevant, 1:Relevant)
    - novelty: (0: None, 1: New Perspective or Unique Insight)
    - clarity: (-1:Unclear, 0:Clear)
    - demonstrated_understanding: (-1:Misunderstanding or Strawman, 0:None, 1:Accurate Trace)

    ## Rhetoric
    - quantity: (-1:Too short or Verbose, 1:Good)
    - negative_politeness: (-1:Rude, 0:Neutral)
    - positive_politeness: (0:Neutral, 1:Friendly or Aligned)
    - receptivity: (0:Closed, 1:Open, Respectful, or Empathetic)
    - metaphor: (1:Good Metaphor, -1:Inappropriate Metaphor, 0:None)
    - substantiation: (1:Concrete, Detailed, or Rigorous, 0:Thin)

    ## Proposition
    - 
    
    Output JSON:
    {{
      "is_valid_answer": boolean,
      "stance": int,
      "rationality": {{ "logic":int, "factuality":int, "relevance":int, "novelty":int, "clarity":int, "demonstrated_understanding":int }},
      "rhetoric": {{ "quantity":int, "negative_politeness":int, "positive_politeness":int, "receptivity":int, "metaphor":int, "substantiation":int }},
    }}
    """
    
    max_retries = 3
    for attempt in range(max_retries):
        try:
            res = client.chat.completions.create(
                model=model_name,
                messages=[{"role": "system", "content": "JSON only"}, {"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
                timeout=30
            )
            return json.loads(res.choices[0].message.content)
        except json.JSONDecodeError as e:
            print(f"JSON decode error (attempt {attempt + 1}/{max_retries}): {e}")
            if attempt == max_retries - 1:
                return None
        except Exception as e:
            print(f"OpenAI API error (attempt {attempt + 1}/{max_retries}): {e}")
            if attempt == max_retries - 1:
                return None
            import time
            time.sleep(2 ** attempt)  # Exponential backoff
    
    return None

async def generate_specific_bot_response(client, model_name, char, role, instruction, score):
    """特定の指示（提案など）を行わせるための生成関数"""
    sys_prompt = f"""
    You are Agent {char}. Role: {role}
    Your Score: {score} (-10 to 10)
    
    INSTRUCTION: {instruction}
    Response constraints: Concise, Japanese, under 140 chars.
    """
    
    max_retries = 3
    for attempt in range(max_retries):
        try:
            res = client.chat.completions.create(
                model=model_name,
                messages=[{"role": "system", "content": sys_prompt}],
                timeout=30
            )
            return res.choices[0].message.content
        except Exception as e:
            print(f"OpenAI API error for bot {char} (attempt {attempt + 1}/{max_retries}): {e}")
            if attempt == max_retries - 1:
                return f"{char}: [システムエラー]"
            await asyncio.sleep(2 ** attempt)
    
    return f"{char}: [システムエラー]"

async def generate_bot_response(client, model_name, char, role, topic, history, scores, status_msg):
    """通常の会話生成関数"""
    current_support = scores.get(char, 0)
    
    sys_prompt = f"""
    You are Agent {char}.
    Current Role Description: {role}
    Current Topic: {topic}
    Your support for proposal: {current_support} (-10 to 10)
    Global Status: {status_msg}
    
    Instruction:
    - Respond to history.
    - If score is negative, criticize. If positive, support.
    - Be concise (under 140 chars).
    """
    
    max_retries = 3
    for attempt in range(max_retries):
        try:
            res = client.chat.completions.create(
                model=model_name,
                messages=[{"role": "system", "content": sys_prompt}, {"role": "user", "content": history}],
                timeout=30
            )
            return res.choices[0].message.content
        except Exception as e:
            print(f"OpenAI API error for bot {char} (attempt {attempt + 1}/{max_retries}): {e}")
            if attempt == max_retries - 1:
                return f"[システムエラー: {char}]"
            await asyncio.sleep(2 ** attempt)
    
    return f"[システムエラー: {char}]"


# =============================================================================
# LOGGING FUNCTIONS
# =============================================================================

def _send_to_gas(gas_app_url, row_data):
    """バックグラウンドでGASにデータを投げる関数"""
    try:
        headers = {'Content-Type': 'application/json'}
        payload = {"row": row_data}
        
        response = requests.post(
            gas_app_url, 
            data=json.dumps(payload), 
            headers=headers,
            timeout=10
        )
        
        if response.status_code != 200:
            print(f"GAS Error: {response.status_code} - {response.text}")
            
    except Exception as e:
        print(f"Logging Failed: {e}")

def log_to_sheet(gas_app_url, row_data):
    """
    メインスレッドから呼び出す関数。
    GASへのHTTP通信は遅い(1-2秒かかる)ため、
    Discord Botの反応を遅らせないよう別スレッドで実行する。
    """
    safe_row = [str(item) for item in row_data]
    thread = threading.Thread(target=_send_to_gas, args=(gas_app_url, safe_row,))
    thread.start()