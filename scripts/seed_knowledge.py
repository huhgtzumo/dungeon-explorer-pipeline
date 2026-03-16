"""Seed knowledge base with exploration elements (hardcoded, no LLM calls).

Usage:
    python -m scripts.seed_knowledge
"""

from __future__ import annotations

import logging

from src.knowledge.knowledge_base import KnowledgeBase

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

# ── Seed Data ──

BUILDINGS = [
    {"name": "廢棄醫院", "name_en": "Abandoned Hospital", "description": "長滿霉斑的走廊、生鏽的輪床、殘留藥劑的瓶罐，空氣中瀰漫消毒水與腐朽混合的氣味"},
    {"name": "古堡地下室", "name_en": "Castle Dungeon", "description": "厚重石牆、鐵鍊與火把座、潮濕陰暗的拱形通道，中世紀的壓迫感撲面而來"},
    {"name": "荒廢工廠", "name_en": "Derelict Factory", "description": "巨大的工業機械靜默矗立、碎裂的窗戶、油漬斑斑的地面，金屬結構在風中發出低沉呻吟"},
    {"name": "沉沒神廟", "name_en": "Sunken Temple", "description": "半淹沒在水中的古老殿堂、青苔覆蓋的石柱、神祕符文在水面下隱約發光"},
    {"name": "蘇聯地堡", "name_en": "Soviet Bunker", "description": "冰冷的混凝土牆壁、生鏽的防爆門、褪色的蘇聯標語和防毒面具散落各處"},
    {"name": "日式廢校", "name_en": "Abandoned Japanese School", "description": "木質地板嘎吱作響、黑板上殘留粉筆字跡、窗外是被藤蔓吞噬的操場"},
    {"name": "地下實驗室", "name_en": "Underground Laboratory", "description": "不鏽鋼檯面上散落的試管、閃爍的警示燈、密封艙和不明液體的容器"},
    {"name": "廢棄礦坑", "name_en": "Abandoned Mine", "description": "狹窄的岩石隧道、腐朽的木質支撐結構、黑暗中迴盪的滴水聲和不穩定的地面"},
    {"name": "沉船殘骸", "name_en": "Shipwreck Interior", "description": "傾斜的甲板、鏽蝕的金屬艙壁、海水滲入的船艙內漂浮著殘骸碎片"},
    {"name": "廢棄精神病院", "name_en": "Abandoned Asylum", "description": "軟墊牆壁的隔離室、鐵柵欄窗戶、牆上的抓痕和塗鴉述說著過去的瘋狂"},
    {"name": "地下教堂", "name_en": "Underground Cathedral", "description": "巨大的地下穹頂、破碎的彩色玻璃散落地面、燭台上凝固的蠟淚成行"},
    {"name": "廢棄遊樂園", "name_en": "Abandoned Amusement Park", "description": "鏽蝕的摩天輪在風中緩慢旋轉、褪色的小丑看板、雜草叢生的碰碰車場地"},
    {"name": "軍事防空洞", "name_en": "Military Air Raid Shelter", "description": "厚重的鋼筋混凝土、通訊設備殘骸、帶有軍事編號的密封門和通風管道"},
    {"name": "古埃及墓穴", "name_en": "Egyptian Tomb", "description": "狹窄的石灰岩通道、牆壁上的象形文字、石棺和陪葬品散發著千年的沉寂"},
    {"name": "廢棄地鐵站", "name_en": "Abandoned Subway Station", "description": "蒙塵的瓷磚牆面、黑暗的隧道深處傳來氣流聲、停靠在月台的廢棄列車"},
    {"name": "維多利亞老宅", "name_en": "Victorian Mansion", "description": "華麗但破敗的裝潢、吱呀的木質樓梯、覆蓋白布的家具和積滿灰塵的水晶吊燈"},
]

