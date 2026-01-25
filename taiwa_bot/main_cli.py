import os
import sys
import asyncio
import nest_asyncio

# このファイルのディレクトリ（project_root）をsys.pathに追加
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)

# 作成したモジュールをインポート
from src.config import DebateConfig
from src.core.state_manager import DebateStateManager
from src.services.llm_service import LLMService

# ==========================================
# アプリケーションクラス (Session Controller)
# ==========================================
class DebateApp:
    def __init__(self, config_kwargs=None):
        # 1. Config初期化
        self.config = DebateConfig(**(config_kwargs or {}))
        
        # 2. Service & Manager初期化 (Dependency Injection)
        self.llm = LLMService(self.config)
        
        # デバッグ用に3人に絞る
        self.manager = DebateStateManager(self.config, active_agents=["A", "B", "E"])

    async def run_bot_turn(self, last_speaker="User", max_turns=2):
        print("\n🤖 **ボット応答 (ターン制):**")
        current_speaker = last_speaker
        
        for _ in range(max_turns):
            # 次話者決定
            next_char = self.manager.select_next_speaker(last_speaker=current_speaker)
            role_def = self.manager.current_roles[next_char]["desc"]
            
            # 発言生成
            hist_str = "\n".join(self.manager.history[-10:])
            status_msg = self.manager.check_convergence()[1]
            current_scores = self.manager.arguments["main"].scores
            
            resp = await self.llm.generate_bot_response(
                next_char, role_def, self.manager.topic, hist_str, current_scores, status_msg
            )
            
            print(f"  **{next_char}**: {resp} `(Score: {current_scores.get(next_char, 0):+.1f})`")
            self.manager.history.append(f"{next_char}: {resp}")
            self.manager.update_silence_counter(next_char)
            
            # 評価 & 更新
            target_prop = self.manager.arguments["main"].content
            eval_res = self.llm.evaluate_input(resp, hist_str, target_prop)
            
            if eval_res:
                self.manager.update_scores(
                    eval_res, 
                    speaker=next_char, 
                    impact_weight=self.config.IMPACT_WEIGHT_BOT
                )
                
                # 終了判定
                code, msg = self.manager.check_convergence()
                if code in ["AGREED", "REJECTED"]:
                    print(f"\n🔴 **結論**: {msg}")
                    return True
            
            current_speaker = next_char
            await asyncio.sleep(0.5)
        return False

    async def process_user_input(self, user_text):
        print(f"\n👤 **User**: {user_text}")
        self.manager.turn_count += 1
        
        # 評価
        hist_str = "\n".join(self.manager.history[-5:])
        target_prop = self.manager.arguments["main"].content
        
        eval_res = self.llm.evaluate_input(user_text, hist_str, target_prop)
        self.manager.history.append(f"User: {user_text}")
        
        if eval_res:
            # スコア更新
            res = self.manager.update_scores(eval_res, speaker="User")
            
            # Role Swap判定
            stance = eval_res.get("stance", 0)
            if str(stance) == "1":
                self.manager.swap_roles_on_agreement()
                print("🔄 **Role Swap Triggered!**")
            
            print(f"📈 Result: Presence={res['presence']:.2f}, Credit={res['credit']:.2f}")
            print(f"📊 Scores: {res['scores']}")
            
            code, msg = self.manager.check_convergence()
            if code in ["AGREED", "REJECTED"]:
                print(f"\n🔴 **結論**: {msg}")
                return True

        # ボットターンへ
        return await self.run_bot_turn(last_speaker="User")

    async def start(self):
        print("="*60)
        print("🎯 Debate Engine v2 (Refactored)")
        print("="*60)
        
        topic = input("📋 議題: ") or "きのこの山は明治の最高傑作である"
        self.manager.set_topic(topic, initial_arg=topic)
        print(f"✅ Start: {topic}")
        
        while True:
            u_in = input("\n👤 あなた: ").strip()
            if u_in == "quit": break
            if u_in == "scores": 
                print(self.manager.arguments["main"].scores)
                continue
                
            ended = await self.process_user_input(u_in)
            if ended: break

# ==========================================
# 起動ブロック
# ==========================================
if __name__ == "__main__":
    # ここで設定をいじれる！
    app = DebateApp(config_kwargs={
        "IMPACT_WEIGHT_BOT": 0.5,
        "USE_MOCK": False # API節約したければTrueに
    })
    
    # Colab対策
    try:
        asyncio.run(app.start())
    except RuntimeError:
        nest_asyncio.apply()
        asyncio.run(app.start())