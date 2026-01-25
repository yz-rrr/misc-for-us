import os
import json
import asyncio
import discord
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from openai import OpenAI
from dotenv import load_dotenv
from datetime import datetime

# --- 1. 設定と定数 ---
load_dotenv()
DISCORD_TOKEN = os.getenv('DISCORD_BOT_TOKEN')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
MODEL_NAME = os.getenv('OPENAI_MODEL_NAME', 'gpt-4o-mini')
GOOGLE_JSON = os.getenv('GOOGLE_CREDENTIALS_JSON')
SPREADSHEET_KEY = os.getenv('SPREADSHEET_KEY')

# デフォルトの役割定義 (初期状態)
DEFAULT_ROLES = {
    "A": "【ユーザー反対派】ユーザーの提案に批判的。論理的弱点を突き、安易な妥協をしない。",
    "B": "【ユーザー支援派】ユーザーに好意的。共感し、論理を補強する。",
    "C": "【Aの補佐/懐疑派】Aに同調する。ユーザーの前提を疑い、リスクを強調する。",
    "D": "【審判】内部スコアに基づき態度を変える。基本は中立的・客観的。",
    "E": "【調停役】議論を整理・要約する。対立が激化した場合、共通点を探す。"
}

# --- 2. クラス定義: 議論状態管理 ---
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
        
        # ★動的ロール管理: 初期状態はデフォルトをコピー
        self.current_roles = DEFAULT_ROLES.copy()

    def set_topic(self, topic, initial_arg="ユーザー提案", proposer="User"):
        """議論のセットアップ（再初期化）"""
        self.topic = topic
        self.arguments = {}
        self.turn_count = 0
        self.history = []
        self.proposer = proposer
        
        # ロールをリセット
        self.current_roles = DEFAULT_ROLES.copy()
        
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
        
        # 2. ★役割定義の動的書き換え
        self.current_roles["A"] = "【ユーザーの相棒】あなたの提案にユーザーが同意しました。ユーザーと協力して自説を守ってください。"
        self.current_roles["B"] = "【批判的吟味役】ユーザーはAの意見に安易に同調しました。本来は支援役でしたが、この癒着には批判的になり、リスクを指摘してください。"
        self.current_roles["C"] = "【徹底抗戦】ユーザーとAの結託を崩すため、論理的な欠陥を攻撃してください。"
        
        return "ROLES_SWAPPED"

    def update_scores(self, eval_data):
        """評価に基づいてボットのスコアを更新"""
        # 1. User Impact Calculation
        rat_score = sum(eval_data['rationality'].values()) # -6 ~ +6
        
        rhe = eval_data['rhetoric']
        presence_val = (rhe['negative_politeness'] + rhe['positive_politeness'] + rhe['receptivity'])
        presence_score = round(presence_val / 2.0, 2)
        
        # 累積信頼度 (減衰あり)
        self.user_presence_credit = (self.user_presence_credit * 0.8) + (presence_score * 0.2)

        # 2. Base Delta Calculation
        delta = 0
        if rat_score >= 2:
            delta = rat_score + (self.user_presence_credit * 2)
        elif rat_score <= 0:
            delta = rat_score * 1.5 
        else:
            delta = rat_score * 0.5
            
        # 3. Bot Specific Updates
        target_arg = self.arguments["main"]
        
        for name in self.current_roles.keys():
            current_s = target_arg.scores[name]
            personal_delta = delta
            
            # ★修正: キャラ名ではなく「現在のスタンス」で説得されやすさを変える
            # 現在反対している(-スコア)キャラは、賛成意見(delta>0)に対して頑固になる
            if current_s < 0 and delta > 0:
                personal_delta *= 0.5 # 反対派は説得されにくい
            
            # 現在賛成している(+スコア)キャラは、賛成意見に対して盛り上がりやすい
            if current_s > 0 and delta > 0:
                personal_delta *= 1.2

            # 更新 & クリップ
            target_arg.scores[name] = max(-10, min(10, current_s + personal_delta))

        return presence_score, target_arg.scores

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
client = OpenAI(api_key=OPENAI_API_KEY)
discord_client = discord.Client(intents=discord.Intents.default())
discord_client.intents.message_content = True

# Google Sheets
try:
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    creds = ServiceAccountCredentials.from_json_keyfile_name(GOOGLE_JSON, scope)
    sheet = gspread.authorize(creds).open_by_key(SPREADSHEET_KEY).sheet1
    if not sheet.get_all_values():
        sheet.append_row([
            "Timestamp", "Turn", "Speaker", "Content", 
            "R_Logic", "R_Fact", "R_Rel", "R_Nov", "R_Clear", "R_Dem_Und", 
            "Rh_Qty", "Rh_NegPol", "Rh_PosPol", "Rh_Recept", "Rh_Meta", "Rh_Subst", 
            "User_Presence", "Bot_Scores_JSON", "State_Status"
        ])
