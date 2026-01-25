# 今はdebate_core.pyを改良中です。
# このファイルは、最新のdebate_core.pyに合わせて修正が必要かもしれません。

# =============================================================================
# DISCORD BOT - モジュラー版（debate_core.py使用）
# =============================================================================

import os
import asyncio
import discord
import json
from openai import OpenAI
from dotenv import load_dotenv
from datetime import datetime

# コア機能をインポート
from debate_core import (
    DebateStateManager, 
    DEFAULT_ROLES,
    evaluate_input,
    generate_specific_bot_response,
    generate_bot_response,
    log_to_sheet
)

# =============================================================================
# CONFIGURATION
# =============================================================================
load_dotenv()

# Environment variables
DISCORD_TOKEN = os.getenv('DISCORD_BOT_TOKEN')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
MODEL_NAME = os.getenv('OPENAI_MODEL_NAME', 'gpt-4o-mini')
GAS_APP_URL = os.getenv('GAS_APP_URL', "https://script.google.com/macros/s/xxxxxxxxx/exec")

# OpenAI & Discord client initialization
client = OpenAI(api_key=OPENAI_API_KEY)
discord_client = discord.Client(intents=discord.Intents.default())
discord_client.intents.message_content = True

# Debate state manager initialization (コア機能から)
manager = DebateStateManager(mode="proposition")

print("✅ Discord Bot initialized with modular architecture (using debate_core.py)")

# =============================================================================
# DISCORD EVENT HANDLERS
# =============================================================================

@discord_client.event
async def on_ready():
    print(f'🤖 Discord Bot logged in as {discord_client.user}')
    print(f'📚 Using debate_core.py for core functionality')
    print(f'🔗 Connected to {len(discord_client.guilds)} guild(s)')

@discord_client.event
async def on_message(message):
    if message.author == discord_client.user: 
        return

    # --- コマンド処理 ---
    if message.content.startswith("!prop"):
        topic = message.content[6:].strip()
        if not topic:
            await message.channel.send("❌ 使用方法: `!prop 議題内容`")
            return
        
        manager.set_topic(topic, initial_arg=topic, proposer="User")
        await message.channel.send(f"【Mode A: 命題検証】\n🎯 議題: {topic}\n📋 議論を開始します。")
        return

    if message.content.startswith("!help"):
        help_text = """
🤖 **議論ボット - コマンド一覧**
• `!prop [議題]` - 新しい議論を開始
• `!help` - このヘルプを表示

💡 **使い方:**
1. `!prop AIの倫理問題について` で議論開始
2. あなたの意見を投稿
3. 5つのAIエージェント(A,B,C,D,E)が応答
4. 議論が続きます

🎯 **特徴:**
• Agent A: 批判的・論理重視
• Agent B: 支援的・感情重視  
• Agent C: 懐疑的・バランス型
• Agent D: 中立的・審判役
• Agent E: 調停役・共通点探し
        """
        await message.channel.send(help_text)
        return

    # --- ユーザー発言処理 ---
    user_text = message.content.strip()
    if not user_text or user_text.startswith("!"):
        return

    # 議論が設定されていない場合
    if manager.topic == "未設定":
        await message.channel.send("❌ 先に `!prop [議題]` で議論を開始してください。")
        return

    await process_user_message(message, user_text)

# =============================================================================
# MESSAGE PROCESSING FUNCTIONS
# =============================================================================

