# 最新コードはColab 0124

# =============================================================================
# DEBUG CLI VERSION - Discord不要のデバッグ用CLI
# =============================================================================

import os
import asyncio
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
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
MODEL_NAME = os.getenv('OPENAI_MODEL_NAME', 'gpt-4o-mini')
GAS_APP_URL = os.getenv('GAS_APP_URL', "https://script.google.com/macros/s/xxxxxxxxx/exec")

# OpenAI client initialization
client = OpenAI(api_key=OPENAI_API_KEY)
manager = DebateStateManager(mode="proposition")


# =============================================================================
# CLI INTERFACE FUNCTIONS
# =============================================================================

def print_separator():
    """区切り線を表示"""
    print("=" * 80)

def print_bot_scores(scores):
    """ボットスコアを視覚的に表示"""
    print("\n📊 **現在のボットスコア:**")
    for char, score in scores.items():
        # スコアを視覚化 (-10 to +10)
        bar_length = 20
        filled_length = int((score + 10) / 20 * bar_length)
        bar = "█" * filled_length + "░" * (bar_length - filled_length)
        print(f"  {char}: [{bar}] {score:+.1f}")

def print_presence_reaction(presence):
    """プレゼンス反応を表示"""
    if presence > 1.5:
        print("✨ ユーザーの態度が素晴らしいです！")
    elif presence < 0:
        print("💀 ユーザーの態度に問題があります...")

async def process_user_input(user_text):
    """ユーザー入力を処理する"""
    print_separator()
    print(f"👤 **User**: {user_text}")
    
    manager.turn_count += 1
    print(f"{manager.turn_count}, {manager.proposer}")
    
    # 履歴構築 & 評価
    recent_history = "\n".join(manager.history[-5:])
    eval_res = evaluate_input(client, MODEL_NAME, user_text, 
                              context=recent_history, topic=manager.topic)
    
    # 履歴に追加
    manager.history.append(f"User: {user_text}")

    # === 初手様子見判定 ===
    is_first_turn = (manager.turn_count == 1)
    is_weak = False
    
    if eval_res and is_first_turn:
        if not eval_res.get('is_valid_answer', False):
          is_weak = True
        # rh = eval_res['rhetoric']
        # if rh['substantiation'] == 0 and rh['quantity'] == -1:
        #     is_weak = True

    if is_first_turn and is_weak and manager.proposer == "User":
        print(f"🤖 *ユーザーは議題「{manager.topic}」に対する回答を保留しました。Agent Aが口火を切ります...*")
        
        # Bot A提案モードに切り替え
        manager.set_topic(manager.topic, initial_arg="Bot A Proposal", proposer="Bot_A")
        
        prompt = f"ユーザーは意見を持っていません。議題「{manager.topic}」について、議論を活性化させるための『独自の主張』や『問題提起』を行ってください。"
        resp_a = await generate_specific_bot_response(client, MODEL_NAME, "A", manager.current_roles["A"]["desc"], prompt, 7)
        
        print(f"🤖 **A**: {resp_a}")
        manager.history.append(f"A: {resp_a}")
        return

    # === 1ターン目の同意判定 (Bot A提案時) ===
    if manager.proposer == "Bot_A" and manager.turn_count == 1:
        # is_agree = False
        # if "同意" in user_text or "賛成" in user_text: is_agree = True
        user_stance = eval_res.get('stance', 0)
        # if eval_res and eval_res['rhetoric']['positive_politeness'] == 1: is_agree = True

        is_agree = False
        print(f"🔍 Stance Detection: {user_stance}")
        if type(user_stance) == int:
            if user_stance == 1:
                is_agree = True
        elif type(user_stance) == str:
            if user_stance.upper() == "AGREE":
                is_agree = True
        
        if is_agree:
            manager.swap_roles_on_agreement()
            print("🔄 *ユーザーがAに同意。BとCが反対派に転向します！*")

    # === 通常処理 ===
    status_label = "Thinking..."
    current_scores = {name: manager.arguments["main"].scores[name] for name in DEFAULT_ROLES.keys()}

    if eval_res:
        res_detail = manager.update_scores(eval_res)
        status_code, status_msg = manager.check_convergence()
        status_label = status_msg
        current_scores = res_detail["scores"]

        # デバッグ情報表示
        print(f"\n📈 **評価結果**: Presence={res_detail['presence']:.2f}, Credit={res_detail['credit']:.2f}, Multiplier={res_detail['multiplier']:.2f}")
        print_bot_scores(current_scores)
        print_presence_reaction(res_detail["presence"])

        # ログ保存（GAS経由） - オプション
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

        if status_code in ["AGREED", "REJECTED"]:
            print(f"\n🔴 **結論が出ました**: {status_msg}")
            return True  # 議論終了

    # === ボット応答ループ (A->B->C->D->E) ===
    print("\n🤖 **ボット応答:**")
    hist_str = "\n".join(manager.history[-10:])
    
    for char in manager.current_roles.keys():
        role_def = manager.current_roles[char]["desc"]
        
        resp = await generate_bot_response(client, MODEL_NAME, char, role_def, manager.topic, hist_str, current_scores, status_label)
        print(f"  **{char}**: {resp} `(Score: {current_scores.get(char, 0):+.1f})`")
        manager.history.append(f"{char}: {resp}")
        
        await asyncio.sleep(0.5)  # 少し間を空ける

    return False  # 議論継続