ROUTES = [
    {"name": "直線深入", "name_en": "Linear Descent", "description": "一條路走到底，越深入越黑暗越危險，壓迫感持續累積，無法回頭的緊迫感"},
    {"name": "分岔選擇", "name_en": "Branching Paths", "description": "多次面臨左右路線的選擇，每條路有不同的遭遇和線索，製造選擇焦慮"},
    {"name": "螺旋下降", "name_en": "Spiral Descent", "description": "沿著螺旋狀樓梯或通道不斷下行，每一圈都能看到上方越來越遠的光線"},
    {"name": "迷宮回繞", "name_en": "Maze Loop", "description": "在相似的房間和走廊間迷失方向，發現自己走回了起點的標記物，增加恐慌"},
    {"name": "塌方改道", "name_en": "Collapse Detour", "description": "原定路線突然塌方堵住，被迫轉入未知區域，打破探索節奏製造意外"},
    {"name": "垂直攀降", "name_en": "Vertical Traverse", "description": "通過電梯井、通風管道或繩索上下移動，垂直空間的恐懼和不穩定感"},
    {"name": "涉水前行", "name_en": "Wading Path", "description": "積水越來越深，從腳踝到膝蓋到腰部，在黑暗水中前行的未知恐懼"},
    {"name": "天花板爬行", "name_en": "Ceiling Crawl", "description": "通道越來越矮，被迫彎腰、蹲行最後匍匐前進，幽閉恐懼達到極致"},
    {"name": "暗門發現", "name_en": "Hidden Door Discovery", "description": "在看似死路的牆壁後發現隱藏通道，打開新的探索空間，驚喜與不安並存"},
    {"name": "環形動線", "name_en": "Circular Route", "description": "探索路線最終形成一個環形，回到起點時發現環境已經改變，增加超自然感"},
    {"name": "階梯遞進", "name_en": "Stepped Progression", "description": "每通過一道門就進入更深層的區域，難度和詭異程度逐層遞增"},
    {"name": "通風管穿越", "name_en": "Vent Crawl", "description": "在狹窄的通風管道中爬行，金屬管壁上的回音放大了每個細微聲響"},
    {"name": "橋樑跨越", "name_en": "Bridge Crossing", "description": "在危險的橋樑或高架結構上前進，下方是深不見底的黑暗或水面"},
    {"name": "逆流溯源", "name_en": "Upstream Trace", "description": "沿著水流、電線或管道的方向逆向追蹤，尋找源頭背後的秘密"},
    {"name": "多層穿梭", "name_en": "Multi-Level Traverse", "description": "在建築的不同樓層間來回移動，通過樓梯、洞口和坍塌處上下穿梭"},
]

