#!/usr/bin/env python3
"""Cross-market ticker normalizer (v7.1), network-free.

Resolves cashtags, exchange-suffixed symbols, bare numeric listing codes, and
CJK/English company names to a Yahoo-style symbol with exchange and currency.
v7.1 adds the dated listing universe in assets/universe/ (built by
connectors/universe.py from the CNINFO, HKEXnews and SEC lists): every A-share,
Hong Kong share and SEC-registered US ticker resolves by code or by name
(simplified, traditional or English), and A+H / HK+US cross-listings are
reported alongside.  Ambiguous inputs are never guessed: they return ranked
candidates with review_needed=true so the agent must verify against the exchange.

Examples:
  python scripts/ticker_normalizer.py '$SIVE' 'TOWA (6315)' 688017 '台积电' 2330
  python scripts/ticker_normalizer.py 贵州茅台 腾讯 000858 00700 苹果 'Apple Inc'
  python scripts/ticker_normalizer.py --hint Korea 000660
"""
from __future__ import annotations

import argparse
import json
import re
import unicodedata
from pathlib import Path
from typing import Any

SEED_PATH = Path(__file__).resolve().parents[1] / "assets" / "ticker-aliases.seed.json"
UNIVERSE_DIR = Path(__file__).resolve().parents[1] / "assets" / "universe"
_HK_SUFFIX = re.compile(r"-(?:sw|w|s|b|r|p|u)$")
_CJK_SUFFIX = re.compile(r"(?:控股|集团|集團|股份|有限公司|公司)+$")
_EN_SUFFIX = re.compile(r"\b(?:inc|incorporated|corp|corporation|co|company|ltd|limited|plc|holdings?|group|n v|s a|ag|se|the)\b")

SUFFIX_INFO = {
    "": ("US", "USD"), "ST": ("Nasdaq Stockholm", "SEK"), "PA": ("Euronext Paris", "EUR"),
    "AS": ("Euronext Amsterdam", "EUR"), "BR": ("Euronext Brussels", "EUR"), "DE": ("XETRA", "EUR"),
    "F": ("Frankfurt", "EUR"), "MI": ("Borsa Italiana", "EUR"), "L": ("London", "GBp"),
    "SW": ("SIX Swiss", "CHF"), "CO": ("Copenhagen", "DKK"), "OL": ("Oslo", "NOK"),
    "HE": ("Helsinki", "EUR"), "TO": ("TSX", "CAD"), "V": ("TSX Venture", "CAD"),
    "AX": ("ASX", "AUD"), "T": ("Tokyo", "JPY"), "KS": ("KOSPI", "KRW"), "KQ": ("KOSDAQ", "KRW"),
    "TW": ("TWSE", "TWD"), "TWO": ("TPEx", "TWD"), "HK": ("HKEX", "HKD"), "SS": ("Shanghai", "CNY"),
    "SZ": ("Shenzhen", "CNY"), "BJ": ("Beijing", "CNY"), "SI": ("SGX", "SGD"), "NS": ("NSE India", "INR"),
}
HINTS = {
    "KS": ("korea", "kospi", "韩国", "韓國", "韩股"), "KQ": ("kosdaq",),
    "T": ("japan", "tokyo", "jp", "日本", "日股", "东证"), "TW": ("taiwan", "twse", "台湾", "台灣", "台股"),
    "TWO": ("tpex", "otc taiwan", "上柜", "上櫃"), "HK": ("hong kong", "hkex", "港股", "香港"),
    "SS": ("shanghai", "sse", "沪", "上交所", "科创板"), "SZ": ("shenzhen", "szse", "深", "深交所", "创业板"),
    "ST": ("sweden", "stockholm", "瑞典"), "PA": ("paris", "france", "法国"), "DE": ("germany", "xetra", "德国"),
    "L": ("london", "uk", "英国"),
}


def _norm(text: str) -> str:
    text = unicodedata.normalize("NFKC", text).strip().lower()
    return re.sub(r"[\s.,'’()（）]+", " ", text).strip()


def load_aliases(paths: list[Path]) -> dict[str, dict[str, Any]]:
    table: dict[str, dict[str, Any]] = {}
    for path in paths:
        if not path.is_file():
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        for row in data.get("aliases", []):
            sym = row["symbol"]
            for name in [sym, sym.split(".")[0], *row.get("names", [])]:
                table.setdefault(_norm(name), row)
    return table


