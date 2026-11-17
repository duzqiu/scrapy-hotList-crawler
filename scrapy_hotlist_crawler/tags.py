"""榜单徽标的统一口径。

各站点给的标签长短不一（百度是「热」「新」，头条是「热门事件」「新事件上榜」
「辟谣」「解读」）。这里只压缩「含热 / 含新」的长标签，其余标签保持原文：

- 文本含「热」→ `热`（如「热门事件」）
- 文本含「新」→ `新`（如「新事件上榜」）
- 其它文本原样保留（如「辟谣」「解读」）

这样既能把「热 / 新」统一成同一口径，又不会丢掉站点自己的分类标签。
"""

from typing import Iterable, List


def normalize_tags(values: Iterable[object] | None) -> List[str]:
    """把标签收敛成「热」/「新」或原文本（去重、保持顺序）。"""
    tags: List[str] = []
    for raw in values or []:
        text = " ".join(str(raw or "").split())
        if not text:
            continue
        if "热" in text:
            tag = "热"
        elif "新" in text:
            tag = "新"
        else:
            tag = text
        if tag not in tags:
            tags.append(tag)
    return tags