ZONES = [
    {"name": "長廊", "name_en": "Long Corridor", "description": "無盡延伸的走廊，兩側是緊閉的門扉，手電筒光束在盡頭消散成黑暗"},
    {"name": "密室", "name_en": "Sealed Chamber", "description": "四面封閉的房間，空氣稀薄，牆上有刮痕和神秘標記，出口機關待解"},
    {"name": "地下水道", "name_en": "Underground Waterway", "description": "拱形磚石通道中流淌著黑色水流，迴盪的水聲掩蓋了其他聲音"},
    {"name": "實驗室", "name_en": "Laboratory", "description": "佈滿儀器的工作台、培養皿中不明物質、牆上貼滿數據圖表和照片"},
    {"name": "祭壇", "name_en": "Altar Room", "description": "房間中央的石制祭台、地面上的符文圓環、牆壁上的宗教或邪教圖騰"},
    {"name": "圖書館", "name_en": "Library", "description": "高聳的書架倒塌散落、泛黃書頁在空氣中飄散、某些書本被特意翻開標記"},
    {"name": "冷凍庫", "name_en": "Cold Storage", "description": "結霜的金屬門後是刺骨寒冷的空間，呼出的白霧中隱約可見懸掛的鉤子"},
    {"name": "監控室", "name_en": "Control Room", "description": "多個閃爍雪花的螢幕、控制台上的按鈕和撥盤、牆上密密麻麻的線路"},
    {"name": "太平間", "name_en": "Morgue", "description": "不鏽鋼抽屜櫃、排水槽、刺鼻的福馬林氣味、其中一個抽屜微微打開"},
    {"name": "鍋爐房", "name_en": "Boiler Room", "description": "巨大的鍋爐和管道系統、蒸氣從接縫處噴出、紅色指示燈在蒸汽中若隱若現"},
    {"name": "停屍間", "name_en": "Crypt", "description": "石棺整齊排列、牆壁上的浮雕訴說著逝者故事、空氣中瀰漫著泥土的氣息"},
    {"name": "手術室", "name_en": "Operating Theater", "description": "老式手術檯上方的無影燈、玻璃櫃中的手術器具、牆角的血跡痕跡"},
    {"name": "檔案室", "name_en": "Archive Room", "description": "一排排金屬檔案櫃、散落的文件和照片、某些檔案被蓄意焚毀只剩殘片"},
    {"name": "通訊室", "name_en": "Communication Room", "description": "老式無線電設備、電報機和摩爾斯電碼記錄、偶爾傳出的白噪音中似有人聲"},
    {"name": "禁閉室", "name_en": "Isolation Cell", "description": "狹小的空間、軟墊牆壁上的抓痕、唯一的光源是門上的小窗口"},
    {"name": "頂樓閣樓", "name_en": "Attic", "description": "低矮的斜屋頂、堆滿灰塵的箱子和舊家具、窗戶透入的微弱月光"},
    {"name": "地下蓄水池", "name_en": "Underground Cistern", "description": "巨大的石柱支撐著穹頂、靜止的水面映出手電筒的光芒、回音綿長不絕"},
]

ENCOUNTERS = [
    {"name": "詭異聲響", "name_en": "Eerie Sound", "description": "遠處傳來無法辨識的聲音——可能是金屬刮擦、低沉的嗡鳴或類似人聲的呢喃"},
    {"name": "門自己關上", "name_en": "Self-Closing Door", "description": "身後的門突然猛力關閉，回頭一看空無一人，嘗試打開卻發現被鎖住了"},
    {"name": "影子閃過", "name_en": "Shadow Passing", "description": "手電筒照到走廊盡頭時，一個黑影快速掠過消失在轉角，回放記憶卻不確定是否真的看見"},
    {"name": "文字浮現牆壁", "name_en": "Wall Writing Appears", "description": "原本空白的牆面上慢慢浮現出文字或符號，像是有人用手指在塵土中書寫"},
    {"name": "溫度驟降", "name_en": "Temperature Drop", "description": "環境溫度突然急劇下降，呼出的氣息化為白霧，手電筒的光似乎也變得微弱"},
    {"name": "設備自行啟動", "name_en": "Equipment Self-Activation", "description": "廢棄的電視突然閃爍、收音機發出白噪音、電燈忽明忽暗，建築不應該有電力供應"},
    {"name": "腳步聲跟隨", "name_en": "Following Footsteps", "description": "停下腳步時，身後的腳步聲還會繼續幾步才停下，但回頭看永遠什麼都沒有"},
    {"name": "物品移位", "name_en": "Object Displacement", "description": "之前經過時明確記得的物品位置改變了——椅子轉向了、書本翻了頁、門開了"},
    {"name": "鏡中異象", "name_en": "Mirror Anomaly", "description": "經過鏡子時餘光看到反射中有不該存在的東西，但直視時一切正常"},
    {"name": "無來源低語", "name_en": "Sourceless Whisper", "description": "極其微弱的低語聲像是從牆壁裡傳出，斷斷續續聽不清內容但能感受到在說話"},
    {"name": "地面震動", "name_en": "Ground Tremor", "description": "腳下的地面突然輕微震動，像是地底深處有什麼巨大的東西在移動"},
    {"name": "電磁干擾", "name_en": "EMF Interference", "description": "手機螢幕出現雪花、指南針瘋狂旋轉、手電筒閃爍不定，電子設備全部失靈"},
    {"name": "呼吸聲", "name_en": "Breathing Sound", "description": "在寂靜的空間中清晰聽到不屬於自己的呼吸聲，沉重而緩慢，就在身後不遠處"},
    {"name": "塗鴉變化", "name_en": "Changing Graffiti", "description": "牆上的塗鴉在第二次經過時內容改變了，新增了一個箭頭或一行文字指向某個方向"},
    {"name": "突然的寂靜", "name_en": "Sudden Silence", "description": "環境中所有背景聲音突然消失——水滴聲、風聲、機械噪音全部停止，絕對的死寂"},
    {"name": "被注視感", "name_en": "Being Watched", "description": "強烈感覺到有什麼東西在黑暗中注視著自己，後頸的汗毛全部立起"},
]