def _result(inp: str, symbol: str | None, confidence: float, reason: str,
            candidates: list[str] | None = None) -> dict[str, Any]:
    out: dict[str, Any] = {"input": inp, "symbol": symbol, "confidence": round(confidence, 2),
                           "review_needed": symbol is None or confidence < 0.8, "reason": reason}
    if symbol:
        suffix = symbol.split(".")[-1] if "." in symbol else ""
        exch, ccy = SUFFIX_INFO.get(suffix, ("unknown", "unknown"))
        out.update(exchange=exch, currency=ccy)
    if candidates:
        out["candidates"] = candidates
    return out


def numeric_candidates(code: str) -> list[str]:
    """Plausible listings for a bare numeric code, most likely first."""
    c: list[str] = []
    if len(code) == 6:
        if code.startswith(("60", "68", "90")):
            c.append(f"{code}.SS")
        if code.startswith(("00", "30", "20")):
            c.append(f"{code}.SZ")
        if code.startswith(("43", "83", "87", "88", "92")):
            c.append(f"{code}.BJ")
        c += [f"{code}.KS", f"{code}.KQ"]  # Korean codes are also 6 digits
    elif len(code) == 4:
        c += [f"{code}.TW", f"{code}.TWO", f"{code}.T", f"{int(code):04d}.HK"]
    elif len(code) == 5:
        c.append(f"{code[-4:] if code.startswith('0') else code}.HK")
    return list(dict.fromkeys(c))


class Universe:
    """Dated listing lists (assets/universe/*.json); empty when the files are absent."""

    def __init__(self, directory: Path = UNIVERSE_DIR) -> None:
        self.as_of: dict[str, str] = {}
        self.cn: dict[str, tuple[str, str]] = {}      # code -> (symbol, name)
        self.hk: dict[str, tuple[str, str]] = {}      # 4-digit code -> (symbol, display name)
        self.us: dict[str, tuple[str, str]] = {}      # ticker -> (symbol, name)
        self.names: dict[str, list[tuple[str, str]]] = {}  # normalised name -> [(symbol, name)]
        self.ah: dict[str, str] = {}                  # A <-> H symbol links (both directions)
        self.hk_us: dict[str, str] = {}               # HK <-> US ADR links (both directions)
        for market in ("cn", "hk", "us", "ah"):
            path = directory / f"{market}.json"
            if not path.is_file():
                continue
            data = json.loads(path.read_text(encoding="utf-8"))
            self.as_of[market] = data.get("as_of", "")
            for row in data.get("rows", []):
                getattr(self, f"_load_{market}")(row)
        if SEED_PATH.is_file():
            for hk, us, _name in json.loads(SEED_PATH.read_text(encoding="utf-8")).get("cross_listings", {}).get("rows", []):
                self.hk_us[hk], self.hk_us[us] = us, hk

    def _index(self, name: str, symbol: str, display: str) -> None:
        base = _HK_SUFFIX.sub("", _norm(name)).strip()
        core = _CJK_SUFFIX.sub("", base)
        for key in {_norm(name), base, core if len(core) >= 2 else base}:
            if key and (symbol, display) not in self.names.setdefault(key, []):
                self.names[key].append((symbol, display))

    def _load_cn(self, row: list[Any]) -> None:
        code, symbol, name = row[0], row[1], row[2]
        self.cn[code] = (symbol, name)
        self._index(name, symbol, name)

    def _load_hk(self, row: list[Any]) -> None:
        code, symbol, tc, sc, en = row[:5]
        display = sc or tc
        self.hk[symbol.split(".")[0]] = (symbol, display)
        for name in (tc, sc):
            if name:
                self._index(name, symbol, display)

    def _load_us(self, row: list[Any]) -> None:
        ticker, name = row[0], row[1]
        self.us[ticker.upper()] = (ticker.upper(), name)
        core = re.sub(r"\s+", " ", _EN_SUFFIX.sub(" ", _norm(name))).strip()
        if core:
            self._index(core, ticker.upper(), name)

    def _load_ah(self, row: list[Any]) -> None:
        self.ah[row[0]], self.ah[row[1]] = row[1], row[0]

    def name_matches(self, text: str) -> tuple[list[tuple[str, str]], str]:
        key = _norm(text)
        exact = self.names.get(key) or self.names.get(_HK_SUFFIX.sub("", key).strip())
        if not exact:
            core = re.sub(r"\s+", " ", _EN_SUFFIX.sub(" ", key)).strip()
            exact = self.names.get(core) if core and core != key else None
        if exact:
            return exact, "exact"
        if len(key) < 2:
            return [], "none"
        pref = [v for k, vals in self.names.items() if k.startswith(key) for v in vals]
        if pref:
            return list(dict.fromkeys(pref))[:12], "prefix"
        inner = [v for k, vals in self.names.items() if key in k for v in vals] if len(key) >= 2 and not key.isascii() else []
        return list(dict.fromkeys(inner))[:12], "contains" if inner else "none"

    def links(self, symbol: str) -> dict[str, str]:
        out = {}
        if symbol in self.ah:
            out["a_share" if symbol.endswith(".HK") else "h_share"] = self.ah[symbol]
        if symbol in self.hk_us:
            out["us_adr" if symbol.endswith(".HK") else "hk_line"] = self.hk_us[symbol]
        return out