async def process_user_message(message, user_text):
    """ユーザーメッセージの処理（コア機能使用）"""
    manager.turn_count += 1
    
    # 履歴構築 & 評価（コア機能使用）
    recent_history = "\n".join(manager.history[-5:])
    eval_res = evaluate_input(client, MODEL_NAME, user_text, context=recent_history)
    
    # 履歴に追加
    manager.history.append(f"User: {user_text}")

    # === 初手様子見判定 ===
    is_first_turn = (manager.turn_count == 1)
    is_weak = False
    
    if eval_res and is_first_turn:
        rh = eval_res['rhetoric']
        if rh['substantiation'] == 0 and rh['quantity'] == -1:
            is_weak = True

    if is_first_turn and is_weak:
        await message.channel.send("🤖 *ユーザーの主張が弱いため、Agent Aが口火を切ります...*")
        
        # Bot A提案モードに切り替え（コア機能使用）
        manager.set_topic(manager.topic, initial_arg="Bot A Proposal", proposer="Bot_A")
        
        prompt = f"ユーザーは意見を持っていません。議題「{manager.topic}」について、議論を活性化させるための『独自の主張』や『問題提起』を行ってください。"
        resp_a = await generate_specific_bot_response(client, MODEL_NAME, "A", manager.current_roles["A"]["desc"], prompt, 7)
        
        await message.channel.send(f"🤖 **A**: {resp_a}")
        manager.history.append(f"A: {resp_a}")
        return

    # === 2ターン目の同意判定 (Bot A提案時) ===
    if manager.proposer == "Bot_A" and manager.turn_count == 2:
        is_agree = False
        if "同意" in user_text or "賛成" in user_text: 
            is_agree = True
        if eval_res and eval_res['rhetoric']['positive_politeness'] == 1: 
            is_agree = True
        
        if is_agree:
            manager.swap_roles_on_agreement()
            await message.channel.send("🔄 *ユーザーがAに同意。BとCが反対派に転向します！*")

    # === 通常処理（コア機能使用） ===
    status_label = "Thinking..."
    current_scores = {name: manager.arguments["main"].scores[name] for name in DEFAULT_ROLES.keys()}

    if eval_res:
        res_detail = manager.update_scores(eval_res)
        status_code, status_msg = manager.check_convergence()
        status_label = status_msg
        current_scores = res_detail["scores"]        

        # リアクション追加
        presence = res_detail["presence"]
        if presence > 1.5: 
            await message.add_reaction("✨")
        elif presence < 0: 
            await message.add_reaction("💀")

        # ログ保存（GAS経由） - コア機能使用
        if GAS_APP_URL != "https://script.google.com/macros/s/xxxxxxxxx/exec":
            row = [
                str(datetime.now()), 
                manager.turn_count, 
                "User", 
                user_text,
                *eval_res['rationality'].values(), 
                res_detail["rat_sum"],
                *eval_res['rhetoric'].values(),
                res_detail["rhe_sum"],
                res_detail["presence"],
                res_detail["credit"],
                res_detail["multiplier"],
                res_detail["rhe_impact"],
                json.dumps(res_detail["scores"]),
                status_msg,
                status_code
            ]
            log_to_sheet(GAS_APP_URL, row)

        # 結論判定
        if status_code in ["AGREED", "REJECTED"]:
            await message.channel.send(f"🔴 **結論が出ました**: {status_msg}")

    # === ボット応答ループ (A->B->C->D->E) ===
    async with message.channel.typing():
        hist_str = "\n".join(manager.history[-10:])
        
        for char in manager.current_roles.keys():
            role_def = manager.current_roles[char]["desc"]
            
            # コア機能の生成関数を使用
            resp = await generate_bot_response(
                client, 
                MODEL_NAME, 
                char, 
                role_def, 
                manager.topic, 
                hist_str, 
                current_scores, 
                status_label
            )
            
            # Discord投稿
            await message.channel.send(f"🤖 **{char}**: {resp} `(Score: {current_scores.get(char, 0):+.1f})`")
            manager.history.append(f"{char}: {resp}")
            
            # ボット応答ログ（GAS経由）- オプション
            if GAS_APP_URL != "https://script.google.com/macros/s/xxxxxxxxx/exec":
                bot_row = [
                    str(datetime.now()), 
                    manager.turn_count, 
                    char, 
                    resp
                ] + [""]*6 + [0] + [""]*6 + [0] + [
                    0, 
                    manager.user_presence_credit, 
                    0, 
                    0, 
                    json.dumps(current_scores), 
                    "Bot Turn",
                    "ONGOING"
                ]
                log_to_sheet(GAS_APP_URL, bot_row)
            
            await asyncio.sleep(2)  # Discord API制限対応

# =============================================================================
# MAIN EXECUTION
# =============================================================================

if __name__ == "__main__":
    # 起動時チェック
    if not DISCORD_TOKEN:
        print("❌ Error: DISCORD_BOT_TOKEN が設定されていません")
        print("   .env ファイルに以下を追加してください:")
        print("   DISCORD_BOT_TOKEN=your_discord_bot_token")
        exit(1)
    
    if not OPENAI_API_KEY:
        print("❌ Error: OPENAI_API_KEY が設定されていません")
        print("   .env ファイルに以下を追加してください:")
        print("   OPENAI_API_KEY=your_openai_api_key")
        exit(1)
    
    print("🚀 Starting Discord Bot with modular architecture...")
    discord_client.run(DISCORD_TOKEN)