LOOT = [
    {"name": "泛黃日記", "name_en": "Yellowed Diary", "description": "封面磨損的手寫日記，記錄了前人在此處的經歷和逐漸失控的心理狀態"},
    {"name": "舊照片", "name_en": "Old Photograph", "description": "黑白或褪色的照片，拍攝的是這個地方全盛時期的樣子，或是一群身份不明的人"},
    {"name": "生鏽鑰匙", "name_en": "Rusty Key", "description": "一把不知道能開什麼鎖的古舊鑰匙，造型獨特，握在手中有異樣的冰涼感"},
    {"name": "神秘符號", "name_en": "Mysterious Symbol", "description": "刻在金屬片或石塊上的不明符號，與牆上和地面的某些標記相呼應"},
    {"name": "錄音帶", "name_en": "Audio Tape", "description": "磁帶錄音器中遺留的錄音帶，播放出模糊的人聲記錄或不明聲響"},
    {"name": "實驗手稿", "name_en": "Research Notes", "description": "潦草的科學筆記和數據記錄，描述了某種實驗的過程和令人不安的結果"},
    {"name": "兒童畫作", "name_en": "Child's Drawing", "description": "蠟筆畫的圖畫，內容是這棟建築和一些詭異的場景，畫中有不該出現的存在"},
    {"name": "身份證件", "name_en": "ID Document", "description": "泛黃的工作證或身份證，照片中的人面容模糊，背面有手寫的求救信息"},
    {"name": "地圖殘片", "name_en": "Map Fragment", "description": "手繪的建築平面圖，標記了一些區域和路線，某些地方被紅筆圈出或打叉"},
    {"name": "斷裂的十字架", "name_en": "Broken Crucifix", "description": "從中間斷裂的金屬十字架，邊緣被磨得光亮像是長期被握在手中"},
    {"name": "密封信封", "name_en": "Sealed Envelope", "description": "火漆封印的舊信封，沉甸甸的手感暗示裡面不只是信紙"},
    {"name": "懷錶", "name_en": "Pocket Watch", "description": "指針停留在某個特定時間的老式懷錶，搖晃時能聽到內部有細微的聲響"},
    {"name": "藥瓶", "name_en": "Medicine Bottle", "description": "標籤模糊的深色玻璃藥瓶，內有不明液體或粉末，瓶身上有手寫的警告標記"},
    {"name": "磁帶錄影", "name_en": "VHS Tape", "description": "標有日期和編號的 VHS 錄影帶，外殼上有刮痕和不明污漬"},
    {"name": "鏽蝕徽章", "name_en": "Corroded Badge", "description": "軍事或機構的金屬徽章，鏽蝕嚴重但仍可辨認出圖案和部分文字"},
]

