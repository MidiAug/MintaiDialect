from typing import List, Tuple, Dict


def segment_text_to_subtitles(base_text: str, total_duration: float) -> List[Dict[str, float | str]]:
    """
    使用与数字嘉庚原逻辑一致的方式，将文本切分为多段字幕并按比例分配时长。

    返回: [{"text": str, "start_time": float, "end_time": float}, ...]
    """
    base_text = (base_text or "").strip()
    if not base_text:
        return []

    punct = set('，,。.!！?？、；;：:（）()【】[]"\'…—-')

    segments: List[Tuple[str, int]] = []  # (display_text, timed_len)
    buf_display: List[str] = []
    timed_len = 0

    for ch in base_text:
        timed_len += 1
        if not ch.isspace() and ch not in punct:
            buf_display.append(ch)
        if ch.isspace() or ch in punct:
            disp = ''.join(buf_display).strip()
            if disp or timed_len > 0:
                segments.append((disp, timed_len))
            buf_display = []
            timed_len = 0

    if buf_display or timed_len > 0:
        disp = ''.join(buf_display).strip()
        segments.append((disp, timed_len))

    total_units = sum(max(1, tl) for (_, tl) in segments) or 1
    t = 0.0
    out: List[Dict[str, float | str]] = []
    for disp, tl in segments:
        dur = total_duration * (max(1, tl) / total_units)
        start = t
        end = t + dur
        text_out = disp
        if text_out:
            out.append({
                "text": text_out,
                "start_time": round(start, 3),
                "end_time": round(end, 3)
            })
        t = end

    return out


