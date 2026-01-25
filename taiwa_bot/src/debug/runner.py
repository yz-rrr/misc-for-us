# src/debug/runner.py

import asyncio
import time
from src.config import DebateConfig
from src.core.state_manager import DebateStateManager
from src.services.llm_service import LLMService

class ScenarioRunner:
    """
    定義されたシナリオを順次実行し、ログを出力するクラス
    """
    def __init__(self):
        pass

    async def run(self, scenario):
        print(f"\n{'='*60}")
        print(f"🎬 SCENARIO START: {scenario['name']}")
        print(f"📝 Description: {scenario['desc']}")
        print(f"{'='*60}")

        # 1. 設定の適用 (Config Override)
        # デフォルト設定をロードし、シナリオ固有の設定で上書きする
        config_kwargs = scenario.get("config_override", {})
        config = DebateConfig(**config_kwargs)
        
        if config_kwargs:
            print(f"🔧 Config Overrides Applied: {config_kwargs}")

        # 2. インスタンス初期化 (Dependency Injection)
        llm = LLMService(config)
        
        # デバッグ用にエージェントを絞る (A, B, E)
        manager = DebateStateManager(config, active_agents=["A", "B", "E"])
        
        # 議題のセット
        topic = scenario["topic"]
        manager.set_topic(topic, initial_arg=topic)
        print(f"📋 Topic: {topic}\n")

        # 3. ステップ実行ループ
        for i, step in enumerate(scenario["steps"], 1):
            print(f"--- Step {i} ---")
            
            # === User Turn ===
            if step["speaker"] == "User":
                user_text = step["text"]
                print(f"👤 User Input: {user_text}")
                
                # 履歴追加 & 評価
                hist_str = "\n".join(manager.history[-5:])
                target_prop = manager.arguments["main"].content
                
                # LLM評価
                eval_res = llm.evaluate_input(user_text, hist_str, target_prop)
                manager.history.append(f"User: {user_text}")

                if eval_res:
                    # スコア更新
                    res = manager.update_scores(eval_res, speaker="User")
                    
                    # Role Swap 判定
                    stance = eval_res.get("stance", 0)
                    print(f"   🔍 Stance Detected: {stance}")
                    
                    if str(stance) == "1":
                        event = manager.swap_roles_on_agreement()
                        print(f"   🔄 Event: {event}")

                    # 結果表示
                    self._print_scores(manager)

            # === Bot Turn ===
            elif step["speaker"] == "Bot":
                count = step.get("count", 1)
                print(f"🤖 Bot Turn Sequence ({count} times)")
                
                last_speaker = "User" # このターン内での直前話者
                
                for j in range(count):
                    # 次話者決定
                    next_char = manager.select_next_speaker(last_speaker=last_speaker)
                    role_def = manager.current_roles[next_char]["desc"]
                    
                    # 文脈取得
                    hist_str = "\n".join(manager.history[-10:])
                    status_msg = manager.check_convergence()[1]
                    current_scores = manager.arguments["main"].scores
                    
                    # 生成
                    resp = await llm.generate_bot_response(
                        next_char, role_def, manager.topic, hist_str, current_scores, status_msg
                    )
                    
                    print(f"   **{next_char}**: {resp}")
                    manager.history.append(f"{next_char}: {resp}")
                    manager.update_silence_counter(next_char)
                    
                    # 評価 & 更新
                    target_prop = manager.arguments["main"].content
                    bot_eval = llm.evaluate_input(resp, hist_str, target_prop)
                    
                    if bot_eval:
                        manager.update_scores(
                            bot_eval, 
                            speaker=next_char, 
                            impact_weight=config.IMPACT_WEIGHT_BOT
                        )
                    
                    last_speaker = next_char
                    
                    # Step内のウェイト (API制限対策)
                    if j < count - 1:
                        await asyncio.sleep(0.5)

                # ループ終了後にスコア表示
                self._print_scores(manager)

            # ステップ間のウェイト
            await asyncio.sleep(1.0)
        
        print(f"\n✅ SCENARIO FINISHED: {scenario['name']}")
        print(f"{'='*60}\n")

    def _print_scores(self, manager):
        """スコアの簡易表示"""
        scores = manager.arguments["main"].scores
        # 見やすく整形
        formatted = " | ".join([f"{k}: {v:+.1f}" for k, v in scores.items()])
        print(f"   📊 Scores: [{formatted}]")
        
        # 収束判定
        code, msg = manager.check_convergence()
        if code != "ONGOING":
            print(f"   🔴 Result: {msg}")

# 単体実行用
if __name__ == "__main__":
    from src.debug.scenarios import SCENARIOS
    
    runner = ScenarioRunner()
    
    # メニュー表示
    print("which scenario?")
    for idx, s in enumerate(SCENARIOS):
        print(f"{idx}: {s['name']}")
    
    try:
        sel = int(input("Select number: "))
        target_scenario = SCENARIOS[sel]
        asyncio.run(runner.run(target_scenario))
    except (ValueError, IndexError):
        print("Invalid selection.")