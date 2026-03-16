#!/usr/bin/env python3
"""Seed the exploration knowledge base with initial elements for all 15 categories."""

import json
import os
import sys
import uuid
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
KB_ROOT = PROJECT_ROOT / "data" / "knowledge"
KB_INDEX_PATH = KB_ROOT / "kb_index.json"

def gen_id(category: str) -> str:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    rand = uuid.uuid4().hex[:6]
    return f"kb_{category}_{ts}_{rand}"

def save_entry(category: str, data: dict) -> dict:
    cat_dir = KB_ROOT / category
    cat_dir.mkdir(parents=True, exist_ok=True)

    entry_id = gen_id(category)
    now = datetime.now().isoformat()
    entry = {
        "id": entry_id,
        "category": category,
        "subcategory": data.get("subcategory", ""),
        "name": data["name"],
        "name_en": data.get("name_en", ""),
        "description": data.get("description", ""),
        "tags": data.get("tags", []),
        "examples": data.get("examples", []),
        "effectiveness_score": data.get("effectiveness_score", 5),
        "usage_count": 0,
        "created_at": now,
        "updated_at": now,
    }

    path = cat_dir / f"{entry_id}.json"
    path.write_text(json.dumps(entry, ensure_ascii=False, indent=2), encoding="utf-8")
    return entry

# ═══════════════════════════════════════════════
# SEED DATA - 15 Categories
# ═══════════════════════════════════════════════

