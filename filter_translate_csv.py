import argparse
import os
from datetime import datetime, date
import pandas as pd
from typing import Optional, Dict, List

# 尝试加载在线翻译器（可选）
_googletrans_available = False
_deep_translator_available = False
try:
    from googletrans import Translator as GoogletransTranslator  # type: ignore
    _googletrans_available = True
except Exception:
    pass

# 进度条（可选）
_tqdm_available = False
try:
    from tqdm import tqdm  # type: ignore
    _tqdm_available = True
except Exception:
    pass

# 离线翻译（MarianMT，可选）
_marian_available = False
try:
    from transformers import MarianMTModel, MarianTokenizer  # type: ignore
    import torch  # type: ignore
    _marian_available = True
except Exception:
    pass
try:
    from deep_translator import GoogleTranslator as DeepGoogleTranslator  # type: ignore
    _deep_translator_available = True
except Exception:
    pass


def parse_args():
    parser = argparse.ArgumentParser(description="按固定时间范围过滤并翻译标题（只输出到新CSV文件，不修改原文件）")
    parser.add_argument("--input", "-i", default="valid_record_ids.csv", help="输入CSV路径")
    parser.add_argument("--output", "-o", default=None, help="输出CSV路径；不填则自动生成 *_filtered_translated.csv")
    return parser.parse_args()
    


def normalize_english(text: str) -> str:
    if not isinstance(text, str):
        return ""
    # Replace spaces with underscores; basic cleanup
    text = text.strip().replace(" ", "_")
    return text


_dict_translations: Dict[str, str] = {
    '2023年10月巴以冲突': 'October 2023 Israel Palestine Conflict',
    '抗日战争暨反法西斯战争胜利80周年': '80th Anniversary of Victory in the Anti Japanese War and World Anti Fascist War',
    '美国所谓对等关税政策': 'US Reciprocal Tariff Policy',
    '新西兰央行降息周期开启': 'New Zealand Central Bank Interest Rate Cut Cycle Begins',
    '特朗普与普京谈判美俄乌三方会晤': 'Trump Putin Negotiations US Russia Ukraine Tripartite Meeting',
}

_translation_cache: Dict[str, str] = {}


def _online_translate(text: str) -> Optional[str]:
    # 优先使用 googletrans，其次 deep_translator；失败则返回 None
    if _googletrans_available:
        try:
            gt = GoogletransTranslator()
            res = gt.translate(text, src='zh-cn', dest='en')
            if res and getattr(res, 'text', ''):
                return res.text
        except Exception:
            pass
    if _deep_translator_available:
        try:
            res = DeepGoogleTranslator(source='auto', target='en').translate(text)
            if isinstance(res, str) and res.strip():
                return res
        except Exception:
            pass
    return None


def translate_to_english(chinese_text: str) -> str:
    if not isinstance(chinese_text, str) or not chinese_text.strip():
        return ''
    # 缓存命中
    if chinese_text in _translation_cache:
        return normalize_english(_translation_cache[chinese_text])
    # 字典命中（优先）
    if chinese_text in _dict_translations:
        eng = _dict_translations[chinese_text]
        _translation_cache[chinese_text] = eng
        return normalize_english(eng)
    # 子串命中
    for k, v in _dict_translations.items():
        if k in chinese_text:
            _translation_cache[chinese_text] = v
            return normalize_english(v)
    # 在线翻译尝试
    eng_online = _online_translate(chinese_text)
    if eng_online:
        _translation_cache[chinese_text] = eng_online
        return normalize_english(eng_online)
    # 兜底：返回原文本（会是中文），但做下划线规范
    return normalize_english(chinese_text)


