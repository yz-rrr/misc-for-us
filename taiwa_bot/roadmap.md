# 🗺 Development Roadmap & Architecture Notes

## 🟢 Phase 1: Proposition Mode (Current)
**目的**: 単一の命題（例：「AIは規制すべきか」）に対する合意形成。
- [x] ユーザーの態度（Politeness）による信頼度更新 (Primacy/Consolidation)
- [x] ボットの役割反転（Role Swap）
- [x] 議論の収束判定 (Convergence Check)

## 🟡 Phase 2: Selection Mode (Pending)
**目的**: 複数の選択肢（例：「旅行先はどこがいいか」）からの最適解の選択。

### 1. データ構造の拡張 (`DebateStateManager`)
現状の `arguments["main"]` だけでなく、動的に候補を追加・削除できる構造が必要。

```python
# 変更案イメージ
self.candidates = {
    "opt_1": {"name": "北海道", "scores": {...}, "tags": ["cold", "food", "nature"]},
    "opt_2": {"name": "沖縄", "scores": {...}, "tags": ["hot", "beach", "resort"]}
}
tagsが必要かどうかは置いておく。


### 3. どこに足すか？


```python
class DebateStateManager:
    def __init__(self, mode="AgreeOrNot"):
        self.mode = mode  # ここで分岐
        # ...

    def update_scores(self, eval_data):
        if self.mode == "AgreeOrNot":
            # 今のロジック（update_scores）
            pass
        elif self.mode == "selection":
            # ここに「どの候補のスコアを上げるか」の分配ロジックを書く
            self._update_selection_scores(eval_data)

```




## 発話分割
* 現在：Botの発話を一括で処理
* ネクスト：Botの発話も分離


* ボットも、ユーザの発話のみならす、ボットの意見に対して反応できる。
　発されたボットの意見によっても、選択肢に対する支持率が上下する。

* ボットの発言順：
    * (mode1) 発言順をランダムにする。
    * (mode2) 文脈によって適切な話者を選択する。ただし数ターン話さないボットがいたら発言が促される。

* 注意点：この機能を入れると、ユーザ発話前に5つのエージェントが全員発話するのでデバッグが大変かも。デバッグ楽にするためにエージェント数を3人に絞ったモードをもうけてもいいかも。