# =============================================================================
# IMPORTS
# =============================================================================

import copy
import requests
import json
import threading
import os
import asyncio
import discord
# from oauth2client.service_account import ServiceAccountCredentials
from openai import OpenAI
from dotenv import load_dotenv
from datetime import datetime

# =============================================================================
# CONSTANTS & CONFIGURATION
# =============================================================================
load_dotenv()

# Environment variables
DISCORD_TOKEN = os.getenv('DISCORD_BOT_TOKEN')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
MODEL_NAME = os.getenv('OPENAI_MODEL_NAME', 'gpt-4o-mini')
# GOOGLE_JSON = os.getenv('GOOGLE_CREDENTIALS_JSON')
# SPREADSHEET_KEY = os.getenv('SPREADSHEET_KEY')

# GAS Web App URL for logging
GAS_APP_URL = "https://script.google.com/macros/s/xxxxxxxxx/exec"

# ★修正: 感度パラメータを含む詳細なロール定義に変更
DEFAULT_ROLES = {
    "A": {
        "desc": "【ユーザー反対派】論理・合理性重視。ユーザーの提案に批判的。論理的弱点を突き、安易な妥協をしない。",
        "logic_weight": 1.8,    # 論理・合理性を超重視
        "rhetoric_weight": 0.2, # 態度はあまり見ない
        "agree_bias": 0.3,      # なかなかデレない
        "disagree_bias": 1.5    # ミスには容赦ない
    },
    "B": {
        "desc": "【ユーザー支援派】感情重視。ユーザーに好意的。共感し、論理を補強する。",
        "logic_weight": 0.4,    # 論理はそこそこでいい
        "rhetoric_weight": 1.6, # 態度や熱意を高く評価
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
        "desc": "【審判】中立的・客観的。",
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
# 1回目と2回目の実効的な合計影響力を 0.20 に調整
# 計算式: (Weight_Primacy * 0.9) + Weight_Consolidation = 0.20

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
                arg.scores = {"A": -7, "B": 7, "C": -3, "D": 0, "E": 0}
                
            elif proposer == "Bot_A":
                # パターンB: Bot A提案 (ユーザー様子見)
                # Aは自分の案なので自信満々。他は様子見。
                arg.scores = {"A": 7, "B": 0, "C": 3, "D": 0, "E": 0}
                # ※この時点では役割定義は変えない（Aは「ユーザー反対派」の性格のまま提案する）

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
        # Presence計算 (Negative + Positive + Receptivity)
        # 今回のターンのユーザー信頼度（話のうまさとは別の「態度の良さ」）：-1〜+2
        current_presence = rhe['negative_politeness'] + rhe['positive_politeness'] + rhe['receptivity']
        
        # Quantity補正: 量が適切なら微加点、不適切なら微減点
        # if rhe['quantity'] == 1: pres_val += 0.5
        # elif rhe['quantity'] == -1: pres_val -= 0.5

        # Presenceスコア（ログ保存・全体指標用）
        # old：presence_score_norm = round(pres_val / 2.0, 2)
        # -1から+2まで動く。
        # 第一印象的効果（すぐに効く）
        self.user_presence_credit = (self.user_presence_credit * CREDIT_DECAY_RATE) + (current_presence * CREDIT_WEIGHT_PRIMACY)
        # Credit (-1.0 ~ +2.0) -> 倍率 (0.5 ~ 2.0)
        # 今後評価ロジックを変えて「1.0 + (self.user_presence_credit / 2.0)」が0以下になる可能性もあるので、
        # 安全のため 0.1 を下限にして、完全にゼロ（無視）やマイナス（逆効果）にはならないようにしておく
        # でもマイナスになっても面白そうだけどね。
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
        
        if all(s >= 7 for s in scores):
            return "AGREED", f"全員の賛成が得られました (Avg: {avg:.1f})"
        elif all(s <= -7 for s in scores):
            return "REJECTED", f"全員が反対で一致しました (Avg: {avg:.1f})"
        return "ONGOING", f"議論継続中 (Avg: {avg:.1f})"

# --- 3. クライアント & 外部連携セットアップ ---
# =============================================================================
# INITIALIZATION
# =============================================================================
# OpenAI & Discord client initialization
client = OpenAI(api_key=OPENAI_API_KEY)
discord_client = discord.Client(intents=discord.Intents.default())
discord_client.intents.message_content = True

# GAS経由でのログ送信を使用（直接スプレッドシートアクセスは廃止）
print("Using GAS for logging instead of direct sheet access")

# Debate state manager initialization
manager = DebateStateManager(mode="proposition")

# =============================================================================
# DISCORD EVENT HANDLERS
# =============================================================================

# =============================================================================
# FUNCTION DEFINITIONS
# old novelty def: (0:None, 1:Small, 2:Big)
# =============================================================================
def evaluate_input(user_text, context):
    """ユーザーの入力を評価する関数"""
    prompt = f"""
    Evaluate user's argument strictly. Output JSON only.
    Input: "{user_text}"
    Context: "{context}"
    
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
    
    Output JSON:
    {{
      "rationality": {{ "logic":int, "factuality":int, "relevance":int, "novelty":int, "clarity":int, "demonstrated_understanding":int }},
      "rhetoric": {{ "quantity":int, "negative_politeness":int, "positive_politeness":int, "receptivity":int, "metaphor":int, "substantiation":int }}
    }}
    """
    
    max_retries = 3
    for attempt in range(max_retries):
        try:
            res = client.chat.completions.create(
                model=MODEL_NAME,
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

async def generate_specific_bot_response(char, role, instruction, score):
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
                model=MODEL_NAME,
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

async def generate_bot_response(char, role, history, scores, status_msg):
    """通常の会話生成関数"""
    current_support = scores.get(char, 0)
    
    sys_prompt = f"""
    You are Agent {char}.
    Current Role Description: {role}
    Current Topic: {manager.topic}
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
                model=MODEL_NAME,
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

def _send_to_gas(row_data):
    """バックグラウンドでGASにデータを投げる関数"""
    try:
        headers = {'Content-Type': 'application/json'}
        payload = {"row": row_data}
        
        # requestsはデフォルトでリダイレクトを追うのでそのままでOK
        response = requests.post(
            GAS_APP_URL, 
            data=json.dumps(payload), 
            headers=headers,
            timeout=10 # タイムアウト設定推奨
        )
        
        # ステータスコード確認（200以外ならエラーログ）
        if response.status_code != 200:
            print(f"GAS Error: {response.status_code} - {response.text}")
            
    except Exception as e:
        print(f"Logging Failed: {e}")

def log_to_sheet(row_data):
    """
    メインスレッドから呼び出す関数。
    GASへのHTTP通信は遅い(1-2秒かかる)ため、
    Discord Botの反応を遅らせないよう別スレッドで実行する。
    """
    # 日時オブジェクトなどはJSON化できないので文字列に変換しておくこと
    safe_row = [str(item) for item in row_data]
    
    thread = threading.Thread(target=_send_to_gas, args=(safe_row,))
    thread.start()

@discord_client.event
async def on_message(message):
    if message.author == discord_client.user: return

    # --- コマンド処理 ---
    if message.content.startswith("!prop"):
        topic = message.content[6:]
        manager.set_topic(topic, initial_arg=topic, proposer="User")
        await message.channel.send(f"【Mode A: 命題検証】\n議題: {topic}\n議論を開始します。")
        return

    # --- ユーザー発言処理 ---
    user_text = message.content
    manager.turn_count += 1
    
    # 履歴構築 & 評価
    # ★重要: コンテキストとして直近の会話を渡す
    recent_history = "\n".join(manager.history[-5:])
    eval_res = evaluate_input(user_text, context=recent_history)
    
    # 履歴に追加
    manager.history.append(f"User: {user_text}")

    # === 初手様子見判定 ===
    is_first_turn = (manager.turn_count == 1)
    is_weak = False
    
    if eval_res and is_first_turn:
        rh = eval_res['rhetoric']
        # 詳述なし & 短すぎる/長すぎる -> 様子見とみなす
        if rh['substantiation'] == 0 and rh['quantity'] == -1:
            is_weak = True

    if is_first_turn and is_weak:
        await message.channel.send("🤖 *ユーザーの主張が弱いため、Agent Aが口火を切ります...*")
        
        # Bot A提案モードに切り替え
        manager.set_topic(manager.topic, initial_arg="Bot A Proposal", proposer="Bot_A")
        
        prompt = f"ユーザーは意見を持っていません。議題「{manager.topic}」について、議論を活性化させるための『独自の主張』や『問題提起』を行ってください。"
        resp_a = await generate_specific_bot_response("A", manager.current_roles["A"]["desc"], prompt, 7)
        
        await message.channel.send(f"**A**: {resp_a}")
        manager.history.append(f"A: {resp_a}")
        return # ここでターン終了

    # === 2ターン目の同意判定 (Bot A提案時) ===
    if manager.proposer == "Bot_A" and manager.turn_count == 2:
        # 同意キーワード または PosPolが高い
        is_agree = False
        if "同意" in user_text or "賛成" in user_text: is_agree = True
        if eval_res and eval_res['rhetoric']['positive_politeness'] == 1: is_agree = True
        
        if is_agree:
            manager.swap_roles_on_agreement()
            await message.channel.send("🔄 *ユーザーがAに同意。BとCが反対派に転向します！*")

    # === 通常処理 ===
    status_label = "Thinking..."
    presence = 0
    current_scores = {name: manager.arguments["main"].scores[name] for name in DEFAULT_ROLES.keys()}

    if eval_res:
        # presence, current_scores = manager.update_scores(eval_res)
        res_detail = manager.update_scores(eval_res)
        status_code, status_msg = manager.check_convergence()
        status_label = status_msg
        current_scores = res_detail["scores"]        

        # ログ保存（GAS経由）
        # r = eval_res['rationality']
        # rh = eval_res['rhetoric']
        #             # json.dumps(current_scores), 
        # user_rowの部分かな
        row = [
            str(datetime.now()), 
            manager.turn_count, 
            "User", 
            user_text,
            # Rationality内訳 (6列)
            *eval_res['rationality'].values(), 
            res_detail["rat_sum"],   # 11: 論理合計
            # Rhetoric内訳 (6列)
            *eval_res['rhetoric'].values(),
            res_detail["rhe_sum"],   # 18: レトリック合計
            # 数理モデルの内部変数 (4列)
            res_detail["presence"],  # 19: 直近Presence
            res_detail["credit"],    # 20: 蓄積信頼(Credit)
            res_detail["multiplier"],# 21: 増幅倍率(Multiplier)
            res_detail["rhe_impact"],# 22: 最終修辞インパクト
            json.dumps(res_detail["scores"]), # 23: ボットスコア(JSON)
            status_msg,               # 24: 収束ステータス
            status_code
        ]
        log_to_sheet(row)

        presence = res_detail["presence"]
        # 試しにuserプレゼンスに合わせてリアクションをつける
        if presence > 1.5: await message.add_reaction("✨")
        elif presence < 0: await message.add_reaction("💀")

        if status_code in ["AGREED", "REJECTED"]:
            await message.channel.send(f"🔴 **結論が出ました**: {status_msg}")

    # === ボット応答ループ (A->B->C->D->E) ===
    async with message.channel.typing():
        # 直近履歴
        hist_str = "\n".join(manager.history[-10:])
        
        for char in manager.current_roles.keys():
            # ★修正: 辞書構造が変わったので desc キーへアクセスするように変更
            role_def = manager.current_roles[char]["desc"] # ← ["desc"] を追加
            
            resp = await generate_bot_response(char, role_def, hist_str, current_scores, status_label)
                        
            await message.channel.send(f"**{char}**: {resp} `(Score: {current_scores.get(char)})`")
            manager.history.append(f"{char}: {resp}")
            
            # ボット応答ログ（GAS経由）
            # bot_row = [
            #     str(datetime.now()), manager.turn_count, char, resp,
            #     "","","","","","","","","","","","","", 
            #     json.dumps(current_scores), "Bot Turn"
            # ]
            # ボット応答ログ（列数を user_row の 26列 に合わせる）
            # 構成: 
            # 1-4: 基本(4)
            # 5-10: Rat内訳(6, 空)
            # 11: Rat合計(1, 0)
            # 12-17: Rhe内訳(6, 空)
            # 18: Rhe合計(1, 0)  <-- ここを追加
            # 19: Presence(1, 0)
            # 20: Credit(1, credit)
            # 21: Multiplier(1, 0)
            # 22: Impact(1, 0)
            # 23: Scores(1, json)
            # 24: Status Msg(1, "Bot Turn")
            # 25: Status Code(1, "ONGOING") <-- ここを追加
            
            bot_row = [str(datetime.now()), 
                       manager.turn_count, 
                       char, 
                       resp] + \
                      [""]*6 + [0] + \
                      [""]*6 + [0] + \
                      [0, 
                       manager.user_presence_credit, 
                       0, 
                       0, 
                       json.dumps(current_scores), 
                       "Bot Turn",
                       "ONGOING"]
            log_to_sheet(bot_row)
            await asyncio.sleep(2)


# =============================================================================
# MAIN EXECUTION
# =============================================================================
if __name__ == "__main__":
    discord_client.run(DISCORD_TOKEN)