# 持久化缓存
_CACHE_PATH = "translation_cache.json"
def _load_persistent_cache() -> Dict[str, str]:
    try:
        if os.path.exists(_CACHE_PATH):
            import json
            with open(_CACHE_PATH, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if isinstance(data, dict):
                    return {str(k): str(v) for k, v in data.items()}
    except Exception:
        pass
    return {}


def _save_persistent_cache(cache: Dict[str, str]) -> None:
    try:
        import json
        with open(_CACHE_PATH, 'w', encoding='utf-8') as f:
            json.dump(cache, f, ensure_ascii=False)
    except Exception:
        pass


class MarianOfflineTranslator:
    def __init__(self) -> None:
        self.enabled = False
        if not _marian_available:
            return
        try:
            self.model_name = 'Helsinki-NLP/opus-mt-zh-en'
            self.tokenizer = MarianTokenizer.from_pretrained(self.model_name)
            self.model = MarianMTModel.from_pretrained(self.model_name)
            self.device = 'cuda' if 'torch' in globals() and torch.cuda.is_available() else 'cpu'
            self.model.to(self.device)
            self.enabled = True
        except Exception:
            self.enabled = False

    def batch_translate(self, texts: List[str], batch_size: int = 16) -> List[str]:
        results: List[str] = []
        if not self.enabled or not texts:
            return [translate_to_english(t) for t in texts]
        indices = range(0, len(texts), batch_size)
        iterator = tqdm(indices, desc="Offline MT", unit="batch") if _tqdm_available else indices
        for i in iterator:
            batch = texts[i:i + batch_size]
            try:
                inputs = self.tokenizer(batch, return_tensors="pt", padding=True, truncation=True).to(self.device)
                with (torch.no_grad() if 'torch' in globals() else nullcontext()):
                    translated = self.model.generate(**inputs, max_length=128)
                out_texts = self.tokenizer.batch_decode(translated, skip_special_tokens=True)
            except Exception:
                out_texts = [translate_to_english(t) for t in batch]
            out_texts = [normalize_english(t) for t in out_texts]
            results.extend(out_texts)
        return results

try:
    from contextlib import nullcontext  # py3.7+
except Exception:
    class nullcontext:  # type: ignore
        def __init__(self, *_, **__):
            pass
        def __enter__(self):
            return None
        def __exit__(self, *exc):
            return False


def main():
    args = parse_args()
    input_path = args.input
    if not os.path.exists(input_path):
        raise FileNotFoundError(f"Input file not found: {input_path}")

    # 输出路径（始终写新文件）
    if args.output:
        output_path = args.output
    else:
        root, ext = os.path.splitext(input_path)
        output_path = f"{root}_filtered_translated{ext or '.csv'}"

    # 读取CSV
    df = pd.read_csv(input_path, dtype=str)

    # 必需列
    required_cols = ["update_date", "title_chinese", "title_english"]
    for col in required_cols:
        if col not in df.columns:
            raise ValueError(f"Missing required column: {col}")

    # 解析日期
    df["update_date"] = pd.to_datetime(df["update_date"], errors="coerce").dt.date

    # 固定时间范围（含边界）
    start_date = datetime.strptime("2025-05-01", "%Y-%m-%d").date()
    end_date = datetime.strptime("2025-09-11", "%Y-%m-%d").date()

    # 过滤
    mask = (df["update_date"] >= start_date) & (df["update_date"] <= end_date)
    filtered = df.loc[mask].copy()

    # 先保存一次（只筛选，不翻译）
    filtered.to_csv(output_path, index=False, encoding="utf-8")
    print(f"已保存筛选结果到 {output_path}，开始逐行翻译并实时保存...")

    # 准备缓存与离线模型
    total = len(filtered)
    print(f"待翻译行数: {total}")
    persistent = _load_persistent_cache()
    _translation_cache.update(persistent)
    offline = MarianOfflineTranslator()

    # 按行翻译并每行保存一次
    if total > 0:
        indices = filtered.index.tolist()
        iterator = tqdm(range(total), desc="Translating", unit="row") if _tqdm_available else range(total)
        for k in iterator:
            idx = indices[k]
            zh = str(filtered.at[idx, "title_chinese"]) if not pd.isna(filtered.at[idx, "title_chinese"]) else ""
            if zh in _translation_cache:
                en = _translation_cache[zh]
            else:
                if offline.enabled and zh:
                    try:
                        en_list = offline.batch_translate([zh], batch_size=1)
                        en = en_list[0] if en_list else normalize_english(zh)
                    except Exception:
                        en = translate_to_english(zh)
                else:
                    en = translate_to_english(zh)
                _translation_cache[zh] = en
                persistent[zh] = en
                _save_persistent_cache(persistent)

            filtered.at[idx, "title_english"] = normalize_english(en)
            # 每翻译一行，立即覆盖保存
            filtered.to_csv(output_path, index=False, encoding="utf-8")

    # 仅保存筛选后的行到新文件
    filtered.to_csv(output_path, index=False, encoding="utf-8")
    print(f"已保存到 {output_path}")


if __name__ == "__main__":
    main()