HAZARDS = [
    {"name": "地板塌陷", "name_en": "Floor Collapse", "description": "腐朽的地板在腳下突然碎裂，險些掉入下層空間，需要快速反應才能抓住邊緣"},
    {"name": "毒氣洩漏", "name_en": "Toxic Gas Leak", "description": "空氣中突然充滿刺鼻的化學氣味，呼吸困難需要立即尋找通風口或撤離"},
    {"name": "鏡子異常", "name_en": "Mirror Anomaly Trap", "description": "注視鏡子太久後發現反射中的自己動作有延遲，或者鏡中場景與現實不同"},
    {"name": "門鎖住", "name_en": "Locked In", "description": "進入房間後門被鎖死或卡住，必須在封閉空間內找到其他出路或破解機關"},
    {"name": "手電筒閃爍", "name_en": "Flashlight Malfunction", "description": "唯一的光源開始不穩定閃爍，在完全黑暗的威脅下必須快速找到替代光源"},
    {"name": "天花板崩落", "name_en": "Ceiling Collapse", "description": "頭頂傳來碎裂聲，混凝土或木材碎片開始掉落，必須快速通過危險區域"},
    {"name": "積水觸電", "name_en": "Electrified Water", "description": "地面積水中有裸露的電線，火花在水面上跳動，必須找到繞行或斷電的方法"},
    {"name": "階梯斷裂", "name_en": "Broken Stairway", "description": "樓梯突然斷裂或缺失幾階，面前是黑暗的間隙，需要冒險跳過或尋找替代路線"},
    {"name": "有毒黴菌", "name_en": "Toxic Mold", "description": "牆壁和天花板覆蓋著大片黑色黴菌，孢子在空氣中漂浮，長時間暴露會引起幻覺"},
    {"name": "機關陷阱", "name_en": "Mechanism Trap", "description": "踩到壓力板或觸動機關線，觸發隱藏的陷阱——可能是落石、鐵柵或突然關閉的通道"},
    {"name": "結構不穩", "name_en": "Structural Instability", "description": "整個區域的支撐結構在搖晃，隨時可能完全坍塌，必須在時間壓力下通過"},
    {"name": "密室缺氧", "name_en": "Sealed Room Suffocation", "description": "密封空間中的氧氣逐漸消耗，呼吸變得困難，思維開始模糊，必須盡快找到出口"},
    {"name": "旋轉牆壁", "name_en": "Rotating Wall", "description": "靠在牆上時牆壁突然旋轉，被帶入完全不同的房間，原來的位置已經封閉"},
    {"name": "隱蔽深坑", "name_en": "Hidden Pit", "description": "被碎片或積水覆蓋的地面下是深不見底的坑洞，一步之差就會跌入深淵"},
    {"name": "倒計時裝置", "name_en": "Countdown Device", "description": "發現一個正在倒計時的電子裝置或機械鐘錶，不知道歸零時會發生什麼"},
]

