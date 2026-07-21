from typing import Any, Dict


def sanitize_chroma_metadata(metadata: Dict[str, Any]) -> Dict[str, Any]:
    """清洗写入 Chroma 的 metadata。

    作用：
    - Chroma 的 metadata value 只允许为 str / int / float / bool。
    - 不能出现 None，否则会报错：Expected metadata value to be a str, int, float or bool。

    参数：
    - metadata: 原始元数据 dict

    返回值：
    - cleaned: 清洗后的元数据 dict

    实现思路：
    - 删除 value 为 None 的键
    - 对常见的 uuid / 数字字符串保持不变
    - 对 list/dict 等复杂类型转为字符串（尽量避免，但防止直接报错）
    """
    cleaned: Dict[str, Any] = {}
    for k, v in (metadata or {}).items():
        if v is None:
            continue
        if isinstance(v, (str, int, float, bool)):
            cleaned[k] = v
            continue
        # parent_id 可能是 int/str，这里兜底转换
        try:
            cleaned[k] = str(v)
        except Exception:
            # 实在无法转换则丢弃
            continue
    return cleaned