SEED = {
    # ─── 場景層 (Scene Layer) ───
    "building_types": [
        {"name": "廢棄精神病院", "name_en": "Abandoned Asylum", "subcategory": "醫療設施", "description": "荒廢的精神療養院，走廊回蕩著過去的低語。病房門半開，鐵床上的束縛帶鏽跡斑斑。", "tags": ["恐怖", "醫療", "經典"], "effectiveness_score": 9},
        {"name": "廢棄醫院", "name_en": "Abandoned Hospital", "subcategory": "醫療設施", "description": "停業多年的綜合醫院，手術室的無影燈歪斜，急診室的推車散落一地。", "tags": ["醫療", "城市", "常見"], "effectiveness_score": 8},
        {"name": "蘇聯地下碉堡", "name_en": "Soviet Underground Bunker", "subcategory": "軍事設施", "description": "冷戰時期的地下防核掩體，厚重的鐵門後是迷宮般的走廊和指揮中心。", "tags": ["軍事", "地下", "冷戰"], "effectiveness_score": 9},
        {"name": "廢棄軍營", "name_en": "Abandoned Military Barracks", "subcategory": "軍事設施", "description": "被遺棄的軍事營區，營房整齊排列卻空無一人，操場上野草叢生。", "tags": ["軍事", "戶外", "大型"], "effectiveness_score": 7},
        {"name": "荒廢學校", "name_en": "Abandoned School", "subcategory": "教育設施", "description": "空蕩的教室裡課桌椅依然排列，黑板上殘留最後一堂課的板書。", "tags": ["教育", "懷舊", "日常"], "effectiveness_score": 7},
        {"name": "廢棄大學", "name_en": "Abandoned University", "subcategory": "教育設施", "description": "關閉的大學校園，圖書館書架傾倒，實驗室的燒杯積了一層灰。", "tags": ["教育", "大型", "學術"], "effectiveness_score": 7},
        {"name": "廢棄工廠", "name_en": "Abandoned Factory", "subcategory": "工業設施", "description": "停產的重工業工廠，巨大的機械設備如鋼鐵巨獸沉默矗立，地面油漬斑駁。", "tags": ["工業", "大型", "機械"], "effectiveness_score": 8},
        {"name": "廢棄發電廠", "name_en": "Abandoned Power Plant", "subcategory": "工業設施", "description": "停運的火力發電廠，冷卻塔如巨大的空心圓柱，控制室的儀表全部歸零。", "tags": ["工業", "能源", "壯觀"], "effectiveness_score": 8},
        {"name": "廢棄礦坑", "name_en": "Abandoned Mine", "subcategory": "工業設施", "description": "封閉的地下礦坑，支撐木柱搖搖欲墜，礦車軌道消失在無盡的黑暗中。", "tags": ["地下", "危險", "幽閉"], "effectiveness_score": 9},
        {"name": "廢棄教堂", "name_en": "Abandoned Church", "subcategory": "宗教設施", "description": "荒廢的教堂，彩色玻璃窗破碎，聖壇上佈滿灰塵，管風琴的管子生鏽彎曲。", "tags": ["宗教", "哥德", "神聖"], "effectiveness_score": 8},
        {"name": "廢棄神社", "name_en": "Abandoned Shrine", "subcategory": "宗教設施", "description": "隱沒在山林中的荒廢神社，鳥居傾斜，石燈籠被藤蔓纏繞。", "tags": ["宗教", "日式", "自然"], "effectiveness_score": 7},
        {"name": "廢棄豪宅", "name_en": "Abandoned Mansion", "subcategory": "居住設施", "description": "曾經輝煌的大宅，水晶吊燈蒙塵，壁爐前的扶手椅覆蓋著白布。", "tags": ["居住", "豪華", "鬼屋"], "effectiveness_score": 8},
        {"name": "廢棄公寓大樓", "name_en": "Abandoned Apartment Block", "subcategory": "居住設施", "description": "被迫遷離的大型公寓，每扇門後都是一個被凍結的生活場景。", "tags": ["居住", "城市", "多層"], "effectiveness_score": 7},
        {"name": "地下防空洞", "name_en": "Underground Air Raid Shelter", "subcategory": "地下設施", "description": "二戰時期的民用防空洞，狹窄的階梯通往陰暗潮濕的避難空間。", "tags": ["地下", "戰爭", "歷史"], "effectiveness_score": 8},
        {"name": "廢棄地鐵站", "name_en": "Abandoned Subway Station", "subcategory": "地下設施", "description": "被關閉的地鐵站，月台空無一人，隧道深處偶爾傳來氣流的呼嘯。", "tags": ["地下", "城市", "交通"], "effectiveness_score": 8},
        {"name": "廢棄下水道系統", "name_en": "Abandoned Sewer System", "subcategory": "地下設施", "description": "城市地下的舊排水系統，拱形磚牆回聲重重，水聲和不明聲響交織。", "tags": ["地下", "城市", "潮濕"], "effectiveness_score": 7},
        {"name": "廢棄監獄", "name_en": "Abandoned Prison", "subcategory": "公共設施", "description": "關閉的監獄設施，牢房鐵門鏽蝕，放風場雜草蔓生，瞭望塔空無一人。", "tags": ["公共", "壓迫", "暴力"], "effectiveness_score": 9},
        {"name": "廢棄游泳池", "name_en": "Abandoned Swimming Pool", "subcategory": "公共設施", "description": "乾涸的公共游泳池，瓷磚破裂脫落，更衣室的置物櫃門敞開。", "tags": ["公共", "運動", "詭異"], "effectiveness_score": 6},
        {"name": "廢棄遊樂園", "name_en": "Abandoned Amusement Park", "subcategory": "公共設施", "description": "關閉的遊樂園，摩天輪靜止不動，旋轉木馬的馬匹掉漆斑駁。", "tags": ["公共", "娛樂", "反差"], "effectiveness_score": 9},
        {"name": "廢棄戲院", "name_en": "Abandoned Theater", "subcategory": "公共設施", "description": "關閉的老戲院，紅色天鵝絨座椅蒙塵，舞台布幕半拉半垂。", "tags": ["公共", "藝術", "華麗"], "effectiveness_score": 7},
        {"name": "廢棄實驗室", "name_en": "Abandoned Laboratory", "subcategory": "其他", "description": "不明機構的研究實驗室，試管架上殘留不明液體，白板上的方程式無人能解。", "tags": ["科學", "神秘", "危險"], "effectiveness_score": 9},
        {"name": "廢棄水壩", "name_en": "Abandoned Dam", "subcategory": "其他", "description": "停止運作的水壩設施，閘門鏽蝕，控制室的儀表板佈滿蜘蛛網。", "tags": ["水利", "壯觀", "戶外"], "effectiveness_score": 7},
        {"name": "廢棄船塢", "name_en": "Abandoned Shipyard", "subcategory": "其他", "description": "廢棄的造船廠，巨大的船架空空如也，起重機的吊臂指向灰暗的天空。", "tags": ["港口", "工業", "大型"], "effectiveness_score": 7},
        {"name": "切爾諾貝利隔離區", "name_en": "Chernobyl Exclusion Zone", "subcategory": "其他", "description": "核災後被永久隔離的城鎮，時間凍結在1986年，大自然正在收復失地。", "tags": ["核災", "傳奇", "輻射"], "effectiveness_score": 10},
        {"name": "廢棄旅館", "name_en": "Abandoned Hotel", "subcategory": "居住設施", "description": "停業的大型旅館，大廳的水晶燈搖搖欲墜，客房鑰匙整齊掛在櫃台後方。", "tags": ["居住", "商業", "閃靈"], "effectiveness_score": 8},
        {"name": "廢棄療養院", "name_en": "Abandoned Sanatorium", "subcategory": "醫療設施", "description": "山上的結核病療養院，長廊的盡頭是大片落地窗，病床朝向已經看不見的風景。", "tags": ["醫療", "山區", "歷史"], "effectiveness_score": 8},
        {"name": "廢棄太平間", "name_en": "Abandoned Morgue", "subcategory": "醫療設施", "description": "醫院地下室的太平間，不鏽鋼抽屜半開，冷藏室的壓縮機早已停止運轉。", "tags": ["醫療", "恐怖", "地下"], "effectiveness_score": 9},
        {"name": "廢棄地下實驗設施", "name_en": "Underground Research Facility", "subcategory": "地下設施", "description": "政府機密研究所的地下層，需要多重密碼的鐵門後是未知的實驗空間。", "tags": ["地下", "政府", "機密"], "effectiveness_score": 9},
        {"name": "廢棄火車站", "name_en": "Abandoned Train Station", "subcategory": "公共設施", "description": "停用的鐵路車站，月台上的時刻表停在最後一班車的時間。", "tags": ["交通", "懷舊", "開放"], "effectiveness_score": 7},
        {"name": "廢棄購物中心", "name_en": "Abandoned Shopping Mall", "subcategory": "公共設施", "description": "倒閉的大型商場，自動手扶梯停止運轉，店鋪招牌七零八落。", "tags": ["商業", "大型", "消費"], "effectiveness_score": 8},
    ],

    "building_backstories": [
        {"name": "神秘火災", "name_en": "Mysterious Fire", "description": "一場原因不明的大火導致建築被廢棄，調查報告被列為機密。殘存的焦痕暗示火勢不自然。", "tags": ["火災", "神秘", "調查"], "effectiveness_score": 8},
        {"name": "連環失蹤", "name_en": "Serial Disappearances", "description": "多名工作人員和訪客在此失蹤，搜索無果後當局下令封鎖。失蹤者至今下落不明。", "tags": ["失蹤", "恐怖", "未解"], "effectiveness_score": 9},
        {"name": "瘟疫爆發", "name_en": "Plague Outbreak", "description": "一場不明傳染病從這裡爆發，所有人被緊急撤離，建築被永久隔離消毒。", "tags": ["疾病", "隔離", "生物"], "effectiveness_score": 8},
        {"name": "實驗失控", "name_en": "Experiment Gone Wrong", "description": "秘密實驗發生嚴重事故，倖存者拒絕透露細節，所有研究資料被銷毀。", "tags": ["實驗", "科學", "政府"], "effectiveness_score": 9},
        {"name": "兇殺案", "name_en": "Murder Case", "description": "這裡發生過駭人聽聞的兇殺案件，輿論壓力下建築被關閉，再也沒人願意靠近。", "tags": ["犯罪", "暴力", "詛咒"], "effectiveness_score": 8},
        {"name": "政府封鎖", "name_en": "Government Lockdown", "description": "政府以國家安全為由下令封鎖，沒有給出任何解釋。附近居民被強制搬遷。", "tags": ["政府", "機密", "陰謀"], "effectiveness_score": 8},
        {"name": "自然災害", "name_en": "Natural Disaster", "description": "地震/颱風/洪水造成嚴重結構損壞，被判定為危樓後遭到廢棄。", "tags": ["災害", "結構", "天災"], "effectiveness_score": 6},
        {"name": "經營破產", "name_en": "Bankruptcy", "description": "經營者突然破產跑路，員工一夜之間消失，留下所有物品原封不動。", "tags": ["經濟", "日常", "突然"], "effectiveness_score": 6},
        {"name": "核洩漏", "name_en": "Nuclear Leak", "description": "附近核設施發生洩漏事故，整個區域被劃為禁區，居民永久撤離。", "tags": ["核災", "輻射", "永久"], "effectiveness_score": 9},
        {"name": "邪教活動", "name_en": "Cult Activity", "description": "發現有邪教組織在此進行儀式活動後，警方突擊搜查並永久封閉此地。", "tags": ["邪教", "儀式", "犯罪"], "effectiveness_score": 9},
        {"name": "結構老化", "name_en": "Structural Decay", "description": "年久失修導致建築結構嚴重劣化，被工程師判定為隨時可能坍塌的危樓。", "tags": ["老化", "危險", "時間"], "effectiveness_score": 5},
        {"name": "戰爭遺留", "name_en": "War Remnant", "description": "戰爭結束後被遺棄的軍事設施或平民建築，牆上彈痕累累。", "tags": ["戰爭", "歷史", "軍事"], "effectiveness_score": 7},
        {"name": "集體自殺", "name_en": "Mass Suicide", "description": "一群人在此地集體結束生命，事件震驚社會。此後無人敢踏入，成為禁忌之地。", "tags": ["死亡", "禁忌", "心理"], "effectiveness_score": 8},
        {"name": "毒氣外洩", "name_en": "Toxic Gas Leak", "description": "地下管線的有毒氣體外洩事件導致多人中毒，建築被緊急封鎖且從未重新開放。", "tags": ["化學", "危險", "工業"], "effectiveness_score": 7},
        {"name": "都市更新失敗", "name_en": "Failed Urban Renewal", "description": "都更計劃中途擱置，居民已搬走但新建設從未開始，留下一片荒涼。", "tags": ["城市", "政策", "經濟"], "effectiveness_score": 5},
        {"name": "鬧鬼傳說", "name_en": "Haunting Legend", "description": "多次有人目擊超自然現象後，口耳相傳的鬧鬼傳說讓所有租戶搬離。", "tags": ["超自然", "傳說", "恐怖"], "effectiveness_score": 8},
        {"name": "醫療醜聞", "name_en": "Medical Scandal", "description": "曝光非法人體實驗或醫療疏失醜聞，媒體風暴下被迫關閉並接受調查。", "tags": ["醫療", "醜聞", "犯罪"], "effectiveness_score": 8},
        {"name": "洪水淹沒", "name_en": "Flood Submersion", "description": "反覆遭受洪水侵襲，地下層永久積水，上層結構因水損而不堪使用。", "tags": ["洪水", "水害", "反覆"], "effectiveness_score": 7},
        {"name": "輻射汙染", "name_en": "Radiation Contamination", "description": "在建築內發現異常輻射值，來源不明，環保單位下令永久封鎖。", "tags": ["輻射", "神秘", "汙染"], "effectiveness_score": 8},
        {"name": "產權糾紛", "name_en": "Property Dispute", "description": "複雜的繼承權訴訟持續數十年，期間無人維護，建築逐漸傾頹。", "tags": ["法律", "時間", "日常"], "effectiveness_score": 4},
    ],

    "exploration_zones": [
        {"name": "陰暗走廊", "name_en": "Dark Corridor", "subcategory": "走廊通道", "description": "幾乎沒有自然光的長走廊，手電筒照出牆上的水漬和剝落的油漆。", "tags": ["基本", "連接", "壓迫"], "effectiveness_score": 7},
        {"name": "緊急逃生通道", "name_en": "Emergency Escape Route", "subcategory": "走廊通道", "description": "狹窄的逃生樓梯間，鐵欄杆鏽蝕，每一步都發出金屬顫鳴。", "tags": ["狹窄", "垂直", "金屬"], "effectiveness_score": 7},
        {"name": "通風管道", "name_en": "Ventilation Duct", "subcategory": "走廊通道", "description": "勉強容一人爬行的通風管道，金屬壁面放大每一個聲響。", "tags": ["幽閉", "爬行", "金屬"], "effectiveness_score": 8},
        {"name": "地下隧道", "name_en": "Underground Tunnel", "subcategory": "走廊通道", "description": "連接不同區域的地下通道，牆壁滲水，地面積水沒過腳踝。", "tags": ["地下", "潮濕", "連接"], "effectiveness_score": 8},
        {"name": "手術室", "name_en": "Operating Room", "subcategory": "功能房間", "description": "塵封的手術室，無影燈歪斜照向空蕩的手術台，器械托盤上的工具鏽跡斑斑。", "tags": ["醫療", "恐怖", "器具"], "effectiveness_score": 9},
        {"name": "檔案室", "name_en": "Archive Room", "subcategory": "功能房間", "description": "堆滿文件和檔案的房間，金屬櫃子排列成迷宮，地上散落著泛黃的紙張。", "tags": ["文件", "線索", "搜索"], "effectiveness_score": 7},
        {"name": "控制室", "name_en": "Control Room", "subcategory": "功能房間", "description": "滿牆的監控螢幕和操作面板，有些儀表的指針還停在最後的讀數上。", "tags": ["科技", "監控", "核心"], "effectiveness_score": 8},
        {"name": "廚房/食堂", "name_en": "Kitchen/Cafeteria", "subcategory": "功能房間", "description": "大型廚房設備生鏽，冰箱門敞開，餐桌上還擺著上一餐的餐盤。", "tags": ["日常", "食物", "生活"], "effectiveness_score": 6},
        {"name": "實驗室", "name_en": "Laboratory", "subcategory": "功能房間", "description": "白色瓷磚牆面的實驗室，試管架上殘留不明液體，通風櫃的玻璃碎裂。", "tags": ["科學", "化學", "危險"], "effectiveness_score": 8},
        {"name": "病房", "name_en": "Patient Ward", "subcategory": "功能房間", "description": "排列著鐵製病床的病房，窗簾在穿堂風中輕搖，床頭櫃的抽屜裡留有私人物品。", "tags": ["醫療", "個人", "悲傷"], "effectiveness_score": 7},
        {"name": "地下室", "name_en": "Basement", "subcategory": "地下空間", "description": "潮濕陰暗的地下室，天花板管線滴水，牆角堆著用途不明的木箱。", "tags": ["地下", "潮濕", "未知"], "effectiveness_score": 8},
        {"name": "鍋爐房", "name_en": "Boiler Room", "subcategory": "地下空間", "description": "巨大的鍋爐如沉睡的怪獸，管線錯綜複雜，空氣中殘留著機油的氣味。", "tags": ["工業", "機械", "悶熱"], "effectiveness_score": 8},
        {"name": "地下儲水池", "name_en": "Underground Cistern", "subcategory": "地下空間", "description": "巨大的地下蓄水空間，拱形石柱倒映在漆黑的水面上。", "tags": ["地下", "水域", "壯觀"], "effectiveness_score": 8},
        {"name": "密室", "name_en": "Hidden Room", "subcategory": "特殊區域", "description": "隱藏在牆壁後的秘密房間，只有通過特定機關才能進入。", "tags": ["隱藏", "發現", "機關"], "effectiveness_score": 9},
        {"name": "隔離區", "name_en": "Quarantine Zone", "subcategory": "特殊區域", "description": "用塑膠布和警告標誌封鎖的區域，透過破損處可以看到裡面散落的醫療廢棄物。", "tags": ["醫療", "危險", "封鎖"], "effectiveness_score": 8},
        {"name": "監控中心", "name_en": "Surveillance Center", "subcategory": "特殊區域", "description": "佈滿監控螢幕的房間，部分螢幕還在閃爍雪花，錄影帶散落一地。", "tags": ["監控", "科技", "窺視"], "effectiveness_score": 8},
        {"name": "停屍間", "name_en": "Morgue", "subcategory": "特殊區域", "description": "冰冷的不鏽鋼空間，屍體冷藏櫃的把手磨損，排水溝有不明暗色痕跡。", "tags": ["死亡", "恐怖", "冰冷"], "effectiveness_score": 9},
        {"name": "屋頂", "name_en": "Rooftop", "subcategory": "頂層空間", "description": "風很大的屋頂，可以俯瞰周圍的荒涼景象，邊緣沒有護欄。", "tags": ["高處", "開闊", "危險"], "effectiveness_score": 7},
        {"name": "鐘塔", "name_en": "Bell Tower", "subcategory": "頂層空間", "description": "螺旋樓梯通往的鐘塔頂端，巨大的銅鐘早已不再敲響。", "tags": ["高處", "垂直", "標誌"], "effectiveness_score": 7},
        {"name": "電梯井", "name_en": "Elevator Shaft", "subcategory": "其他", "description": "打開的電梯門後是漆黑的深淵，鋼纜在黑暗中輕微晃動。", "tags": ["垂直", "危險", "深淵"], "effectiveness_score": 8},
        {"name": "禮拜堂", "name_en": "Chapel", "subcategory": "特殊區域", "description": "建築內的小型禮拜堂，彩繪玻璃投射出昏暗的彩色光影，長椅上放著打開的聖經。", "tags": ["宗教", "靜謐", "神聖"], "effectiveness_score": 7},
        {"name": "洗衣房", "name_en": "Laundry Room", "subcategory": "功能房間", "description": "大型工業洗衣機排列成行，地上散落著發霉的衣物和床單。", "tags": ["日常", "潮濕", "氣味"], "effectiveness_score": 6},
        {"name": "彈藥庫", "name_en": "Ammunition Storage", "subcategory": "特殊區域", "description": "厚重防爆門後的彈藥庫，金屬架上空空如也，但角落似乎還有遺漏的東西。", "tags": ["軍事", "危險", "封鎖"], "effectiveness_score": 8},
        {"name": "游泳池區", "name_en": "Pool Area", "subcategory": "其他", "description": "乾涸的泳池底部裂開，更衣室的鏡子碎裂，瓷磚上長滿青苔。", "tags": ["水域", "空間", "詭異"], "effectiveness_score": 7},
        {"name": "地下停車場", "name_en": "Underground Parking", "subcategory": "地下空間", "description": "昏暗的地下停車場，螢光燈管閃爍，幾輛被遺棄的車輛靜靜矗立。", "tags": ["地下", "車輛", "開闊"], "effectiveness_score": 7},
    ],

    "route_paths": [
        {"name": "正門突入", "name_en": "Front Door Entry", "description": "從正門進入，門鎖已被破壞，推開沉重的大門，灰塵在光柱中飛舞。", "tags": ["正面", "基本", "大膽"], "effectiveness_score": 6},
        {"name": "窗戶翻入", "name_en": "Window Climb", "description": "從破碎的窗戶攀爬進入，玻璃碎片在手電筒下閃爍，落地時揚起一陣灰塵。", "tags": ["攀爬", "碎玻璃", "隱蔽"], "effectiveness_score": 7},
        {"name": "地下通道", "name_en": "Underground Passage", "description": "通過建築外的地下入口進入，潮濕的台階向下延伸到黑暗中。", "tags": ["地下", "隱蔽", "潮濕"], "effectiveness_score": 8},
        {"name": "屋頂垂降", "name_en": "Rooftop Rappel", "description": "從相鄰建築跳上屋頂，然後通過天井或樓梯間向下探索。", "tags": ["高處", "動作", "刺激"], "effectiveness_score": 8},
        {"name": "排水管道", "name_en": "Drainage Pipe", "description": "從建築外的大型排水管爬入，膝蓋浸在淺水中，空間越來越窄。", "tags": ["幽閉", "潮濕", "管道"], "effectiveness_score": 8},
        {"name": "貨物入口", "name_en": "Loading Dock", "description": "從後方的貨物裝卸區進入，鐵捲門半開，卡車停靠台已經荒廢。", "tags": ["後方", "工業", "大型"], "effectiveness_score": 6},
        {"name": "消防梯", "name_en": "Fire Escape", "description": "從外牆的消防逃生梯攀上，鏽蝕的金屬階梯發出令人不安的聲響。", "tags": ["攀爬", "外牆", "金屬"], "effectiveness_score": 7},
        {"name": "圍牆缺口", "name_en": "Wall Breach", "description": "從圍牆倒塌處的缺口潛入園區，穿過荒草叢生的庭院接近建築。", "tags": ["戶外", "隱蔽", "接近"], "effectiveness_score": 6},
        {"name": "通風口", "name_en": "Ventilation Opening", "description": "拆開外牆的大型通風口格柵，勉強擠入通風管道系統。", "tags": ["幽閉", "管道", "困難"], "effectiveness_score": 8},
        {"name": "水路進入", "name_en": "Waterway Entry", "description": "通過連接建築的水道或下水道系統，涉水進入地下層。", "tags": ["水域", "地下", "冒險"], "effectiveness_score": 8},
        {"name": "電梯維修口", "name_en": "Elevator Maintenance Hatch", "description": "從電梯頂部的維修口進入電梯井，然後通過各層的檢修門進入建築。", "tags": ["垂直", "技術", "危險"], "effectiveness_score": 8},
        {"name": "隱藏側門", "name_en": "Hidden Side Door", "description": "在建築側面被藤蔓遮蔽的小門，推開後是一條窄小的服務通道。", "tags": ["隱蔽", "發現", "側面"], "effectiveness_score": 7},
        {"name": "屋頂天窗", "name_en": "Skylight Entry", "description": "從屋頂破碎的天窗垂降進入，繩索在空曠的大廳上方搖擺。", "tags": ["高處", "垂降", "危險"], "effectiveness_score": 8},
        {"name": "停車場入口", "name_en": "Parking Garage Entry", "description": "從地下停車場的車輛出入口走入，逐漸深入建築內部。", "tags": ["地下", "車輛", "漸進"], "effectiveness_score": 6},
        {"name": "管道間", "name_en": "Utility Shaft", "description": "通過外部的設備管道間進入，在管線叢中找到通往內部的通道。", "tags": ["技術", "管道", "狹窄"], "effectiveness_score": 7},
    ],

    # ─── 事件層 (Event Layer) ───
    "encounters": [
        {"name": "門自動關上", "name_en": "Door Slams Shut", "subcategory": "物理異常", "description": "身後的門突然猛力關上，回頭查看卻沒有任何外力作用的跡象。", "tags": ["突然", "門", "驚嚇"], "effectiveness_score": 8},
        {"name": "手電筒閃爍", "name_en": "Flashlight Flickers", "subcategory": "物理異常", "description": "手電筒突然開始不穩定地閃爍，光束忽明忽暗，但電池是全新的。", "tags": ["燈光", "設備", "不安"], "effectiveness_score": 7},
        {"name": "遠處腳步聲", "name_en": "Distant Footsteps", "subcategory": "聽覺異常", "description": "走廊盡頭傳來清晰的腳步聲，由遠而近，但目光所及之處空無一人。", "tags": ["聲音", "腳步", "接近"], "effectiveness_score": 9},
        {"name": "影子移動", "name_en": "Moving Shadow", "subcategory": "視覺異常", "description": "手電筒照到牆上，一個不屬於自己的影子一閃而過。", "tags": ["視覺", "影子", "短暫"], "effectiveness_score": 8},
        {"name": "溫度驟降", "name_en": "Sudden Temperature Drop", "subcategory": "環境異常", "description": "經過某個區域時，溫度驟然下降數度，呼出的氣都變成白霧。", "tags": ["溫度", "寒冷", "區域"], "effectiveness_score": 7},
        {"name": "設備突然啟動", "name_en": "Equipment Activates", "subcategory": "物理異常", "description": "一台斷電多年的機器突然啟動了幾秒鐘，發出嗡嗡的運轉聲後又歸於沉默。", "tags": ["設備", "電力", "詭異"], "effectiveness_score": 8},
        {"name": "收音機雜訊", "name_en": "Radio Static", "subcategory": "聽覺異常", "description": "對講機突然爆出一陣雜訊，雜訊中似乎混雜著模糊的人聲。", "tags": ["聲音", "電子", "人聲"], "effectiveness_score": 8},
        {"name": "椅子自行轉動", "name_en": "Chair Rotates", "subcategory": "物理異常", "description": "辦公室的旋轉椅緩慢地自行轉動，好像剛有人站起來離開。", "tags": ["物品", "移動", "詭異"], "effectiveness_score": 7},
        {"name": "鏡中異象", "name_en": "Mirror Anomaly", "subcategory": "視覺異常", "description": "經過一面破碎的鏡子時，餘光瞥見鏡中倒影的動作似乎慢了半拍。", "tags": ["鏡子", "視覺", "自我"], "effectiveness_score": 8},
        {"name": "不明敲擊聲", "name_en": "Unknown Knocking", "subcategory": "聽覺異常", "description": "牆壁或管線中傳來有節奏的敲擊聲，三短一長，不斷重複。", "tags": ["聲音", "節奏", "牆壁"], "effectiveness_score": 8},
        {"name": "走廊盡頭的人影", "name_en": "Figure at End of Hallway", "subcategory": "視覺異常", "description": "手電筒照向走廊盡頭，一個模糊的人形站在那裡，再看時已經消失。", "tags": ["人影", "遠處", "消失"], "effectiveness_score": 9},
        {"name": "電話突然響起", "name_en": "Phone Rings", "subcategory": "聽覺異常", "description": "一部落滿灰塵的座機突然響了起來，拿起話筒只有嗡嗡的電流聲。", "tags": ["電話", "聲音", "詭異"], "effectiveness_score": 8},
        {"name": "血跡滴落", "name_en": "Dripping Blood", "subcategory": "視覺異常", "description": "天花板緩慢滴下暗紅色的液體，仔細檢查發現是多年前的鏽水...或者不是。", "tags": ["血跡", "天花板", "噁心"], "effectiveness_score": 7},
        {"name": "呼吸聲", "name_en": "Breathing Sound", "subcategory": "聽覺異常", "description": "安靜的房間裡，除了自己的呼吸外，似乎還能聽到另一個人的呼吸。", "tags": ["呼吸", "近距離", "恐怖"], "effectiveness_score": 9},
        {"name": "玻璃自行破碎", "name_en": "Glass Shatters", "subcategory": "物理異常", "description": "遠處傳來玻璃破碎的聲響，走過去查看卻找不到新的碎片。", "tags": ["玻璃", "聲音", "幻覺"], "effectiveness_score": 7},
        {"name": "文字出現在牆上", "name_en": "Writing Appears on Wall", "subcategory": "視覺異常", "description": "回頭時發現剛才乾淨的牆上多了幾個字，字跡模糊但似乎是某種警告。", "tags": ["文字", "牆壁", "警告"], "effectiveness_score": 9},
        {"name": "電磁干擾", "name_en": "EMF Interference", "subcategory": "環境異常", "description": "EMF探測器的數值突然飆升，指向一個看似普通的角落。", "tags": ["設備", "電磁", "偵測"], "effectiveness_score": 7},
        {"name": "東西從架上掉落", "name_en": "Object Falls from Shelf", "subcategory": "物理異常", "description": "經過時，架上一個物品突然掉落地面，打破令人窒息的寂靜。", "tags": ["物品", "墜落", "驚嚇"], "effectiveness_score": 7},
        {"name": "指南針異常", "name_en": "Compass Malfunction", "subcategory": "環境異常", "description": "指南針的指針開始瘋狂旋轉，GPS也顯示錯誤的位置資訊。", "tags": ["設備", "方向", "迷失"], "effectiveness_score": 7},
        {"name": "兒童笑聲", "name_en": "Children Laughing", "subcategory": "聽覺異常", "description": "從某個房間傳來隱約的兒童笑聲，靠近時卻變成了風聲。", "tags": ["兒童", "笑聲", "經典恐怖"], "effectiveness_score": 8},
        {"name": "被移動的物品", "name_en": "Moved Objects", "subcategory": "物理異常", "description": "回到之前經過的房間，發現桌上的物品位置明顯改變了。", "tags": ["物品", "改變", "不安"], "effectiveness_score": 8},
        {"name": "不明光源", "name_en": "Unknown Light Source", "subcategory": "視覺異常", "description": "在完全斷電的建築深處，遠處閃過一道微弱的光芒。", "tags": ["光源", "遠處", "引導"], "effectiveness_score": 7},
        {"name": "腐臭味突然出現", "name_en": "Sudden Foul Smell", "subcategory": "環境異常", "description": "經過某個區域時，突然聞到一股強烈的腐臭味，但很快又消散了。", "tags": ["氣味", "腐臭", "短暫"], "effectiveness_score": 7},
        {"name": "鎖上的門自行開啟", "name_en": "Locked Door Opens", "subcategory": "物理異常", "description": "一扇明明上鎖的門，在你轉身時喀嚓一聲彈開了。", "tags": ["門", "解鎖", "邀請"], "effectiveness_score": 8},
        {"name": "恐慌感突然襲來", "name_en": "Sudden Panic", "subcategory": "心理異常", "description": "毫無預警地被強烈的恐慌感包圍，每一根神經都在尖叫著要你離開。", "tags": ["心理", "恐慌", "直覺"], "effectiveness_score": 8},
        {"name": "時間感錯亂", "name_en": "Time Distortion", "subcategory": "心理異常", "description": "看手錶發現已經過了三個小時，但感覺只進來了不到三十分鐘。", "tags": ["時間", "心理", "詭異"], "effectiveness_score": 8},
        {"name": "既視感", "name_en": "Déjà Vu", "subcategory": "心理異常", "description": "強烈的既視感——這個房間、這個角度、這個光線，好像以前來過。", "tags": ["心理", "記憶", "循環"], "effectiveness_score": 7},
        {"name": "相機異常", "name_en": "Camera Glitch", "subcategory": "環境異常", "description": "GoPro 的畫面突然出現嚴重雜訊和變形，回放時發現有幾幀拍到了不該在那裡的東西。", "tags": ["攝影", "設備", "證據"], "effectiveness_score": 9},
    ],

    "found_items": [
        {"name": "泛黃日記", "name_en": "Yellowed Diary", "subcategory": "文件記錄", "description": "一本私人日記，最後幾頁的字跡越來越潦草，內容暗示寫作者精神逐漸崩潰。", "tags": ["文字", "個人", "線索"], "effectiveness_score": 9},
        {"name": "生鏽鑰匙", "name_en": "Rusty Key", "subcategory": "工具設備", "description": "一把形狀不尋常的鑰匙，上面刻著難以辨認的編號，不知道對應哪扇門。", "tags": ["鑰匙", "謎題", "進展"], "effectiveness_score": 8},
        {"name": "醫療記錄", "name_en": "Medical Records", "subcategory": "文件記錄", "description": "散落的病歷檔案，記載著異常的治療方案和令人不安的實驗數據。", "tags": ["醫療", "文件", "真相"], "effectiveness_score": 8},
        {"name": "神秘符號", "name_en": "Mysterious Symbols", "subcategory": "神秘物件", "description": "牆上或地板上刻劃的不明符號，不像任何已知的語言或宗教符號。", "tags": ["符號", "神秘", "儀式"], "effectiveness_score": 8},
        {"name": "錄音帶", "name_en": "Audio Cassette", "subcategory": "文件記錄", "description": "一盒未標記的錄音帶，帶子有些變形但可能還能播放。", "tags": ["音頻", "記錄", "過去"], "effectiveness_score": 8},
        {"name": "褪色照片", "name_en": "Faded Photographs", "subcategory": "個人物品", "description": "幾張褪色的照片，人物面容模糊，背景就是現在站的這個地方。", "tags": ["照片", "過去", "對比"], "effectiveness_score": 7},
        {"name": "藥瓶", "name_en": "Medicine Bottles", "subcategory": "個人物品", "description": "標籤剝落的藥瓶，裡面還有少量不明藥片，處方資訊已無法辨識。", "tags": ["醫療", "藥物", "個人"], "effectiveness_score": 6},
        {"name": "手繪地圖", "name_en": "Hand-drawn Map", "subcategory": "文件記錄", "description": "某人手繪的建築平面圖，上面用紅筆標記了幾個位置，其中一個畫了大叉。", "tags": ["地圖", "標記", "指引"], "effectiveness_score": 9},
        {"name": "兒童玩具", "name_en": "Children's Toy", "subcategory": "個人物品", "description": "一個破舊的兒童玩具，不應該出現在這種地方，背後可能有更深的故事。", "tags": ["兒童", "詭異", "情感"], "effectiveness_score": 7},
        {"name": "斷裂的身分證", "name_en": "Broken ID Card", "subcategory": "個人物品", "description": "一張損毀的工作人員證件，照片已看不清，但名字和部門勉強可辨。", "tags": ["身分", "工作人員", "線索"], "effectiveness_score": 7},
        {"name": "宗教護身符", "name_en": "Religious Amulet", "subcategory": "神秘物件", "description": "某種宗教或民間信仰的護身符，似乎被刻意放在門口或窗台上。", "tags": ["宗教", "保護", "信仰"], "effectiveness_score": 7},
        {"name": "監控錄影帶", "name_en": "Surveillance Tape", "subcategory": "文件記錄", "description": "監控室遺留的錄影帶，標籤寫著事故發生當天的日期。", "tags": ["監控", "證據", "真相"], "effectiveness_score": 9},
        {"name": "實驗報告", "name_en": "Experiment Report", "subcategory": "文件記錄", "description": "殘缺的實驗報告，數據被大量塗黑，能看見的部分提到了「受試者」。", "tags": ["實驗", "機密", "塗黑"], "effectiveness_score": 9},
        {"name": "手電筒（他人的）", "name_en": "Someone's Flashlight", "subcategory": "工具設備", "description": "地上一支手電筒，不是自己的，電池已耗盡，表面有刮痕。", "tags": ["裝備", "他人", "疑問"], "effectiveness_score": 8},
        {"name": "壁畫/塗鴉", "name_en": "Wall Mural/Graffiti", "subcategory": "神秘物件", "description": "牆上大面積的塗鴉或壁畫，混雜著警告標語、宗教符號和看不懂的圖案。", "tags": ["藝術", "訊息", "前人"], "effectiveness_score": 7},
        {"name": "密碼鎖提示", "name_en": "Combination Lock Clue", "subcategory": "文件記錄", "description": "一張寫滿數字和日期的紙條，可能是某個保險箱或密碼門的組合。", "tags": ["密碼", "謎題", "解鎖"], "effectiveness_score": 8},
        {"name": "骨頭", "name_en": "Bones", "subcategory": "神秘物件", "description": "角落裡發現的骨頭，不確定是動物的還是...需要更仔細的檢查。", "tags": ["骨骼", "恐怖", "發現"], "effectiveness_score": 8},
        {"name": "求救信", "name_en": "Distress Letter", "subcategory": "文件記錄", "description": "一封寫在任何可用紙張上的求救信，字跡顫抖，內容描述被困的經歷。", "tags": ["求救", "情感", "絕望"], "effectiveness_score": 9},
        {"name": "過期罐頭", "name_en": "Expired Canned Food", "subcategory": "個人物品", "description": "角落堆放的過期罐頭和水壺，暗示有人曾在這裡躲藏了一段時間。", "tags": ["食物", "生存", "躲藏"], "effectiveness_score": 7},
        {"name": "老式收音機", "name_en": "Old Radio", "subcategory": "工具設備", "description": "一台老式短波收音機，旋鈕調到一個特定頻率，接上電源可能還能用。", "tags": ["電子", "通訊", "頻率"], "effectiveness_score": 7},
    ],

    "traps_hazards": [
        {"name": "地板塌陷", "name_en": "Floor Collapse", "subcategory": "結構危險", "description": "腐朽的地板突然塌陷，腳下出現一個通向下層的洞。", "tags": ["墜落", "結構", "突然"], "effectiveness_score": 9},
        {"name": "鐵門鎖死", "name_en": "Iron Gate Locks", "subcategory": "機關陷阱", "description": "通過的門突然關閉並鎖死，找不到任何開啟機制。", "tags": ["困住", "門", "恐慌"], "effectiveness_score": 9},
        {"name": "有毒氣體", "name_en": "Toxic Gas", "subcategory": "環境危險", "description": "空氣中開始瀰漫一股刺鼻的化學氣味，頭開始暈眩。", "tags": ["化學", "窒息", "緊急"], "effectiveness_score": 8},
        {"name": "積水陷阱", "name_en": "Water Trap", "subcategory": "環境危險", "description": "地面積水逐漸上升，水位以不自然的速度淹沒腳踝、膝蓋。", "tags": ["水", "淹沒", "緊急"], "effectiveness_score": 8},
        {"name": "結構不穩", "name_en": "Structural Instability", "subcategory": "結構危險", "description": "天花板發出令人不安的吱嘎聲，混凝土碎片不斷掉落，整個空間似乎隨時會坍塌。", "tags": ["坍塌", "結構", "持續"], "effectiveness_score": 8},
        {"name": "野生動物", "name_en": "Wild Animals", "subcategory": "環境危險", "description": "黑暗中傳來動物的低吼或翅膀拍擊聲，可能是野狗、蝙蝠、或更大的東西。", "tags": ["動物", "威脅", "聲音"], "effectiveness_score": 7},
        {"name": "完全斷電", "name_en": "Total Blackout", "subcategory": "環境危險", "description": "僅存的微弱光源突然消失，連備用手電也不知為何熄滅，陷入完全黑暗。", "tags": ["黑暗", "設備", "恐慌"], "effectiveness_score": 9},
        {"name": "石棉暴露", "name_en": "Asbestos Exposure", "subcategory": "環境危險", "description": "破損的管道包覆層釋放石棉纖維，空氣中的粉塵可能致癌。", "tags": ["健康", "隱形", "長期"], "effectiveness_score": 6},
        {"name": "電擊危險", "name_en": "Electrical Hazard", "subcategory": "結構危險", "description": "踩入水中時感到腳底微微刺痛——積水中有裸露的電線。", "tags": ["電擊", "水", "隱蔽"], "effectiveness_score": 8},
        {"name": "玻璃碎片區", "name_en": "Glass Shard Field", "subcategory": "環境危險", "description": "地面覆蓋著細碎的玻璃碎片，每一步都嘎吱作響，一不小心就會割傷。", "tags": ["玻璃", "地面", "噪音"], "effectiveness_score": 6},
        {"name": "升降梯突然啟動", "name_en": "Elevator Activates", "subcategory": "機關陷阱", "description": "廢棄的電梯突然運轉起來，金屬摩擦的尖叫聲在電梯井中迴響。", "tags": ["電梯", "機械", "驚嚇"], "effectiveness_score": 8},
        {"name": "天花板崩落", "name_en": "Ceiling Collapse", "subcategory": "結構危險", "description": "頭頂的天花板突然大面積崩落，碎石和粉塵傾瀉而下。", "tags": ["崩落", "緊急", "逃跑"], "effectiveness_score": 8},
        {"name": "化學品洩漏", "name_en": "Chemical Spill", "subcategory": "環境危險", "description": "架上的舊化學容器傾倒，不明液體流淌一地，接觸皮膚會灼傷。", "tags": ["化學", "危險", "迴避"], "effectiveness_score": 7},
        {"name": "隱藏的深坑", "name_en": "Hidden Pit", "subcategory": "結構危險", "description": "看似正常的地面覆蓋物下隱藏著一個深坑，一步錯就會掉下去。", "tags": ["陷阱", "隱藏", "墜落"], "effectiveness_score": 8},
        {"name": "鐵絲網纏繞", "name_en": "Barbed Wire Tangle", "subcategory": "環境危險", "description": "黑暗中意外撞上散落的鐵絲網，刺刺的金屬線纏住衣物和裝備。", "tags": ["鐵絲", "束縛", "割傷"], "effectiveness_score": 6},
        {"name": "防盜警報觸發", "name_en": "Security Alarm Triggered", "subcategory": "機關陷阱", "description": "不小心觸發了殘存的防盜系統，刺耳的警報聲響徹整棟建築。", "tags": ["警報", "噪音", "暴露"], "effectiveness_score": 7},
    ],

    "narrative_clues": [
        {"name": "牆上的倒數", "name_en": "Wall Countdown", "description": "牆上用粉筆寫的倒數數字：7, 6, 5... 到 2 就停了。", "tags": ["數字", "倒數", "未完成"], "effectiveness_score": 9},
        {"name": "最後的廣播", "name_en": "Last Broadcast", "description": "找到的收音機只能收到一個頻率，反覆播放同一段預錄的緊急廣播。", "tags": ["音頻", "循環", "緊急"], "effectiveness_score": 8},
        {"name": "失蹤者照片牆", "name_en": "Missing Persons Wall", "description": "一面牆上貼滿了失蹤人口的尋人啟事，日期跨越好幾年。", "tags": ["照片", "失蹤", "累積"], "effectiveness_score": 9},
        {"name": "實驗受試者編號", "name_en": "Test Subject Numbers", "description": "牆上噴漆寫著編號：#001 至 #047，每個編號旁有✓或✗標記。", "tags": ["編號", "實驗", "系統性"], "effectiveness_score": 9},
        {"name": "日記中的精神崩潰", "name_en": "Journal Mental Breakdown", "description": "日記前段正常，後段字跡越來越亂，最後幾頁只有反覆書寫的同一句話。", "tags": ["文字", "瘋狂", "漸進"], "effectiveness_score": 9},
        {"name": "密碼門", "name_en": "Code-Locked Door", "description": "一扇需要密碼的電子鎖門，面板還有電，輸入錯誤會發出警告聲。", "tags": ["密碼", "門", "互動"], "effectiveness_score": 8},
        {"name": "監控畫面殘影", "name_en": "Surveillance Footage Ghost", "description": "仍在運作的監控螢幕，畫面中偶爾閃過不應該存在的人影。", "tags": ["監控", "影像", "證據"], "effectiveness_score": 9},
        {"name": "孩子的畫", "name_en": "Child's Drawing", "description": "牆上或紙上的兒童塗鴉，畫的是這棟建築，但畫中有讓人不安的細節。", "tags": ["兒童", "藝術", "暗示"], "effectiveness_score": 8},
        {"name": "逃生路線圖", "name_en": "Escape Route Map", "description": "某人在牆上畫的逃生路線，但路線的終點被用紅色大叉劃掉了。", "tags": ["地圖", "逃生", "失敗"], "effectiveness_score": 8},
        {"name": "錄音機留言", "name_en": "Recorder Message", "description": "找到一台小型錄音機，按下播放後是一段充滿恐懼的口述記錄。", "tags": ["音頻", "個人", "記錄"], "effectiveness_score": 9},
        {"name": "新鮮的痕跡", "name_en": "Fresh Traces", "description": "在厚厚的灰塵中發現新鮮的足跡或指紋——有人最近來過。", "tags": ["痕跡", "近期", "他人"], "effectiveness_score": 8},
        {"name": "被釘死的門", "name_en": "Boarded Up Door", "description": "一扇從外面被釘上木板的門，木板上用噴漆寫著「不要打開」。", "tags": ["門", "封鎖", "警告"], "effectiveness_score": 8},
        {"name": "舊報紙剪報", "name_en": "Old Newspaper Clippings", "description": "牆上釘著多張舊報紙剪報，報導都與這棟建築的事故有關。", "tags": ["報紙", "歷史", "蒐集"], "effectiveness_score": 7},
        {"name": "地上的拖曳痕跡", "name_en": "Drag Marks on Floor", "description": "地面上有明顯的拖曳痕跡，從房間中央一路延伸到門外消失。", "tags": ["痕跡", "暴力", "推理"], "effectiveness_score": 8},
        {"name": "反覆出現的符號", "name_en": "Recurring Symbol", "description": "同一個不明符號出現在不同房間的牆上、地板、甚至天花板上。", "tags": ["符號", "反覆", "意義"], "effectiveness_score": 8},
    ],

    # ─── 氛圍層 (Atmosphere Layer) ───
    "time_settings": [
        {"name": "深夜兩點", "name_en": "2 AM", "description": "凌晨兩點，萬物沉睡的時刻，只有探索者的腳步打破寂靜。", "tags": ["深夜", "安靜", "經典"], "effectiveness_score": 8},
        {"name": "凌晨三點", "name_en": "3 AM (Witching Hour)", "description": "魔鬼時刻——凌晨三點，傳說中靈體最活躍的時間。", "tags": ["深夜", "超自然", "高峰"], "effectiveness_score": 9},
        {"name": "黃昏時分", "name_en": "Dusk", "description": "太陽即將落下，最後的光線在廢墟中投射出詭異的長影。", "tags": ["黃昏", "過渡", "影子"], "effectiveness_score": 7},
        {"name": "午夜", "name_en": "Midnight", "description": "日期交替的時刻，新的一天在黑暗中開始。", "tags": ["午夜", "交替", "標誌"], "effectiveness_score": 7},
        {"name": "破曉前", "name_en": "Before Dawn", "description": "天亮前最黑暗的時刻，空氣中帶著寒意和即將結束的緊張感。", "tags": ["黎明前", "寒冷", "期待"], "effectiveness_score": 7},
        {"name": "白天（反差恐怖）", "name_en": "Daytime (Contrast Horror)", "description": "大白天進入廢墟，外面陽光普照，裡面卻暗如深淵——反差讓恐怖更真實。", "tags": ["白天", "反差", "真實"], "effectiveness_score": 7},
        {"name": "月蝕之夜", "name_en": "Lunar Eclipse Night", "description": "血月高掛的夜晚，月光透過雲層投射出暗紅色的光芒。", "tags": ["月蝕", "紅光", "特殊"], "effectiveness_score": 8},
        {"name": "暴風雨夜", "name_en": "Stormy Night", "description": "狂風暴雨的夜晚，雷電照亮廢墟的輪廓，雨水從破損的屋頂灌入。", "tags": ["暴風雨", "動態", "聲音"], "effectiveness_score": 9},
        {"name": "停電之後", "name_en": "After Power Outage", "description": "城市大停電的夜晚，整個區域一片漆黑，連街燈都滅了。", "tags": ["停電", "黑暗", "孤立"], "effectiveness_score": 8},
        {"name": "大霧清晨", "name_en": "Foggy Morning", "description": "濃霧籠罩的清晨，能見度不到五公尺，廢墟在霧中若隱若現。", "tags": ["霧", "清晨", "迷幻"], "effectiveness_score": 8},
        {"name": "日落時分", "name_en": "Sunset", "description": "最後一縷陽光從窗戶照入，隨著太陽下山，室內逐漸被黑暗吞噬。", "tags": ["日落", "過渡", "漸變"], "effectiveness_score": 7},
        {"name": "萬聖節夜", "name_en": "Halloween Night", "description": "10月31日的夜晚，在這個特殊的日子探索廢墟格外應景。", "tags": ["節日", "特殊", "氣氛"], "effectiveness_score": 7},
        {"name": "新年倒數時", "name_en": "New Year's Eve Countdown", "description": "跨年夜，遠處傳來煙火和歡呼，廢墟裡卻是另一個世界。", "tags": ["節日", "反差", "孤獨"], "effectiveness_score": 7},
        {"name": "颱風前夕", "name_en": "Before Typhoon", "description": "颱風來襲前的寂靜，氣壓降低讓人莫名焦躁，風開始變強。", "tags": ["颱風", "不安", "壓力"], "effectiveness_score": 8},
        {"name": "冬至深夜", "name_en": "Winter Solstice Night", "description": "一年中最長的夜晚，黑暗似乎永遠不會結束。", "tags": ["冬季", "最長夜", "寒冷"], "effectiveness_score": 7},
    ],

    "weather_conditions": [
        {"name": "暴雨傾盆", "name_en": "Heavy Rain", "description": "持續的大雨讓室外一片朦朧，雨水沿著牆壁裂縫流入建築內部。", "tags": ["雨", "潮濕", "聲音"], "effectiveness_score": 8},
        {"name": "濃霧", "name_en": "Dense Fog", "description": "能見度極低的濃霧，建築輪廓在霧中像幽靈般若隱若現。", "tags": ["霧", "視覺", "朦朧"], "effectiveness_score": 8},
        {"name": "寂靜無風", "name_en": "Dead Calm", "description": "沒有一絲風的夜晚，空氣凝滯不動，寂靜得能聽見自己的心跳。", "tags": ["安靜", "無風", "壓迫"], "effectiveness_score": 8},
        {"name": "冷到結霜", "name_en": "Freezing Cold", "description": "氣溫降到冰點以下，金屬表面結了一層薄霜，呼出的氣都是白霧。", "tags": ["寒冷", "結霜", "不適"], "effectiveness_score": 7},
        {"name": "遠處雷聲", "name_en": "Distant Thunder", "description": "遠方傳來低沉的雷聲，偶爾閃電照亮天際，暴風雨正在接近。", "tags": ["雷聲", "閃電", "接近"], "effectiveness_score": 8},
        {"name": "毛毛雨", "name_en": "Drizzle", "description": "綿密的細雨讓一切都濕漉漉的，地面濕滑，金屬更加冰冷。", "tags": ["小雨", "潮濕", "陰鬱"], "effectiveness_score": 6},
        {"name": "狂風呼嘯", "name_en": "Howling Wind", "description": "強風灌入建築的每個縫隙，發出像野獸般的呼嘯，門窗劇烈拍打。", "tags": ["風", "聲音", "動態"], "effectiveness_score": 8},
        {"name": "冰雹", "name_en": "Hailstorm", "description": "冰雹砸在屋頂和窗戶上，發出密集的敲擊聲，像萬千手指同時敲打。", "tags": ["冰雹", "噪音", "暴力"], "effectiveness_score": 7},
        {"name": "悶熱潮濕", "name_en": "Humid and Muggy", "description": "令人窒息的悶熱，空氣中水分飽和，衣服很快被汗水浸透。", "tags": ["悶熱", "不適", "夏季"], "effectiveness_score": 6},
        {"name": "萬里無雲", "name_en": "Clear Starry Sky", "description": "異常晴朗的夜空，星光從破損的天花板灑落，形成微弱的自然光。", "tags": ["晴朗", "星光", "寧靜"], "effectiveness_score": 6},
        {"name": "雪", "name_en": "Snowfall", "description": "大雪紛飛，白雪覆蓋廢墟如同冰封的墓地，腳印格外清晰。", "tags": ["雪", "白色", "痕跡"], "effectiveness_score": 7},
        {"name": "沙塵暴", "name_en": "Sandstorm", "description": "黃沙漫天，能見度幾乎為零，沙粒打在皮膚上隱隱作痛。", "tags": ["沙塵", "能見度", "惡劣"], "effectiveness_score": 7},
        {"name": "間歇性閃電", "name_en": "Intermittent Lightning", "description": "不規律的閃電不斷照亮室內空間，每一次閃光都揭示不同的恐怖細節。", "tags": ["閃電", "間歇", "揭示"], "effectiveness_score": 9},
        {"name": "回南天", "name_en": "Returning Moisture", "description": "極度潮濕的天氣，牆壁和地板都在冒水珠，整棟建築像在流汗。", "tags": ["潮濕", "水珠", "詭異"], "effectiveness_score": 7},
        {"name": "起霧散去循環", "name_en": "Fog Cycles", "description": "霧氣一陣一陣地湧入又散去，視野在清晰和朦朧間不斷切換。", "tags": ["霧", "循環", "不穩定"], "effectiveness_score": 7},
    ],

    "ambient_triggers": [
        {"name": "持續滴水聲", "name_en": "Constant Dripping", "description": "規律的滴水聲在寂靜中格外刺耳，不知道水從哪裡來。", "tags": ["水", "規律", "背景"], "effectiveness_score": 7},
        {"name": "金屬碰撞", "name_en": "Metal Clanking", "description": "某處傳來金屬互相碰撞的聲響，像是風吹動懸掛的鏈條。", "tags": ["金屬", "碰撞", "風"], "effectiveness_score": 7},
        {"name": "風灌入裂縫", "name_en": "Wind Through Cracks", "description": "風通過牆壁和窗戶的裂縫擠入，發出低沉的呻吟般的聲音。", "tags": ["風", "呻吟", "建築"], "effectiveness_score": 8},
        {"name": "燈泡明滅", "name_en": "Flickering Bulb", "description": "某處一顆燈泡不知為何還在通電，忽明忽暗地閃爍。", "tags": ["燈光", "電力", "閃爍"], "effectiveness_score": 8},
        {"name": "玻璃碎裂", "name_en": "Glass Breaking", "description": "遠處傳來玻璃破碎的清脆聲響，迴響在空蕩的走廊中。", "tags": ["玻璃", "突然", "遠處"], "effectiveness_score": 7},
        {"name": "管線嘎吱聲", "name_en": "Pipe Groaning", "description": "老舊的金屬管線因溫差收縮，發出類似呻吟的嘎吱聲。", "tags": ["管線", "聲音", "金屬"], "effectiveness_score": 7},
        {"name": "老鼠竄逃", "name_en": "Rats Scurrying", "description": "腳邊突然竄過的小動物影子和細碎的爪子刮地聲。", "tags": ["動物", "突然", "地面"], "effectiveness_score": 6},
        {"name": "門的吱嘎聲", "name_en": "Creaking Door", "description": "某扇門在氣流中緩慢搖擺，鉸鏈發出令人牙酸的吱嘎聲。", "tags": ["門", "搖擺", "經典"], "effectiveness_score": 7},
        {"name": "回音放大", "name_en": "Echo Amplification", "description": "自己的腳步和呼吸在空間中被異常放大，彷彿有人在模仿。", "tags": ["回音", "放大", "模仿"], "effectiveness_score": 8},
        {"name": "電磁嗡嗡聲", "name_en": "Electromagnetic Hum", "description": "一種低頻的嗡嗡聲充斥空間，找不到來源，讓人頭疼。", "tags": ["低頻", "電磁", "不適"], "effectiveness_score": 7},
        {"name": "窗簾飄動", "name_en": "Curtain Flutter", "description": "殘破的窗簾被看不見的風吹得輕輕飄動，在手電筒光中投射出舞動的影子。", "tags": ["窗簾", "風", "影子"], "effectiveness_score": 7},
        {"name": "天花板灰塵掉落", "name_en": "Ceiling Dust Falls", "description": "頭頂不時落下細碎的灰塵和碎片，暗示上方有什麼在移動。", "tags": ["灰塵", "上方", "移動"], "effectiveness_score": 7},
        {"name": "遠處的警笛", "name_en": "Distant Siren", "description": "遠方隱約傳來警笛或救護車的聲音，提醒你外面的世界仍在運轉。", "tags": ["外部", "警笛", "對比"], "effectiveness_score": 6},
        {"name": "蟲鳴蛙叫", "name_en": "Insects and Frogs", "description": "建築被自然收復的痕跡——蟲鳴和蛙叫取代了人類活動的聲音。", "tags": ["自然", "接管", "生命"], "effectiveness_score": 6},
        {"name": "不明振動", "name_en": "Unknown Vibration", "description": "地板和牆壁傳來微弱但持續的振動，像是地底有某種機械在運轉。", "tags": ["振動", "地底", "機械"], "effectiveness_score": 8},
        {"name": "時鐘滴答聲", "name_en": "Clock Ticking", "description": "某處傳來老式時鐘的滴答聲，在廢棄多年的建築中格外不協調。", "tags": ["時鐘", "計時", "詭異"], "effectiveness_score": 8},
        {"name": "暖氣管突然膨脹", "name_en": "Heating Pipe Expansion", "description": "廢棄的暖氣系統管線突然發出巨大的膨脹聲，像是某個東西在管子裡移動。", "tags": ["管線", "突然", "膨脹"], "effectiveness_score": 7},
        {"name": "腐木斷裂", "name_en": "Rotting Wood Snapping", "description": "腐朽的木質結構在自身重量下緩慢斷裂，發出沉悶的碎裂聲。", "tags": ["木頭", "斷裂", "結構"], "effectiveness_score": 7},
        {"name": "鳥群驚飛", "name_en": "Birds Taking Flight", "description": "突然的聲響驚動了棲息在建築中的鳥群，翅膀拍擊的聲音如爆炸般響起。", "tags": ["鳥", "突然", "驚嚇"], "effectiveness_score": 7},
        {"name": "水管爆裂", "name_en": "Pipe Burst", "description": "某根老舊水管突然爆裂，水柱噴射而出，在寂靜中格外震撼。", "tags": ["水管", "突然", "噴射"], "effectiveness_score": 7},
    ],

    # ─── 結構層 (Structure Layer) ───
    "tension_curves": [
        {"name": "漸進升高", "name_en": "Gradual Escalation", "description": "從安靜開場，事件強度逐步遞增，在最後爆發到最高點。", "tags": ["穩定", "漸進", "爆發"], "effectiveness_score": 8},
        {"name": "先平後爆", "name_en": "Calm Then Explosion", "description": "大部分時間維持低張力的探索節奏，在某個瞬間突然爆發極大恐懼。", "tags": ["反差", "突然", "衝擊"], "effectiveness_score": 9},
        {"name": "波浪式", "name_en": "Wave Pattern", "description": "張力如波浪般起伏——緊張、緩和、更緊張、稍緩、最終高潮。", "tags": ["波浪", "起伏", "節奏"], "effectiveness_score": 8},
        {"name": "持續高壓", "name_en": "Sustained High Pressure", "description": "從一開始就營造強烈的不安感，全程維持高度緊張，沒有喘息的空間。", "tags": ["高壓", "持續", "窒息"], "effectiveness_score": 7},
        {"name": "假結局反轉", "name_en": "False Ending Twist", "description": "看似安全結束後，突然揭示一個更恐怖的真相或事件，推翻之前的認知。", "tags": ["反轉", "假結局", "驚喜"], "effectiveness_score": 10},
        {"name": "雙高潮", "name_en": "Double Climax", "description": "設置兩個張力高峰：第一個較小的高潮引發第二個更大的終極高潮。", "tags": ["雙峰", "遞進", "加倍"], "effectiveness_score": 8},
        {"name": "倒敘緊張", "name_en": "Reverse Tension", "description": "從最恐怖的場景開始，然後倒敘揭示如何走到這一步。", "tags": ["倒敘", "懸念", "解謎"], "effectiveness_score": 7},
        {"name": "螺旋下降", "name_en": "Downward Spiral", "description": "每一個發現都比上一個更令人不安，探索者越深入越無法抽身。", "tags": ["螺旋", "加深", "不歸路"], "effectiveness_score": 9},
        {"name": "平靜中的異常", "name_en": "Abnormality in Calm", "description": "表面上一切平靜正常，但細微的錯誤和不協調感持續累積，直到觀眾意識到哪裡不對。", "tags": ["細微", "累積", "恐怖谷"], "effectiveness_score": 8},
        {"name": "心跳節奏", "name_en": "Heartbeat Rhythm", "description": "事件的發生頻率模仿加速的心跳：開始緩慢，逐漸加快，最後瘋狂。", "tags": ["心跳", "加速", "生理"], "effectiveness_score": 8},
    ],

    "ending_types": [
        {"name": "安全撤離", "name_en": "Safe Extraction", "description": "在最後一刻成功逃出建築，回到外面的世界喘息，但帶著永遠無法忘記的記憶。", "tags": ["逃出", "安全", "喘息"], "effectiveness_score": 7},
        {"name": "被迫逃跑", "name_en": "Forced Escape", "description": "某個事件迫使探索者放棄計劃，瘋狂奔跑逃出，裝備和錄影器材都顧不上了。", "tags": ["逃跑", "恐慌", "遺失"], "effectiveness_score": 8},
        {"name": "發現真相", "name_en": "Truth Discovered", "description": "在最深處找到了這個地方的終極秘密，真相比任何想像都更令人不安。", "tags": ["真相", "揭示", "震撼"], "effectiveness_score": 9},
        {"name": "迷失更深", "name_en": "Lost Deeper", "description": "試圖原路返回卻發現路線改變了，被迫往更深處前進，結局是未知。", "tags": ["迷失", "深入", "未知"], "effectiveness_score": 9},
        {"name": "懸念結尾", "name_en": "Cliffhanger", "description": "影片在最緊張的一刻突然結束——門後有什麼？那個聲音是什麼？下集揭曉。", "tags": ["懸念", "中斷", "續集"], "effectiveness_score": 9},
        {"name": "循環結局", "name_en": "Loop Ending", "description": "回到入口卻發現一切又回到了開始的狀態，好像從未離開過。", "tags": ["循環", "詭異", "時間"], "effectiveness_score": 8},
        {"name": "監控視角", "name_en": "Surveillance View", "description": "最後畫面切到監控視角，看著探索者離開——但監控畫面中還有另一個人影。", "tags": ["監控", "第三人", "餘韻"], "effectiveness_score": 10},
        {"name": "失去畫面", "name_en": "Signal Lost", "description": "攝影機突然嚴重干擾，畫面扭曲變形，在雜訊中一閃——然後什麼都沒有了。", "tags": ["技術", "中斷", "失蹤"], "effectiveness_score": 9},
        {"name": "平靜離開但...","name_en": "Calm Exit But...", "description": "探索者平靜離開，上車發動引擎，後視鏡中建築的某個窗戶亮起了燈。", "tags": ["平靜", "反差", "暗示"], "effectiveness_score": 9},
        {"name": "發現不是獨自一人", "name_en": "Not Alone", "description": "回看GoPro錄影時，發現某個角落一直有人在觀察自己。", "tags": ["回放", "發現", "恐怖"], "effectiveness_score": 10},
        {"name": "設備回收", "name_en": "Equipment Recovery", "description": "這段影片是從廢墟中找回的設備上恢復的——探索者本人從未回來。", "tags": ["找到片段", "失蹤", "偽紀錄"], "effectiveness_score": 9},
        {"name": "照片證據", "name_en": "Photo Evidence", "description": "結尾展示探索中拍的照片，放大後每張照片背景都有同一個不該在那裡的東西。", "tags": ["照片", "放大", "發現"], "effectiveness_score": 9},
        {"name": "電話留言", "name_en": "Voicemail", "description": "結尾是探索者探索後留給朋友的語音留言，語氣恐慌，之後再也聯繫不上此人。", "tags": ["語音", "失聯", "偽紀錄"], "effectiveness_score": 8},
        {"name": "清晨回望", "name_en": "Dawn Look Back", "description": "天亮了，探索者站在遠處回望建築，一切在晨光下看起來平凡無奇——彷彿什麼都沒發生過。", "tags": ["清晨", "平靜", "反差"], "effectiveness_score": 7},
        {"name": "續集預告", "name_en": "Sequel Teaser", "description": "結尾出現一張新地點的照片和座標，配上字幕「下一站」，暗示探索還沒結束。", "tags": ["續集", "預告", "系列"], "effectiveness_score": 7},
    ],

    "exploration_motives": [
        {"name": "都市傳說驗證", "name_en": "Urban Legend Verification", "description": "為了驗證網路上流傳已久的都市傳說，深入這個被稱為「不能去的地方」。", "tags": ["傳說", "驗證", "好奇"], "effectiveness_score": 8},
        {"name": "失蹤者搜索", "name_en": "Missing Person Search", "description": "追蹤一名失蹤者最後出現的地點，帶著手電筒和相機重走他的路線。", "tags": ["失蹤", "搜索", "個人"], "effectiveness_score": 9},
        {"name": "網友挑戰", "name_en": "Internet Challenge", "description": "社群媒體上有人發起挑戰：在這棟建築裡待滿一個小時並全程直播。", "tags": ["挑戰", "社群", "勇氣"], "effectiveness_score": 7},
        {"name": "職業廢墟探索", "name_en": "Professional Urbex", "description": "作為一名都市探險家，記錄和保存這些即將消失的人類遺跡是使命。", "tags": ["專業", "記錄", "保存"], "effectiveness_score": 7},
        {"name": "尋寶", "name_en": "Treasure Hunting", "description": "傳聞建築中藏有價值不菲的遺留物品或秘密，值得冒險一探。", "tags": ["寶藏", "貪婪", "回報"], "effectiveness_score": 7},
        {"name": "記者調查", "name_en": "Journalist Investigation", "description": "作為調查記者，追蹤一條與這棟建築相關的線索，試圖揭露被掩蓋的真相。", "tags": ["記者", "調查", "真相"], "effectiveness_score": 8},
        {"name": "攝影創作", "name_en": "Photography Project", "description": "廢墟攝影師被這裡獨特的美感吸引，帶著相機記錄衰敗中的美。", "tags": ["攝影", "藝術", "美感"], "effectiveness_score": 6},
        {"name": "回憶追尋", "name_en": "Memory Pursuit", "description": "這裡曾與自己的過去有關——也許是童年、也許是某個人，想在廢墟中找回遺失的記憶。", "tags": ["個人", "回憶", "情感"], "effectiveness_score": 8},
        {"name": "科學研究", "name_en": "Scientific Research", "description": "攜帶EMF探測器、溫度計等設備，用科學方法調查這裡的異常現象報告。", "tags": ["科學", "設備", "理性"], "effectiveness_score": 7},
        {"name": "打賭", "name_en": "Bet/Dare", "description": "跟朋友打賭的代價——獨自在廢墟中度過一夜，否則輸掉一筆不小的賭注。", "tags": ["賭注", "朋友", "壓力"], "effectiveness_score": 7},
        {"name": "逃避現實", "name_en": "Escaping Reality", "description": "生活中遭遇挫折，在黑暗和廢墟中找到一種奇特的平靜和自由。", "tags": ["逃避", "心理", "自由"], "effectiveness_score": 6},
        {"name": "接到匿名訊息", "name_en": "Anonymous Message", "description": "收到一則匿名訊息，只有一個地址和一句話：「來了就知道了。」", "tags": ["匿名", "邀請", "神秘"], "effectiveness_score": 9},
        {"name": "續集探索", "name_en": "Return Visit", "description": "上次探索留下太多未解之謎，這次帶著更好的裝備和更大的決心重返。", "tags": ["重返", "續集", "決心"], "effectiveness_score": 8},
        {"name": "夢境指引", "name_en": "Dream Guidance", "description": "反覆夢見同一棟建築，搜尋後發現它真實存在，覺得必須親自去看看。", "tags": ["夢境", "超自然", "命運"], "effectiveness_score": 8},
        {"name": "直播內容製作", "name_en": "Live Stream Content", "description": "作為內容創作者，為了觀眾和流量深入廢墟，全程直播。", "tags": ["直播", "內容", "觀眾"], "effectiveness_score": 7},
    ],

    "explorer_equipment": [
        {"name": "強力手電筒", "name_en": "High-Power Flashlight", "description": "2000流明的戰術手電筒，是黑暗中最可靠的夥伴。", "tags": ["照明", "基本", "戰術"], "effectiveness_score": 8},
        {"name": "GoPro攝影機", "name_en": "GoPro Camera", "description": "頭戴式運動攝影機，全程記錄第一人稱視角的探索畫面。", "tags": ["攝影", "POV", "記錄"], "effectiveness_score": 9},
        {"name": "EMF探測器", "name_en": "EMF Detector", "description": "電磁場探測器，常用於偵測異常的電磁波動。", "tags": ["偵測", "科學", "超自然"], "effectiveness_score": 7},
        {"name": "對講機", "name_en": "Walkie-Talkie", "description": "與留在外面的夥伴保持通訊的對講機，但越深入信號越差。", "tags": ["通訊", "夥伴", "信號"], "effectiveness_score": 7},
        {"name": "攀爬繩索", "name_en": "Climbing Rope", "description": "20公尺的登山繩索，用於垂降或攀爬無法正常通行的區域。", "tags": ["攀爬", "垂降", "移動"], "effectiveness_score": 7},
        {"name": "撬棍", "name_en": "Crowbar", "description": "萬用工具——撬門、撬窗、清除障礙物，必要時也是防身武器。", "tags": ["工具", "力量", "多用"], "effectiveness_score": 8},
        {"name": "防毒面具", "name_en": "Gas Mask", "description": "防止吸入有害氣體、石棉纖維或黴菌孢子的專業防毒面具。", "tags": ["防護", "呼吸", "安全"], "effectiveness_score": 7},
        {"name": "夜視儀", "name_en": "Night Vision Device", "description": "軍用級夜視裝置，在完全黑暗中也能看到周圍環境的綠色影像。", "tags": ["夜視", "科技", "軍事"], "effectiveness_score": 8},
        {"name": "紅外線溫度計", "name_en": "Infrared Thermometer", "description": "用來偵測環境溫度變化，特別是那些不自然的冷點。", "tags": ["溫度", "偵測", "科學"], "effectiveness_score": 6},
        {"name": "備用電池", "name_en": "Spare Batteries", "description": "大量的備用電池，因為這種地方的設備特別容易莫名其妙地沒電。", "tags": ["電力", "備份", "實用"], "effectiveness_score": 7},
        {"name": "急救包", "name_en": "First Aid Kit", "description": "基本的急救用品——繃帶、消毒液、止痛藥，廢墟探索中受傷機率很高。", "tags": ["醫療", "安全", "基本"], "effectiveness_score": 6},
        {"name": "粉筆/噴漆", "name_en": "Chalk/Spray Paint", "description": "在牆上做標記防止迷路，也可以標記已探索和未探索的區域。", "tags": ["標記", "導航", "記錄"], "effectiveness_score": 7},
        {"name": "收音機/掃描器", "name_en": "Radio Scanner", "description": "可以掃描各頻段的收音機，有時能接收到殘留的廣播信號。", "tags": ["通訊", "掃描", "發現"], "effectiveness_score": 7},
        {"name": "金屬探測器", "name_en": "Metal Detector", "description": "偵測牆壁或地面下隱藏的金屬物品和管線。", "tags": ["偵測", "隱藏", "尋寶"], "effectiveness_score": 6},
        {"name": "雷射測距儀", "name_en": "Laser Rangefinder", "description": "測量空間距離和深度，特別適用於評估地下空間或深坑的深度。", "tags": ["測量", "科技", "評估"], "effectiveness_score": 6},
        {"name": "無人機", "name_en": "Drone", "description": "小型無人機，先用它偵察無法直接到達的區域和高處。", "tags": ["空中", "偵察", "科技"], "effectiveness_score": 7},
        {"name": "防刺手套", "name_en": "Cut-Resistant Gloves", "description": "防止被鏽蝕金屬、碎玻璃或鐵絲網割傷的防護手套。", "tags": ["防護", "手部", "實用"], "effectiveness_score": 6},
        {"name": "頭燈", "name_en": "Headlamp", "description": "解放雙手的頭戴式照明，探索時特別實用。", "tags": ["照明", "免持", "基本"], "effectiveness_score": 8},
        {"name": "指南針+紙質地圖", "name_en": "Compass + Paper Map", "description": "不依賴電子設備的導航方案，在信號被干擾時是最後的保障。", "tags": ["導航", "類比", "備份"], "effectiveness_score": 6},
        {"name": "靈魂盒", "name_en": "Spirit Box", "description": "快速掃描FM/AM頻段的裝置，據說能接收靈體的聲音訊息。", "tags": ["超自然", "掃描", "爭議"], "effectiveness_score": 7},
    ],
}