_UNIVERSE: Universe | None = None


def universe() -> Universe:
    global _UNIVERSE
    if _UNIVERSE is None:
        _UNIVERSE = Universe()
    return _UNIVERSE


def _with_listing(res: dict[str, Any], uni: Universe) -> dict[str, Any]:
    sym = res.get("symbol")
    if not sym:
        return res
    for table in (uni.cn, uni.hk, uni.us):
        key = sym.split(".")[0] if "." in sym else sym
        hit = table.get(key) or (uni.hk.get(f"{int(key):04d}") if table is uni.hk and key.isdigit() and sym.endswith(".HK") else None)
        if hit and hit[0] == sym:
            res.setdefault("name", hit[1])
            break
    links = uni.links(sym)
    if links:
        res["cross_listings"] = links
    return res


def _pick_line(matches: list[tuple[str, str]], hint_l: str) -> tuple[str, str] | None:
    """One company, several lines (A+H, HK+ADR): prefer the market the user hinted, else the home line."""
    syms = [m[0] for m in matches]
    for suffix, words in HINTS.items():
        if any(w in hint_l for w in words):
            pref = [m for m in matches if m[0].endswith("." + suffix)]
            if pref:
                return pref[0]
    if any(w in hint_l for w in ("美股", "us", "nasdaq", "nyse", "adr")):
        pref = [m for m in matches if "." not in m[0]]
        if pref:
            return pref[0]
    uni = universe()
    if len(matches) == 2 and (uni.ah.get(syms[0]) == syms[1] or uni.hk_us.get(syms[0]) == syms[1]):
        order = {"SS": 0, "SZ": 0, "BJ": 0, "HK": 1}
        return sorted(matches, key=lambda m: order.get(m[0].rsplit(".", 1)[-1] if "." in m[0] else "", 2))[0]
    return None


def normalize(raw: str, aliases: dict[str, dict[str, Any]], hint: str = "") -> dict[str, Any]:
    uni = universe()
    res = _with_listing(_normalize(raw, aliases, hint), uni)
    links = res.get("cross_listings") or {}
    hint_l = hint.lower()
    want = None
    if links.get("us_adr") and any(w in hint_l for w in ("美股", "us", "nasdaq", "nyse", "adr")):
        want = links["us_adr"]
    elif links.get("h_share") and any(w in hint_l for w in HINTS["HK"]):
        want = links["h_share"]
    elif links.get("a_share") and any(w in hint_l for w in HINTS["SS"] + HINTS["SZ"] + ("a股", "a-share")):
        want = links["a_share"]
    if want:
        switched = _with_listing(_result(raw, want, res["confidence"], f"{res['reason']}; switched to the hinted cross-listing"), uni)
        return switched
    return res


