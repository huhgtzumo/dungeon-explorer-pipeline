"""Seed KB batch 2: Fill narrative_clues to 30 and ambient_triggers to 40.

Run: python -m scripts.seed_kb_batch2
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime
from pathlib import Path

KB_ROOT = Path(__file__).resolve().parent.parent / "data" / "knowledge"

ADDITIONAL_ENTRIES: dict[str, list[dict]] = {
    # ── narrative_clues: 15 more (currently 15, target 30) ──
    "narrative_clues": [
        {"name": "牆上塗鴉", "name_en": "Wall Graffiti",
         "description": "潦草的字跡寫著警告或求救信息，有些被人刻意塗抹覆蓋。",
         "tags": ["文字", "警告", "線索"], "effectiveness_score": 7},
        {"name": "密碼鎖提示", "name_en": "Combination Lock Hint",
         "description": "散落在不同房間的數字碎片，拼湊起來可能是某個密碼鎖的組合。",
         "tags": ["密碼", "解謎", "互動"], "effectiveness_score": 8},
        {"name": "實驗記錄表", "name_en": "Experiment Log Sheet",
         "description": "記載異常數據的實驗表格，受試者欄位的名字被用黑色墨水塗掉。",
         "tags": ["實驗", "文件", "機密"], "effectiveness_score": 9},
        {"name": "保全巡邏日誌", "name_en": "Security Patrol Log",
         "description": "保全人員的巡邏記錄，最後幾頁的字跡越來越潦草，最終戛然而止。",
         "tags": ["保全", "日誌", "異常"], "effectiveness_score": 8},
        {"name": "失蹤者遺物", "name_en": "Missing Person's Belongings",
         "description": "背包、手機、鑰匙散落在地，主人卻不見蹤影。",
         "tags": ["失蹤", "遺物", "懸疑"], "effectiveness_score": 9},
        {"name": "倒數刻痕", "name_en": "Countdown Tally Marks",
         "description": "牆上用指甲或銳器刻下的正字計數，從某天開始突然停止。",
         "tags": ["計數", "囚禁", "時間"], "effectiveness_score": 8},
        {"name": "被撕毀的藍圖", "name_en": "Torn Blueprint",
         "description": "建築藍圖被人故意撕碎，拼起來發現有一層未標示的地下結構。",
         "tags": ["藍圖", "建築", "隱藏"], "effectiveness_score": 8},
        {"name": "血跡指引", "name_en": "Blood Trail Guide",
         "description": "乾涸的血跡形成一條路線，像是有人在引導或被拖行。",
         "tags": ["血跡", "路線", "驚悚"], "effectiveness_score": 9},
        {"name": "兒童塗鴉日記", "name_en": "Child's Crayon Diary",
         "description": "用蠟筆畫的日記本，畫面從快樂的家庭逐漸變成黑暗壓抑的場景。",
         "tags": ["兒童", "日記", "心理"], "effectiveness_score": 8},
        {"name": "地圖上的標記", "name_en": "Map Markings",
         "description": "一張手繪地圖，標記出幾個位置並用紅筆畫了大叉。",
         "tags": ["地圖", "標記", "路線"], "effectiveness_score": 7},
        {"name": "錄影帶殘片", "name_en": "VHS Tape Fragment",
         "description": "損壞的錄影帶，勉強播放出模糊的畫面和扭曲的音訊。",
         "tags": ["錄影", "影像", "殘片"], "effectiveness_score": 8},
        {"name": "員工證件", "name_en": "Employee ID Badge",
         "description": "遺落的員工證件，照片已褪色，但姓名和部門仍可辨認。",
         "tags": ["證件", "身份", "線索"], "effectiveness_score": 6},
        {"name": "求救字條", "name_en": "Distress Note",
         "description": "摺疊塞在縫隙中的紙條，寫著不要相信某人或不要打開某扇門。",
         "tags": ["求救", "警告", "紙條"], "effectiveness_score": 8},
        {"name": "異常溫度計", "name_en": "Anomalous Thermometer",
         "description": "牆上的溫度計顯示不可能的讀數，或在不同房間呈現極端差異。",
         "tags": ["溫度", "異常", "科學"], "effectiveness_score": 7},
        {"name": "未寄出的信件", "name_en": "Unsent Letters",
         "description": "成疊未寄出的信件，內容從日常問候逐漸變成偏執妄想的記錄。",
         "tags": ["信件", "心理", "記錄"], "effectiveness_score": 8},
    ],

    # ── ambient_triggers: 20 more (currently 20, target 40) ──
    "ambient_triggers": [
        {"name": "腳步聲回音", "name_en": "Footstep Echo",
         "description": "自己的腳步在空曠走廊中產生延遲回音，有時回音的節奏似乎不太對。",
         "tags": ["聲音", "回音", "心理"], "effectiveness_score": 8},
        {"name": "電話鈴聲", "name_en": "Phone Ringing",
         "description": "廢棄建築中突然響起的電話鈴聲，接起來只有雜訊。",
         "tags": ["聲音", "電話", "突發"], "effectiveness_score": 9},
        {"name": "牆壁滲水", "name_en": "Wall Seepage",
         "description": "牆面不明液體緩慢滲出，顏色在手電筒下呈現詭異的暗紅色。",
         "tags": ["視覺", "水", "氛圍"], "effectiveness_score": 7},
        {"name": "電梯自動開關", "name_en": "Elevator Auto Open-Close",
         "description": "停用的電梯突然自行開門關門，金屬摩擦聲在樓道迴盪。",
         "tags": ["機械", "電梯", "異常"], "effectiveness_score": 9},
        {"name": "呼吸般的氣流", "name_en": "Breathing-like Airflow",
         "description": "通風管道傳來有節奏的氣流，像是某種巨大生物在呼吸。",
         "tags": ["空氣", "聲音", "心理"], "effectiveness_score": 8},
        {"name": "突然的寂靜", "name_en": "Sudden Silence",
         "description": "所有環境音瞬間消失，連蟲鳴和風聲都停止了。",
         "tags": ["寂靜", "反差", "心理"], "effectiveness_score": 9},
        {"name": "鏡面反射異常", "name_en": "Mirror Reflection Anomaly",
         "description": "破碎鏡面中的倒影似乎有微妙的延遲，或角度不太正確。",
         "tags": ["視覺", "鏡子", "異常"], "effectiveness_score": 9},
        {"name": "溫度驟降", "name_en": "Sudden Temperature Drop",
         "description": "進入特定區域時體感溫度急劇下降，呼出的氣息凝成白霧。",
         "tags": ["溫度", "體感", "環境"], "effectiveness_score": 8},
        {"name": "油漆剝落聲", "name_en": "Paint Peeling Sound",
         "description": "牆面油漆大片剝落，發出細碎的撕裂聲，露出底下的塗鴉。",
         "tags": ["聲音", "視覺", "衰敗"], "effectiveness_score": 6},
        {"name": "無線電雜訊", "name_en": "Radio Static",
         "description": "對講機突然收到斷斷續續的雜訊，偶爾似乎混雜著人聲片段。",
         "tags": ["聲音", "通訊", "異常"], "effectiveness_score": 8},
        {"name": "影子移動", "name_en": "Shadow Movement",
         "description": "手電筒照不到的角落，影子似乎獨立於光源在移動。",
         "tags": ["視覺", "影子", "驚悚"], "effectiveness_score": 9},
        {"name": "地板震動", "name_en": "Floor Vibration",
         "description": "腳下傳來低頻震動，像是地底有重型機械在運轉。",
         "tags": ["觸覺", "震動", "地下"], "effectiveness_score": 7},
        {"name": "異味飄散", "name_en": "Strange Odor Wafting",
         "description": "時有時無的化學藥劑氣味，混合著潮濕腐朽的味道。",
         "tags": ["嗅覺", "化學", "環境"], "effectiveness_score": 6},
        {"name": "自動門感應", "name_en": "Auto Door Sensor Trigger",
         "description": "損壞的自動門突然感應到什麼而開啟，但目視範圍內空無一人。",
         "tags": ["機械", "門", "異常"], "effectiveness_score": 8},
        {"name": "水龍頭自轉", "name_en": "Faucet Self-Turn",
         "description": "廢棄洗手間的水龍頭突然打開，流出鏽紅色的水。",
         "tags": ["水", "機械", "突發"], "effectiveness_score": 7},
        {"name": "塵埃光柱", "name_en": "Dust Light Beam",
         "description": "月光或手電筒穿過縫隙形成光柱，大量灰塵在其中漂浮翻騰。",
         "tags": ["視覺", "光線", "氛圍"], "effectiveness_score": 7},
        {"name": "鐵鏈拖曳聲", "name_en": "Chain Dragging Sound",
         "description": "遠處傳來金屬鏈條在地面拖行的聲音，時近時遠。",
         "tags": ["聲音", "金屬", "驚悚"], "effectiveness_score": 9},
        {"name": "日光燈殘響", "name_en": "Fluorescent Light Buzzing",
         "description": "破損的日光燈管發出間歇性的嗡嗡聲和微弱閃爍。",
         "tags": ["聲音", "光線", "衰敗"], "effectiveness_score": 7},
        {"name": "紙張翻動", "name_en": "Papers Rustling",
         "description": "沒有明顯風源，桌上散落的文件卻緩慢翻動。",
         "tags": ["聲音", "紙張", "異常"], "effectiveness_score": 7},
        {"name": "EMF讀數飆升", "name_en": "EMF Spike",
         "description": "電磁場偵測器突然發出急促的警報聲，讀數瞬間衝到紅區。",
         "tags": ["設備", "電磁", "偵測"], "effectiveness_score": 8},
    ],
}


def _generate_id(category: str) -> str:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    rand = uuid.uuid4().hex[:6]
    return f"kb_{category}_{ts}_{rand}"


def main():
    now = datetime.now().isoformat()
    total = 0

    for category, items in ADDITIONAL_ENTRIES.items():
        cat_dir = KB_ROOT / category
        cat_dir.mkdir(parents=True, exist_ok=True)

        for item in items:
            entry_id = _generate_id(category)
            entry = {
                "id": entry_id,
                "category": category,
                "subcategory": item.get("subcategory", ""),
                "name": item["name"],
                "name_en": item["name_en"],
                "description": item["description"],
                "tags": item["tags"],
                "examples": [],
                "effectiveness_score": item.get("effectiveness_score", 5),
                "usage_count": 0,
                "created_at": now,
                "updated_at": now,
            }
            path = cat_dir / f"{entry_id}.json"
            path.write_text(json.dumps(entry, ensure_ascii=False, indent=2), encoding="utf-8")
            total += 1
            print(f"  + {category}/{entry_id}: {item['name']}")

    print(f"\nDone: {total} entries added")


if __name__ == "__main__":
    main()