def main():
    print("═══ 知識庫填充腳本 ═══\n")

    # Ensure directories
    KB_ROOT.mkdir(parents=True, exist_ok=True)
    for cat in SEED:
        (KB_ROOT / cat).mkdir(exist_ok=True)

    all_index = []
    total = 0

    for category, items in SEED.items():
        print(f"  {category}: ", end="")
        count = 0
        for item in items:
            entry = save_entry(category, item)
            all_index.append({
                "id": entry["id"],
                "category": category,
                "subcategory": entry.get("subcategory", ""),
                "name": entry["name"],
                "tags": entry.get("tags", []),
                "effectiveness_score": entry.get("effectiveness_score", 5),
                "created_at": entry["created_at"],
            })
            count += 1
            total += 1
            import time; time.sleep(0.001)  # Ensure unique timestamps
        print(f"{count} 筆")

    # Write index
    KB_INDEX_PATH.write_text(
        json.dumps(all_index, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    print(f"\n✅ 完成！共填充 {total} 筆元素到 {len(SEED)} 個類別")
    print(f"   Index: {KB_INDEX_PATH}")

    # Print stats
    print("\n📊 類別統計:")
    for cat, items in SEED.items():
        print(f"   {cat}: {len(items)}")


if __name__ == "__main__":
    main()