def _normalize(raw: str, aliases: dict[str, dict[str, Any]], hint: str = "") -> dict[str, Any]:
    inp = raw
    text = raw.strip()
    hint_l = (hint + " " + text).lower()
    m = re.search(r"\((\d{4,6})\)", text) or re.search(r"\b(\d{4,6})\b", text)
    name_part = re.sub(r"\(.*?\)", "", text).strip().lstrip("$")
    # 1) explicit suffix
    sm = re.fullmatch(r"\$?([A-Za-z0-9\-]{1,12})\.([A-Za-z]{1,3})", text)
    if sm and sm.group(2).upper() in SUFFIX_INFO:
        return _result(inp, f"{sm.group(1).upper()}.{sm.group(2).upper()}", 0.95, "explicit exchange suffix")
    # 2) alias table (name, cashtag, or base symbol)
    for key in (_norm(name_part), _norm(text.lstrip("$"))):
        row = aliases.get(key)
        if row:
            res = _result(inp, row["symbol"], 0.9, "alias table")
            if row.get("exchange"):
                res["exchange"] = row["exchange"]
            return res
    uni = universe()
    # 3) numeric listing code
    if m:
        code = m.group(1)
        cands = numeric_candidates(code)
        korea = any(w in hint_l for w in HINTS["KS"] + HINTS["KQ"])
        if len(code) == 6 and code in uni.cn and not korea:
            return _result(inp, uni.cn[code][0], 0.9, f"A-share code in CNINFO list ({uni.as_of.get('cn')}); Korea uses 6 digits too", cands)
        hk_key = f"{int(code):04d}" if len(code) in (4, 5) else None
        taiwan_or_japan = any(w in hint_l for w in HINTS["TW"] + HINTS["TWO"] + HINTS["T"])
        if hk_key and hk_key in uni.hk and (len(code) == 5 or (code.startswith("0") and not taiwan_or_japan)):
            return _result(inp, uni.hk[hk_key][0], 0.9 if len(code) == 5 else 0.85,
                           f"HKEX active list ({uni.as_of.get('hk')})", cands)
        for suffix, words in HINTS.items():
            if any(w in hint_l for w in words):
                pref = [c for c in cands if c.endswith("." + suffix)]
                if pref:
                    return _result(inp, pref[0], 0.85, f"numeric code + market hint {suffix}", cands)
        if len(code) == 6 and code.startswith(("60", "68")):
            return _result(inp, f"{code}.SS", 0.6, "6-digit code: Shanghai most likely, Korea possible", cands)
        return _result(inp, None, 0.0, "ambiguous numeric code; verify exchange", cands)
    # 4) bare US-style cashtag
    if re.fullmatch(r"\$?[A-Za-z]{1,5}(?:-[A-Za-z])?", text):
        sym = text.lstrip("$").upper()
        if sym in uni.us:
            return _result(inp, sym, 0.9, f"SEC ticker map ({uni.as_of.get('us')})")
        if re.fullmatch(r"\$?[A-Za-z]{1,5}", text):
            conf = 0.85 if text.startswith("$") else 0.7
            return _result(inp, sym, conf, "US-style symbol; foreign listings with the same code must be checked")
    # 5) company name in the listing universe (simplified / traditional / English)
    matches, how = uni.name_matches(name_part or text)
    if matches:
        if len(matches) == 1:
            conf = {"exact": 0.9, "prefix": 0.8}.get(how, 0.75)
            return _result(inp, matches[0][0], conf, f"listing universe name match ({how})")
        line = _pick_line(matches, hint_l)
        if line:
            return _result(inp, line[0], 0.85 if how == "exact" else 0.75,
                           f"listing universe name match ({how}); same company has other lines", [m[0] for m in matches])
        return _result(inp, None, 0.0, f"several listings match the name ({how}); pick one",
                       [f"{m[0]} {m[1]}" for m in matches])
    return _result(inp, None, 0.0, "unresolved name; add to local alias overlay after verification")


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("inputs", nargs="+")
    p.add_argument("--hint", default="", help="market hint, e.g. Korea, Taiwan, 港股")
    p.add_argument("--aliases", type=Path, action="append", default=[],
                   help="additional local alias overlay JSON (same shape as the seed)")
    args = p.parse_args(argv)
    table = load_aliases([*args.aliases, SEED_PATH])
    for raw in args.inputs:
        print(json.dumps(normalize(raw, table, args.hint), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
