"""召回结果的合并、排序、截断工具(供三路召回节点复用)"""


def merge_scored(scored_items: list[tuple[dict, float]], id_key: str) -> list[dict]:
    """把 (payload, score) 列表按实体去重,每个实体保留最高分,按分数降序返回 payload。

    Qdrant 中同一实体的 name/desc/alias 展开成多个向量点,payload 相同(含实体 id),
    因此需要按 payload[id_key] 去重并保留最高分。
    """
    best: dict[str, dict] = {}  # 实体id -> {"payload":..., "score":...}
    for payload, score in scored_items:
        entity_id = payload.get(id_key)
        if entity_id is None:
            continue
        if entity_id not in best or score > best[entity_id]["score"]:
            best[entity_id] = {"payload": payload, "score": score}

    ranked = sorted(best.values(), key=lambda x: x["score"], reverse=True)
    return [item["payload"] for item in ranked]


def dedupe_preserving_order(items: list[dict], id_key: str) -> list[dict]:
    """按 id 去重并保持原有顺序(ES 结果已按 _score 降序,保留首次出现即可)"""
    seen: set = set()
    result: list[dict] = []
    for item in items:
        entity_id = item.get(id_key)
        if entity_id in seen:
            continue
        seen.add(entity_id)
        result.append(item)
    return result
