"""第 2 章：室內泳池（抽水前）。P7 解開之前顯示這個版本：池子是滿的、水面暗綠，什麼都看不到。

和 pool.py 共用所有擺設，只差在池子有水、沒有池底的機位。遊戲裡兩個版本的 room.json 位置完全一樣。
"""
import importlib.util
import os

import kit

_spec = importlib.util.spec_from_file_location("room_pool", os.path.join(os.path.dirname(__file__), "pool.py"))
_pool = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_pool)


def build(k):
    orig = kit.pool_basin
    kit.pool_basin = lambda k_, *a, **kw: orig(k_, *a, **{**kw, "drained": False})
    try:
        data = _pool.build(k)
    finally:
        kit.pool_basin = orig
    data["cameras"] = [c for c in data["cameras"] if c["id"] != "bottom"]
    data["zones"] = [z for z in data["zones"] if z["camera"] != "bottom"]
    data["notes"] = "抽水前的版本（P7 之前）。"
    return data