CLUES = [
    {"name": "牆上刻字", "name_en": "Wall Carving", "description": "用尖銳物體刻在牆上的文字，內容是警告、求助或指引方向的信息"},
    {"name": "地圖殘片", "name_en": "Map Fragment", "description": "手繪的建築或區域地圖的一部分，標記了某些重要位置和危險區域"},
    {"name": "前人留言", "name_en": "Previous Explorer's Note", "description": "用粉筆、炭筆或噴漆留下的信息，講述之前探索者的發現和遭遇"},
    {"name": "新聞剪報", "name_en": "News Clipping", "description": "泛黃的報紙剪報，報導了與這個地方相關的事件——事故、失蹤或神秘現象"},
    {"name": "實驗記錄", "name_en": "Experiment Log", "description": "科學實驗的詳細記錄文件，揭示了這個地方曾經進行的研究和其令人不安的結果"},
    {"name": "監控截圖", "name_en": "Surveillance Screenshot", "description": "從監控系統列印出的截圖，在模糊的畫面中可以看到不該存在的人影或異象"},
    {"name": "密碼便條", "name_en": "Password Note", "description": "寫有數字或符號組合的小紙條，可能是保險箱或電子鎖的密碼"},
    {"name": "聲音記錄", "name_en": "Audio Recording", "description": "錄音設備中存儲的對話或環境聲音，內容暗示了某個事件的真相"},
    {"name": "施工圖紙", "name_en": "Blueprint", "description": "建築的原始設計圖紙，揭示了隱藏房間、秘密通道或不在官方記錄中的區域"},
    {"name": "日期標記", "name_en": "Date Marking", "description": "在門框或柱子上刻下的日期序列，最後一個日期之後是空白，暗示某天一切停止了"},
    {"name": "人員名冊", "name_en": "Personnel Roster", "description": "工作人員或實驗對象的名單，某些名字被劃掉或標注了特殊符號"},
    {"name": "手機殘留信息", "name_en": "Phone Message", "description": "破碎但仍有部分功能的手機，裡面留有最後的通話記錄或未發送的簡訊"},
    {"name": "塗改痕跡", "name_en": "Redacted Document", "description": "被大量塗黑的官方文件，從未被遮蓋的部分可以拼湊出令人震驚的信息"},
    {"name": "化學配方", "name_en": "Chemical Formula", "description": "黑板或筆記本上的化學公式和分子結構圖，旁邊標注著危險警示和問號"},
    {"name": "倖存者證詞", "name_en": "Survivor Testimony", "description": "手寫或打字機打出的證詞文件，講述者描述了在這個地方親眼目睹的恐怖經歷"},
]

ATMOSPHERE = [
    {"name": "背景音突變", "name_en": "Ambient Sound Shift", "description": "環境音從低沉的嗡鳴突然轉為刺耳的高頻音，彷彿空間本身在尖叫"},
    {"name": "回音異常", "name_en": "Abnormal Echo", "description": "腳步聲的回音頻率和方向不對勁，像是從不存在的空間反射回來的"},
    {"name": "滴水聲", "name_en": "Dripping Sound", "description": "規律的水滴聲在黑暗中迴盪，成為唯一的時間參照，但偶爾節奏會改變"},
    {"name": "遠處腳步聲", "name_en": "Distant Footsteps", "description": "從遠方傳來清晰的腳步聲，有時靠近有時遠離，但永遠看不到來源"},
    {"name": "無來源低語", "name_en": "Sourceless Murmur", "description": "極其微弱的呢喃聲像是從牆壁深處傳出，偶爾能辨認出單獨的詞語"},
    {"name": "金屬共鳴", "name_en": "Metallic Resonance", "description": "管道或金屬結構突然發出深沉的共鳴聲，持續數秒後慢慢消散"},
    {"name": "風從密室吹出", "name_en": "Wind from Sealed Room", "description": "在完全密封的空間中感到微風吹過，風中帶著不屬於這裡的氣味"},
    {"name": "光源明滅", "name_en": "Light Flickering", "description": "手電筒或環境中的殘餘光源開始不規律閃爍，每次明暗交替時周圍似乎有變化"},
    {"name": "氣味變化", "name_en": "Scent Change", "description": "空氣中突然出現強烈的氣味——焦糊味、花香、血腥味或已經不該存在的味道"},
    {"name": "靜電感", "name_en": "Static Electricity", "description": "頭髮和皮膚上的汗毛因靜電豎立，觸摸金屬表面時能看到微小的電弧"},
    {"name": "時間扭曲感", "name_en": "Time Distortion", "description": "感覺只過了幾分鐘，但手錶顯示已經過了幾個小時，或者反過來"},
    {"name": "壓力感變化", "name_en": "Pressure Change", "description": "耳朵突然感到壓力變化像是坐電梯時的感覺，暗示空間結構正在改變"},
    {"name": "動物聲響", "name_en": "Animal Sounds", "description": "在不該有動物的深處聽到飛翅聲、爪子刮地聲或細微的吱吱叫聲"},
    {"name": "機械啟動聲", "name_en": "Machinery Starting", "description": "廢棄多年的機械突然發出啟動的聲音，齒輪和活塞的節奏在黑暗中迴盪"},
    {"name": "溫度梯度", "name_en": "Temperature Gradient", "description": "通過特定區域時溫度急劇變化，形成明顯的冷熱邊界，像是無形的牆壁"},
    {"name": "振動頻率", "name_en": "Subsonic Vibration", "description": "感受不到但身體能察覺的低頻振動，引起不安、噁心和莫名的恐懼感"},
]