# =============================================================================
# MAIN CLI LOOP
# =============================================================================

async def main():
    """メインのCLI議論ループ"""
    print("=" * 80)
    print("🎯 **議論ボット - デバッグ用CLI版**")
    print("=" * 80)
    
    # OpenAI API キーチェック
    if not OPENAI_API_KEY:
        print("❌ エラー: OPENAI_API_KEY が設定されていません")
        print("   .env ファイルに以下を追加してください:")
        print("   OPENAI_API_KEY=your_api_key_here")
        return
    
    print("✅ OpenAI API設定を確認しました")
    
    # 議題設定
    while True:
        topic = input("\n📋 議題を入力してください (例: AIの倫理): ").strip()
        if topic:
            break
        print("❌ 空の議題は設定できません。")
    
    manager.set_topic(topic, initial_arg=topic, proposer="User")
    print(f"\n✅ 【議論開始】議題: {topic}")
    print("\n💡 ヒント:")
    print("  - 'quit' で終了")
    print("  - 'scores' で現在のボットスコア表示")
    print("  - 'history' で会話履歴表示")
    
    # メイン議論ループ
    while True:
        print_separator()
        user_input = input("👤 あなた: ").strip()
        
        if user_input.lower() == 'quit':
            print("👋 議論を終了します。")
            break
        elif user_input.lower() == 'scores':
            current_scores = {name: manager.arguments["main"].scores[name] for name in DEFAULT_ROLES.keys()}
            print_bot_scores(current_scores)
            continue
        elif user_input.lower() == 'history':
            print("\n📜 **会話履歴:**")
            for i, line in enumerate(manager.history[-20:], 1):  # 直近20件
                print(f"  {i}: {line}")
            continue
        elif not user_input:
            print("❌ 空の入力は処理できません。")
            continue
        
        # ユーザー入力処理
        try:
            debate_ended = await process_user_input(user_input)
            if debate_ended:
                print("\n🎉 議論が終了しました！新しい議論を始めたい場合は再実行してください。")
                break
        except KeyboardInterrupt:
            print("\n\n👋 Ctrl+Cが押されました。議論を終了します。")
            break
        except Exception as e:
            print(f"\n❌ エラーが発生しました: {e}")
            print("議論を続行します...")



if __name__ == "__main__":
    # Google Colab等でのイベントループ競合対策
    try:
        asyncio.run(main())
    except RuntimeError as e:
        if "asyncio.run() cannot be called from a running event loop" in str(e):
            print("⚠️  既存のイベントループを検出しました（Google Colab等）")
            print("💡 以下のコードを実行してください:")
            print("---")
            print("import nest_asyncio")
            print("nest_asyncio.apply()")
            print("import asyncio")
            print("from debug_cli import main")
            print("await main()  # または asyncio.create_task(main())")
            print("---")
        else:
            raise e
        

"""
Google Colab等でのイベントループ競合対策コード例:

import nest_asyncio
nest_asyncio.apply()
import asyncio
# from debug_cli import main
await main()  # または asyncio.create_task(main())
"""
