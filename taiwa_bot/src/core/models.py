# 0125 発言分割。Colab移植とデバッグはまだ。


# =============================================================================
# DEBATE CORE MODULE - Discord非依存のコア機能
# 将来的には複数論点でどれがいいか選ぶタイプの会話も実装したいが、今は賛成/反対タイプ
# =============================================================================

import copy
import random
import requests
import json
import threading
import asyncio
from openai import OpenAI
from datetime import datetime

from src.core.models import DEFAULT_ROLES

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