ENDINGS = [
    {"name": "成功逃出", "name_en": "Successful Escape", "description": "在最後關頭找到出口並成功離開，但帶走的東西暗示這一切遠未結束"},
    {"name": "找到寶物", "name_en": "Treasure Found", "description": "在最深處發現了追尋的目標——可能是物品、真相或答案，但代價是什麼"},
    {"name": "發現真相", "name_en": "Truth Revealed", "description": "所有線索拼湊在一起揭示了這個地方的完整故事，真相比想像的更令人不安"},
    {"name": "開放式懸念", "name_en": "Open-Ended Mystery", "description": "離開時留下了未解之謎，某些問題沒有得到回答，觀眾帶著疑問結束觀看"},
    {"name": "循環暗示", "name_en": "Loop Implication", "description": "結局場景暗示探索者可能陷入了某種循環，之前的探索可能不是第一次"},
    {"name": "反轉揭露", "name_en": "Twist Reveal", "description": "最後時刻揭示的信息完全顛覆了之前所有的認知，整個探索的意義被重新定義"},
    {"name": "倖存但改變", "name_en": "Survived but Changed", "description": "雖然活著離開了，但某些東西——聲音、影像或感覺——跟著探索者一起離開了"},
    {"name": "發出求救", "name_en": "Distress Signal Sent", "description": "在最後時刻成功發出了求救信號或將發現傳送出去，等待救援或回應"},
    {"name": "再次進入", "name_en": "Re-Entry", "description": "以為已經逃出但發現自己又回到了起點，或者決定主動返回去完成未竟之事"},
    {"name": "目擊真容", "name_en": "Face to Face", "description": "在最後一刻終於正面遭遇了一直暗示存在的「那個東西」，畫面在這裡結束"},
    {"name": "數據丟失", "name_en": "Data Loss", "description": "帶出的記錄設備故障、影像損毀、照片模糊，沒有人會相信探索者的描述"},
    {"name": "後續預告", "name_en": "Sequel Tease", "description": "成功離開後發現新的線索指向另一個地點，下一次探索的種子被埋下"},
    {"name": "同伴失蹤", "name_en": "Companion Lost", "description": "探索結束時發現同伴不見了，但通訊設備還能收到對方微弱的信號"},
    {"name": "覺醒暗示", "name_en": "Awakening Hint", "description": "結尾暗示整個探索可能是夢境、幻覺或某種實驗的一部分"},
    {"name": "守護者現身", "name_en": "Guardian Appears", "description": "探索的最後階段遇到了這個地方的「守護者」——可能是人、也可能不是"},
]