except Exception as e:
    print(f"Sheet Error: {e}")
    sheet = None

# マネージャ初期化
manager = DebateStateManager(mode="proposition")

# --- 4. LLM API ラッパー関数 ---
def evaluate_input(user_text, context):
    prompt = f"""
    Evaluate user's argument strictly. Output JSON only.
    Input: "{user_text}"
    Context: "{context}"
    
    ## Rationality (Logos/Substance)
    - logic: (-1:Contradiction, 1:Consistent)
    - factuality: (-1:Error, 1:Valid)
    - relevance: (-1:Irrelevant, 1:Relevant)
    - novelty: (0:None, 1:Minor, 2:Major)
    - clarity: (-1:Unclear, 0:Clear)
    - demonstrated_understanding: (-1:Strawman/Misunderstanding, 0:None, 1:Accurate Trace)

    ## Rhetoric (Pathos/Ethos)
    - quantity: (-1:Poor, 1:Good)
    - negative_politeness: (-1:Rude, 0:Neutral)
    - positive_politeness: (0:Neutral, 1:Friendly/Aligned)
    - receptivity: (0:Closed, 1:Open/Respectful)
    - metaphor: (-1:Bad, 0:None, 1:Good)
    - substantiation: (0:Abstract/Thin, 1:Concrete/Detailed/Rigorous)
    
    Output JSON:
    {{
      "rationality": {{ "logic":int, "factuality":int, "relevance":int, "novelty":int, "clarity":int, "demonstrated_understanding":int }},
      "rhetoric": {{ "quantity":int, "negative_politeness":int, "positive_politeness":int, "receptivity":int, "metaphor":int, "substantiation":int }}
    }}
    """
    try:
        res = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[{"role": "system", "content": "JSON only"}, {"role": "user", "content": prompt}],
            response_format={"type": "json_object"}
        )
        return json.loads(res.choices[0].message.content)
    except: return None

async def generate_specific_bot_response(char, role, instruction, score):
    """特定の指示（提案など）を行わせるための生成関数"""
    sys_prompt = f"""
    You are Agent {char}. Role: {role}
    Your Score: {score} (-10 to 10)
    
    INSTRUCTION: {instruction}
    Response constraints: Concise, Japanese, under 140 chars.
    """
    try:
        res = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[{"role": "system", "content": sys_prompt}]
        )
        return res.choices[0].message.content
    except: return "..."

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
    try:
        res = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[{"role": "system", "content": sys_prompt}, {"role": "user", "content": history}]
        )
        return res.choices[0].message.content
    except: return "..."

# --- 5. メインイベントループ ---
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
        resp_a = await generate_specific_bot_response("A", manager.current_roles["A"], prompt, 7)
        
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
    current_scores = {}

    if eval_res:
        presence, current_scores = manager.update_scores(eval_res)
        status_code, status_msg = manager.check_convergence()
        status_label = status_msg
        
        # ログ保存
        if sheet:
            r = eval_res['rationality']
            rh = eval_res['rhetoric']
            row = [
                str(datetime.now()), manager.turn_count, "User", user_text,
                r['logic'], r['factuality'], r['relevance'], r['novelty'], r['clarity'], r['demonstrated_understanding'],
                rh['quantity'], rh['negative_politeness'], rh['positive_politeness'], rh['receptivity'], rh['metaphor'], rh['substantiation'],
                presence, json.dumps(current_scores), status_code
            ]
            sheet.append_row(row)

        if presence > 0.5: await message.add_reaction("✨")
        elif presence < 0: await message.add_reaction("💀")

        if status_code in ["AGREED", "REJECTED"]:
            await message.channel.send(f"🔴 **結論が出ました**: {status_msg}")

    # === ボット応答ループ (A->B->C->D->E) ===
    async with message.channel.typing():
        # 直近履歴
        hist_str = "\n".join(manager.history[-10:])
        
        for char in manager.current_roles.keys():
            # ★修正: 現在の動的ロールを使用
            role_def = manager.current_roles[char]
            
            resp = await generate_bot_response(char, role_def, hist_str, current_scores, status_label)
            
            await message.channel.send(f"**{char}**: {resp} `(Score: {current_scores.get(char)})`")
            manager.history.append(f"{char}: {resp}")
            
            if sheet:
                sheet.append_row([
                    str(datetime.now()), manager.turn_count, char, resp,
                    "","","","","","","","","","","","","", 
                    json.dumps(current_scores), "Bot Turn"
                ])
            await asyncio.sleep(2)

discord_client.run(DISCORD_TOKEN)