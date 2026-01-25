import json
import threading
import requests
import asyncio
from openai import OpenAI

class LLMService:
    # =============================================================================
    # AI FUNCTIONS
    # =============================================================================

    def __init__(self, config):
        """
        config: DebateConfig のインスタンス
        """
        self.config = config
        
        # モックモードでなければクライアントを初期化
        if not getattr(self.config, "USE_MOCK", False):
            self.client = OpenAI(api_key=self.config.OPENAI_API_KEY)
        else:
            self.client = None

    def evaluate_input(client, model_name, user_text, context, target_proposition):
        """ユーザーの入力を評価する関数"""
        prompt = f"""
        Evaluate user's argument strictly. Output JSON only.
        Analyze the user's input in the context of the debate topic.

        Target Proposition: "{target_proposition}"
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

        ## Stance towards the Target Proposition
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
    # MOCK FUNCTIONS (API節約用)
    # =============================================================================
    def _mock_evaluate_input(self, user_text, target_proposition):
        """モック用の評価ロジック"""
        stance = 0
        # 簡易的なキーワード判定
        if "同意" in user_text or "賛成" in user_text or "そうだね" in user_text:
            stance = 1
        elif "反対" in user_text or "違う" in user_text:
            stance = -1
            
        return {
            "is_valid_answer": True,
            "stance": stance,
            "rationality": {"logic": 1, "factuality": 1, "relevance": 1, "novelty": 0, "clarity": 1, "demonstrated_understanding": 1},
            "rhetoric": {"quantity": 1, "negative_politeness": 0, "positive_politeness": 1, "receptivity": 1, "metaphor": 0, "substantiation": 1}
        }

    # =============================================================================
    # LOGGING FUNCTIONS
    # =============================================================================

    @staticmethod
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
        thread = threading.Thread(target=LLMService._send_to_gas, args=(gas_app_url, safe_row,))
        thread.start()