TENSION_CURVES = [
    {"name": "平靜→升溫→高潮→反轉", "name_en": "Calm-Rise-Climax-Twist", "description": "經典四段式：開場營造氛圍(1-2)→線索累積緊張感(3-4)→遭遇高潮事件(4)→結局反轉(5)"},
    {"name": "恐懼遞增", "name_en": "Escalating Fear", "description": "緊張度從1持續攀升到5，沒有喘息空間，每個區域都比前一個更加恐怖"},
    {"name": "波浪式", "name_en": "Wave Pattern", "description": "緊張-舒緩-緊張-舒緩的交替節奏，讓觀眾在每次放鬆後被更強的恐懼擊中"},
    {"name": "虛假安全", "name_en": "False Security", "description": "前半段刻意營造安全感(1-2)，中段開始不對勁(3)，後半段爆發(4-5)，反差最大化"},
    {"name": "開場衝擊", "name_en": "Opening Shock", "description": "開場直接用強烈事件拉到4-5，然後降到2慢慢展開故事，結尾再次拉高"},
    {"name": "雙高潮", "name_en": "Double Climax", "description": "兩個高潮點：中段一個小高潮(4)讓人以為已經結束，結尾更大的高潮(5)才是真正的衝擊"},
    {"name": "慢燃", "name_en": "Slow Burn", "description": "前 80% 都是低緊張度(1-3)的氛圍營造和線索收集，最後 20% 突然爆發到5"},
    {"name": "持續高壓", "name_en": "Sustained Pressure", "description": "全程維持在 3-4 的高緊張度，沒有明顯的起伏但始終讓人喘不過氣"},
    {"name": "倒敘懸念", "name_en": "Flashback Suspense", "description": "開場展示結局片段(5)，然後回到起點(1)慢慢揭示如何走到那一步"},
    {"name": "階梯式", "name_en": "Staircase Pattern", "description": "每進入新區域緊張度提升一級(1→2→3→4→5)，像爬樓梯一樣穩定遞增"},
    {"name": "過山車", "name_en": "Roller Coaster", "description": "極端的起伏變化(5-1-5-1-5)，在恐懼和舒緩間快速切換，情緒震盪最大化"},
    {"name": "平行線索", "name_en": "Parallel Threads", "description": "兩條故事線交替展開，一條緊張(4-5)一條平靜(1-2)，最後交匯在高潮點"},
    {"name": "迷霧揭開", "name_en": "Fog Clearing", "description": "開場完全的迷茫和困惑(3)，隨著線索收集真相逐漸清晰(2→4)，最終全貌揭示(5)"},
    {"name": "圍困升級", "name_en": "Siege Escalation", "description": "探索者逐漸意識到自己被困住了(2→3→4→5)，每次嘗試離開都發現新的困境"},
    {"name": "心理瓦解", "name_en": "Psychological Breakdown", "description": "緊張度隨著探索者心理狀態變化(1→2→3→4→5)，不確定看到的是真實還是幻覺"},
    {"name": "節拍器", "name_en": "Metronome", "description": "像節拍器一樣精確的節奏：每30秒一個事件點，緊張度在3-4之間規律波動"},
]

ALL_SEED_DATA = {
    "building_types": BUILDINGS,
    "routes": ROUTES,
    "exploration_areas": ZONES,
    "encounters": ENCOUNTERS,
    "items": LOOT,
    "traps": HAZARDS,
    "narrative_clues": CLUES,
    "atmosphere_triggers": ATMOSPHERE,
    "endings": ENDINGS,
    "tension_curves": TENSION_CURVES,
}


def main():
    kb = KnowledgeBase()

    total_added = 0
    for category, items in ALL_SEED_DATA.items():
        logger.info("=== Seeding %s (%d items) ===", category, len(items))
        added = 0
        for item in items:
            name = item.get("name", "")
            if not name:
                continue

            # Skip if similar entry already exists
            existing = kb.find_similar(category, name)
            if existing:
                logger.info("  Skip (exists): %s", name)
                continue

            kb.add_entry(category, {
                "name": name,
                "name_en": item.get("name_en", ""),
                "description": item.get("description", ""),
                "tags": [category],
                "examples": [{
                    "drama_title": "種子數據",
                    "video_id": "",
                    "excerpt": item.get("description", ""),
                    "context": "",
                }],
                "effectiveness_score": 5,
            })
            added += 1
            logger.info("  Added: %s", name)

        total_added += added
        logger.info("%s: added %d items", category, added)

    logger.info("=== Done! Total added: %d items across %d categories ===",
                total_added, len(ALL_SEED_DATA))


if __name__ == "__main__":
    main()
