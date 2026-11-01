"""Presentation-only English/Simplified Chinese catalog; save text stays canonical."""

import re

from events import EFFECTS, EVENTS

LANGUAGES = {"English": "en", "简体中文": "zh_CN"}
RESOURCES = {"Food": "食物", "Energy": "能源", "Materials": "材料",
             "Population": "人口", "Happiness": "幸福度"}
CATALOG = {
    "COLONY ZERO": "COLONY ZERO", "Language": "语言", "New": "新游戏",
    "Demo (seed 7)": "演示（种子7）", "Save": "保存", "Load": "读取",
    "Report": "日报", "Guide": "帮助", "HQ": "总部", "SOL": "发电",
    "FARM": "农场", "MINE": "矿场", "HOME": "住宅", "NEXT: OFFLINE": "将停机",
    "Solar Plant": "太阳能发电站", "Hydroponic Farm": "水培农场",
    "Mining Facility": "采矿设施", "Residential Module": "住宅模块",
    "Headquarters": "总部", "Empty ground": "空地", "None": "无",
    "New Eden": "新伊甸", "Prosperous Colony": "繁荣殖民地",
    "Struggling Outpost": "艰难前哨", "Silent Beacon": "寂静信标",
    "a hopeful community": "充满希望的社区", "a cautious community": "谨慎前行的社区",
    "a weary community": "疲惫的社区", "SURVIVED": "生存成功", "COLONY LOST": "殖民地失守",
    "Welcome, Governor. Build food production before the supplies run out.": "欢迎，总督。请在补给耗尽前建立食物生产设施。",
    "2189  /  A distant world. A small crew. Survive until the supply ship arrives.": "2189年 / 遥远的星球，一支小小的队伍。坚持到补给船抵达。",
    "Growth needs 40+  |  New Eden needs 65+": "人口增长需要40+ | 新伊甸需要65+",
    "THE LANDING SITE": "着陆基地",
    "Select a tile. Build on empty ground; upgrade a facility.": "选择地块：空地可建造，已有设施可升级。",
    "Meals: 1 Food/person. Homes: 1 Energy/day.": "每人每天消耗1食物；每栋住宅每天消耗1能源。",
    "Green = farm/home link. Orange = mine/home noise.": "绿色：农场/住宅增产；橙色：矿场/住宅噪声。",
    "Advance one day  >": "推进一天  >", "Build selected facility": "建造所选设施",
    "Upgrade to L2": "升级至L2", "Maximum level (L2)": "已达最高等级（L2）",
    "COLONY LOG  /  Most recent actions": "殖民地日志 / 最近操作",
    "One build OR upgrade per day. No demolition.": "每天只能新建或升级一次；不能拆除。",
    "One build OR upgrade per day.": "每天只能新建或升级一次。",
    "Ready to build.": "可以建造。",
    "Expedition complete. Start New or Load to continue playing.": "本次远征已结束；请选择新游戏或读取存档。",
    "Council decision required first.": "请先处理议会事件。",
    "Select an empty tile to build.": "请选择空地建造。",
    "Construction used. Advance one day for a fresh crew.": "今天的施工机会已用完；推进一天后恢复。",
    "Build or upgrade used today.": "今天已进行过新建或升级。",
    "Select an empty tile to build, or a facility to upgrade.": "选择空地建造，或选择已有设施升级。",
    "Review the log, save this ending, or start New.": "可查看日志、保存结局，或开始新游戏。",
    "COUNCIL  /  Standing by": "议会 / 等待事件",
    "Decisions: days 2, 4, 6, 9, 12, 14; shuffled order.": "事件出现在第2、4、6、9、12、14天，顺序随机。",
    "Report explains growth, production and temporary effects.": "日报说明人口增长、生产和持续效果。",
    "Guide explains home/farm links and mine noise. Zero people = failure.": "帮助说明相邻增产和矿场噪声；人口归零即失败。",
    "Colony report": "殖民地日报", "Governor's guide": "总督指南",
    "Survive 15 settled days. Build OR upgrade once per day.": "坚持15个结算日；每天只能新建或升级一次。",
    "Each person eats 1 Food/day. Each Home uses 1 Energy/day.": "每人每天吃1食物，每栋住宅每天用1能源。",
    "Power order: HQ, homes, farms, then mines.": "供电顺序：总部、住宅、农场、矿场。",
    "Orthogonal neighbours only (not diagonals):": "相邻只看上下左右，不看对角：",
    "- A powered Farm next to any Home gets +2 Food/day, once per Farm.": "- 有电农场靠近任意住宅，每天额外产2食物；每个农场只计一次。",
    "- Each Home next to any Mine causes -2 Happiness/day; total noise capped at -4.": "- 每个靠近矿场的住宅每天造成-2幸福度；全殖民地噪声最多-4。",
    "Green/orange borders preview these links around your selected tile.": "绿色和橙色边框预览所选地块周围的相邻影响。",
    "Growth every third day needs housing, powered homes, surplus food and Happiness 40+.": "每3天检查人口增长，需要空住房、住宅供电、食物盈余和40+幸福度。",
    "Storms and rover extraction can affect the NEXT 2 or 3 settlements.": "风暴和矿藏开采会影响接下来的2或3次结算。",
    "Read both choices. Late investments may not pay back.": "请比较两项选择；临近结束时投资可能来不及回本。",
    "NEXT: OFFLINE is a power forecast. Report shows the full calculation.": "“将停机”是下一次结算的供电预测；日报提供完整计算。",
    "Action unavailable": "无法执行", "New colony": "新殖民地",
    "Replace the current colony? Save first if you want to keep it.": "要替换当前殖民地吗？如需保留进度，请先保存。",
    "New expedition. One construction action per day: build OR upgrade.": "新的远征开始。每天只有一次施工机会：新建或升级。",
    "No stored-resource change.": "库存资源没有变化。", "Save colony": "保存殖民地",
    "Colony JSON save": "殖民地JSON存档", "All files": "所有文件",
    "Save failed": "保存失败", "Colony saved": "保存成功", "Load colony": "读取殖民地",
    "Load failed": "读取失败", "Your current colony is unchanged.": "当前殖民地保持不变。",
    "Replace the current colony with this save? Unsaved progress will be lost.": "用该存档替换当前殖民地吗？未保存的进度会丢失。",
    "Older save: future turns use V2.0 meals, home power, adjacency and event rules. No past timed effects are invented. Save to a new filename.": "旧版存档：之后使用V2.0的食物、住宅供电、相邻和事件规则；不会补造过去的持续效果。请另存新文件名。",
    "Buildings start at L1, Happiness at 70.": "已有建筑设为L1，幸福度设为70。",
    "Loaded colony. Future event order and construction availability restored.": "已读取殖民地，并恢复事件顺序和施工状态。",
    "Leave Colony Zero": "离开Colony Zero", "Quit? Unsaved progress will be lost.": "确定退出吗？未保存的进度会丢失。",
    "Language changed. Your colony and progress are unchanged.": "语言已切换；殖民地和进度保持不变。",
    "Unsupported interface language.": "不支持该界面语言。",
    "No days settled yet. Each resident needs 1 Food per day.": "尚未结算；每名居民每天需要1食物。",
    "Landing complete. Four pioneers. Fifteen days. One chance.": "着陆完成。四名先驱，十五天，一次机会。",
    "Farm/home link: +2 Food when powered.": "农场/住宅相邻：农场有电时额外产2食物。",
    "No home next door: farm has no adjacency bonus.": "旁边没有住宅：农场没有相邻加成。",
    "Mine noise: -2 Happiness/day.": "矿场噪声：每天-2幸福度。", "No mine noise.": "没有矿场噪声。",
    "Mine next to homes: daily noise penalty (colony cap -4).": "矿场邻近住宅：每天造成噪声损失，全殖民地最多-4。",
    "No homes next door: no mine noise.": "旁边没有住宅：不造成矿场噪声。",
    "Plan homes next to farms and away from mines.": "住宅宜靠近农场，并远离矿场。",
    "This expedition has ended. Start a new colony or load a save.": "本次远征已结束，请开始新游戏或读取存档。",
    "Resolve the council event before building or advancing.": "请先处理议会事件，再建造或推进。",
    "Choose one of the four building types.": "请选择四种建筑中的一种。",
    "That tile is occupied. Select an empty tile.": "该地块已被占用，请选择空地。",
    "The crew can build once per day. Advance to the next day.": "每天只能施工一次，请推进到下一天。",
    "Tile coordinates must be whole numbers.": "地块坐标必须为整数。",
    "Choose a tile inside the map.": "请选择地图内的地块。",
    "Select an existing facility. HQ cannot be upgraded.": "请选择已有设施；总部不能升级。",
    "This facility is already at maximum level (L2).": "该设施已达最高等级L2。",
    "Construction used: building and upgrading share one daily action.": "施工机会已用完：新建和升级共用每天一次的机会。",
    "No survivors remain.": "已没有幸存者。", "Survival losses prevent growth today.": "今天有人死亡，无法增加人口。",
    "Growth paused: Happiness below 40.": "人口增长暂停：幸福度低于40。",
    "Growth paused: no spare housing.": "人口增长暂停：没有空住房。",
    "Growth paused: unpowered housing.": "人口增长暂停：有住宅缺电。",
    "New arrival: +1 Population; settlement supplies -4 Food.": "新居民定居：人口+1，安置补给消耗4食物。",
    "New arrival settled: +1 Population, -4 Food for settlement supplies.": "新居民定居：人口+1，安置补给消耗4食物。",
    "Growth paused: Happiness below 40. Stable supplies and council choices can rebuild trust.": "人口增长暂停：幸福度低于40。稳定供应和事件选择可重建信任。",
    "Expedition ended. No further settlements.": "远征已结束，不再进行结算。",
    "There is no council decision waiting.": "当前没有等待处理的议会事件。",
    "Choose option 1 or 2.": "请选择选项1或2。", "No immediate resource change": "没有即时资源变化",
    "No resource change": "资源没有变化", "No colonists remain. The beacon falls silent.": "居民全部离去，信标归于寂静。",
    "The supply ship has arrived. Your colony survived fifteen days.": "补给船已经抵达，你的殖民地坚持了十五天。",
    "Solar storm": "太阳风暴", "Rover extraction": "探测车开采",
    "Save must be a JSON object.": "存档必须是JSON对象。",
    "Unsupported save version; V2.0 reads versions 1, 2 and 3.": "不支持该存档版本；当前程序支持格式1、2、3。",
    "Missing or unexpected save fields.": "存档字段缺失或包含未知字段。",
    "Map must have five rows.": "地图必须有五行。", "Map rows must have five tiles.": "地图每行必须有五个格子。",
    "Unknown map tile.": "地图包含未知地块。", "Exactly one HQ must occupy the central tile.": "中央地块必须是唯一的总部。",
    "Imported older save: no V2.0 daily report or timed effects were recorded.": "已导入旧版存档：旧版没有记录当前格式的日报和持续效果。",
    "Invalid daily report.": "日报数据无效。", "Unknown timed effects.": "存在未知持续效果。",
    "Invalid effect duration.": "持续效果天数无效。", "Happiness must be a whole number from 0 to 100.": "幸福度必须是0到100的整数。",
    "Levels must have five rows.": "等级矩阵必须有五行。", "Level rows must have five tiles.": "等级矩阵每行必须有五个格子。",
    "Invalid facility level.": "设施等级无效。", "Facility levels do not match map tiles.": "设施等级与地图地块不匹配。",
    "Invalid population.": "人口数据无效。", "Invalid day.": "日期无效。", "Invalid construction flag.": "施工状态无效。",
    "Invalid expedition status.": "远征状态无效。", "Invalid result message.": "结局文本无效。",
    "Event deck must contain all six events exactly once.": "事件列表必须恰好包含六种事件，各一次。",
    "Unknown pending event.": "待处理事件无效。", "Invalid colony log.": "殖民地日志无效。",
    "Population exceeds housing capacity.": "人口超过住房容量。", "Too many construction actions for this day.": "施工次数超过该日期允许的次数。",
    "Construction flag needs a building.": "施工状态与地图建筑不一致。",
    "An ended expedition cannot have a pending construction action.": "已结束的远征不能保留施工操作状态。",
    "Active game has inconsistent survival or day values.": "进行中的游戏，其人口或日期状态不一致。",
    "Victory requires fifteen completed days and survivors.": "胜利必须已完成十五天且仍有居民。",
    "Failure requires no survivors.": "失败状态要求人口归零。",
    "Pending event is inconsistent with this turn.": "待处理事件与当前回合不一致。",
    "Pending event does not match the deck.": "待处理事件与事件顺序不一致。",
    "Timed effect is inconsistent with the event date.": "持续效果与事件发生日期不一致。",
    "Save is too large (maximum 100 KB).": "存档过大，最大允许100KB。",
}

EVENT_ZH = {
    "cold": ("漫长的蓝色霜冻", "寒潮即将抵达着陆点。", ("让加热器继续工作", "保护根系，暂停外围种植")),
    "dust": ("看不见日出的天空", "细尘正在覆盖太阳能阵列。", ("安装阵列防护网", "等待天空放晴")),
    "filters": ("我们呼吸的空气", "生产过滤器需要检修。", ("更换过滤网", "启用备用过滤循环")),
    "community": ("大家坐在同一张桌旁", "居民正在准备共享补给包。", ("预留足额社区补给", "分享较小的储备包")),
    "medical": ("住所里的低烧", "陌生的发烧症状让居民疲惫不堪。要为医疗加热器供电，还是消耗食物储备，让大家慢慢恢复？", ("启动医疗加热器", "休息并使用康复口粮")),
    "festival": ("黑暗中的一盏灯", "居民想举办灯夜庆祝新家。要花补给留下共同回忆，还是让工坊继续加班，生产备用零件？", ("举办灯夜庆典", "工坊加班")),
    "storm": ("天空电光闪烁", "一场持续两天的太阳风暴即将到来。要花材料加装防护，还是依靠储存的能源度过发电下降的时期？", ("保护太阳能阵列", "承受风暴")),
    "immigrants": ("来自轨道的请求", "两名勘探员申请永久定居，需要住房和安置补给。他们的飞船也携带了一些备用零件。", ("欢迎勘探员定居", "发送告别信号")),
    "fault": ("午夜的异响", "储能转换器发生振动。要更换磨损的外壳，还是放空储能并回收可用零件？", ("维修转换器", "放空并回收")),
    "contamination": ("储藏室里的异物", "一批密封食物中发现了外星孢子。要消耗能源加热灭菌，还是丢弃可疑食物？", ("加热灭菌", "丢弃可疑食物")),
    "deposit": ("尘土下的银色矿脉", "探测车发现了矿藏。要投资未来三天的开采，还是立即收集表面碎矿？临近补给船抵达时，投资可能来不及回本。", ("资助探测车开采", "收集表面碎矿")),
    "protest": ("晚餐时的空座位", "一名先驱想离开。要分享一顿特别的晚餐挽留他，还是收回他的口粮，祝他一路顺风？", ("举办殖民地聚餐", "接受居民离开")),
}
for event_id, (title, story, options) in EVENT_ZH.items():
    event = EVENTS[event_id]
    CATALOG[event["title"]] = title
    CATALOG[event["story"]] = story
    for option, label in zip(event["options"], options):
        CATALOG[option["label"]] = label
CATALOG[EFFECTS["solar_storm"]["description"]] = "接下来2天太阳能总发电量减半（向下取整）"
CATALOG[EFFECTS["ore_rush"]["description"]] = "接下来3天，只要有矿场供电，每天额外获得4材料"

from narrative import STORIES, REACTIONS, EXTRA_TEXT
CATALOG.update(EXTRA_TEXT)
CATALOG["+8 Materials/week for next 3 weeks if any mine is powered"] = "接下来3周，只要有矿场供电，每周额外获得8材料"
CATALOG.update({"Motion: on": "动态：开启", "Motion: reduced": "动态：减少", "Sound: on": "音效：开启",
                "Sound: off": "音效：关闭", "Opening costs unchanged.": "开荒阶段费用保持不变。",
                "All encounters resolved. Finish the beacon.": "全部事件已处理，请完成信标。"})
for title, title_zh, story, story_zh in STORIES.values():
    CATALOG.update({title: title_zh, story: story_zh})
for reactions in REACTIONS.values():
    CATALOG.update(dict(reactions))
CATALOG.update({
    EFFECTS["cold_snap"]["description"]: "接下来2周农场产量为75%（每座向下取整）",
    EFFECTS["dust_cloud"]["description"]: "接下来3周太阳能为50%（不与风暴叠加）",
    EFFECTS["filter_load"]["description"]: "接下来3周每座有电农场/矿场额外消耗1能源",
    "Invalid campaign ruleset.": "远征规则版本无效。",
    "Event deck violates opening or recovery spacing.": "事件顺序违反开荒或恢复间隔规则。",
    "Legacy campaign has new effects.": "旧版远征包含不适用的新效果。",
    "Invalid locked council offer.": "锁定的议会选项无效。", "Unexpected council offer.": "存在不应出现的议会选项。",
    "Unsupported save version; V3.1 reads versions 1 through 5.": "不支持的存档版本；当前支持格式1至5。",
})

CATALOG.update({
    "Stranded Colony": "失联殖民地",
    "Four pioneers. Thirty days. Repair the beacon before the ship passes.": "四名先驱，三十天。请在补给船经过前修复信标。",
    "Growth needs 40+  |  New Eden needs 80+": "人口增长需要40+ | 新伊甸需要80+",
    "Work on HQ beacon": "修复总部信标",
    "Daily crew action used today.": "今天的施工机会已用完。",
    "Legacy expedition: the beacon objective is not required.": "旧版远征不需要完成信标任务。",
    "Beacon ready. Keep the colony alive until Day 30.": "信标就绪。请让殖民地坚持到第30天。",
    "The crew is busy. HQ work shares the daily construction action.": "施工队正忙。总部任务与建筑共用每日施工机会。",
    "Emergency rationing is already active for the next settlement.": "下一次结算已经启用应急配给。",
    "Both emergency ration orders have been used.": "两次应急配给机会均已用完。",
    "Emergency rations: next meals halved (round up), growth paused; Happiness -8 (floor 0).": "应急配给：下次口粮消耗减半（向上取整），暂停人口增长；幸福度-8（最低0）。",
    "Legacy expedition: survive 15 days; beacon not required.": "旧版远征：生存15天，不需要信标。",
    "Beacon 3/3 READY | Survive until Day 30.": "信标3/3已就绪 | 请坚持到第30天。",
    "The crew channel is silent.": "居民频道已归于寂静。",
    "We survived, but the ship never received our coordinates.": "我们活下来了，但飞船没能收到我们的坐标。",
    "Our next meal is at risk. Can we ration or power a farm?": "下一顿饭没有保障。能启动配给，或给农场供电吗？",
    "The lights are going out. Check our power supply.": "灯正在熄灭，请检查电力供应。",
    "The ship is getting close. Please finish the beacon.": "补给船快到了，请尽快修复信标。",
    "We need hope before more people can settle here.": "我们需要先重拾希望，才能吸引更多居民。",
    "This is becoming a place we can call home.": "这里正在成为我们可以称作家的地方。",
    "Growth paused: emergency rations this settlement.": "人口增长暂停：本次结算采用应急配给。",
    "Day 30: the supply ship passed without a completed beacon. The colony is stranded.": "第30天：信标未完成，补给船驶过，殖民地陷入失联。",
    "Day 30: your beacon guides the supply ship home. The colony is saved.": "第30天：信标指引补给船抵达，殖民地获救。",
    "The survivors built a home, but missed their only rescue window. Finish all three HQ stages next time.": "幸存者建起了家园，却错过唯一的救援窗口。下次请完成总部的全部三个阶段。",
    "Legacy: six events over 15 days.": "旧版远征：15天，共六类事件。",
    "Eight encounters: days 2, 5, 9, 13, 17, 21, 25, 28.": "八次事件：第2、5、9、13、17、21、25、28天。",
    "Repair all three beacon stages before Day 30.": "请在第30天前完成信标的三个阶段。",
    "Survive 30 days AND finish all three HQ beacon stages.": "生存30天，并完成总部信标的全部三个阶段。",
    "One daily crew action: build, upgrade OR HQ work.": "每日一次施工：新建、升级或总部任务，三选一。",
    "HQ unlocks after days 6, 14, 22; costs 18/28/36 Materials and 8/18/32 Energy.": "总部任务在第6、14、22天结算后解锁，依次需要18/28/36材料和8/18/32能源。",
    "HQ work gives +3 Happiness per stage (cap 100).": "每完成一个总部阶段，幸福度+3（上限100）。",
    "Rations: twice per game, next meals halved (round up), -8 Happiness, no growth that day.": "应急配给：每局两次，下次口粮消耗减半（向上取整），幸福度-8，当天不增长人口。",
    "Growth every fourth day needs housing, powered homes, surplus food and Happiness 40+.": "每4天检查人口增长，需要空住房、住宅供电、食物盈余和40+幸福度。",
    "Quiet days move Happiness one point toward 78; events can raise it higher.": "平稳日幸福度每天向78靠近1点；事件可将其提高到78以上。",
    "Legacy imports keep 15 days, six events, third-day growth and their original Happiness recovery.": "旧存档保留15天期限、六类事件、每3天增长检查及原有幸福度恢复规则。",
    "Older save: the original 15-day campaign and six-event deck are preserved; no beacon is required. Existing timed effects are retained for schema 3. Save to a new filename.": "旧存档保留原来的15天期限和六类事件，不需要完成信标；格式3保留已有持续效果。建议另存为新文件。",
    "Unsupported save version; V3.0 reads versions 1, 2, 3 and 4.": "不支持的存档版本；当前支持格式1、2、3、4。",
    "Invalid campaign length.": "远征天数无效。", "Invalid beacon stage.": "信标阶段无效。",
    "Invalid emergency ration counters.": "应急配给次数或天数无效。",
    "Ration order has no recorded use.": "应急配给缺少使用记录。",
    "Legacy campaign cannot contain beacon work.": "旧版远征不能包含信标施工进度。",
    "Event deck must contain every campaign event exactly once.": "事件顺序必须恰好包含该远征的每类事件，各一次。",
    "Beacon stage is not unlocked yet.": "信标阶段尚未解锁。",
    "Failure requires no survivors or a missed beacon deadline.": "失败状态要求人口归零或错过信标期限。",
    "An ended expedition cannot have active emergency rations.": "结束后的远征不能保留待结算配给。",
    "Rations must settle before a council event.": "配给必须在议会事件前完成结算。",
    "Too many ration orders for this day.": "配给使用次数超过当前天数允许的次数。",
    "All eight encounters resolved. Finish the beacon.": "八次事件均已处理，请完成信标。",
    "Victory requires the campaign deadline, survivors and the required beacon.": "胜利需要完成远征天数、保有居民并完成所需信标任务。",
})


from polish import STORY_VARIANTS, BULLETINS, TEXT as POLISH_TEXT, ERRORS as POLISH_ERRORS
CATALOG.update(POLISH_TEXT)
CATALOG.update(POLISH_ERRORS)
CATALOG.update({
    'Read history':'阅读历史', 'Colony history':'殖民地历史',
    'Select a Farm or Mine to manage next-week production.':'选择农场或矿场，安排下一周生产。',
    'COLONY CHRONICLE':'殖民地纪事', 'Pause production':'暂停生产',
    'Resume production':'恢复生产', 'PAUSED BY YOU':'主动停用', 'RUNNING':'运行中',
    'Only Farms and Mines can be paused.':'仅农场和矿场可暂停生产。',
    'Production controls require a new V3.3 expedition.':'生产控制需要开始V3.3新版远征。',
    'Paused: no power or output. No crew action; timers continue.':'停用不耗电、不产出，不占施工；效果正常计时。',
    'Open Report for the full settlement calculation.':'打开周报可查看完整结算计算。',
    'Pause/resume Farms or Mines without a crew action. Paused sites use no power and produce nothing; timers continue.':
        '暂停/恢复农场或矿场不占施工。停用设施不耗电、不产出，效果正常计时。',
    'Invalid production switches.':'生产开关数据无效。',
    'Switch does not match a controllable facility.':'开关与可控制设施不一致。',
    'Older format cannot contain V3.3 rules.':'旧格式不能包含V3.3规则。',
    'Unsupported save version; V3.3 reads versions 1 through 7.':'不支持的存档版本；当前支持格式1至7。',
})
CATALOG.update({
    'Finish the beacon by Week 29, before advancing into Week 30.':'请在第29周完成信标，再推进至第30周。',
    'Locked quote. No inventory tax.':'报价已锁定，库存不加罚。',
    'Open Report for the colony record and rating targets.':'打开周报查看基地经历和评级条件。',
})
for title, title_zh, story, story_zh in STORY_VARIANTS.values():
    CATALOG.update({title:title_zh,story:story_zh})
CATALOG.update(dict(BULLETINS.values()))


def _resources(text):
    """Replace resource terms only inside known numeric messages, never paths."""
    return re.sub(r"\b(Food|Energy|Materials|Population|Happiness)\b",
                  lambda match: RESOURCES[match[0]], text)


def weekly_chinese(text):
    """Convert units, preserving words such as sky (天空) and file paths."""
    if "\\" in text or ".json" in text:
        return text
    text = text.replace("日报", "周报").replace("今天", "本周").replace("每天", "每周").replace("每日", "每周").replace("本日", "本周").replace("次日预测", "下周预测")
    return re.sub(r"(\d+|十五|三十|一|两|三)天", r"\1周", text)


def translate(text, language="en"):
    """Translate known canonical messages; preserve unknown OS details verbatim."""
    if language not in ("en", "zh_CN"):
        raise ValueError("Unsupported interface language.")
    text = str(text)
    if language == "en" or not text:
        return text
    if text in CATALOG:
        return CATALOG[text]
    if "\n" in text:
        return "\n".join(translate(line, language) for line in text.split("\n"))
    if "; " in text and (any(effect["description"] in text for effect in EFFECTS.values()) or '+8 Materials/week' in text):
        return "；".join(translate(part, language) for part in text.split("; "))
    # Weekly saves use canonical Week wording; reuse validated day templates.
    # Unknown external text/paths are returned verbatim, never rewritten.
    if "\\" not in text and ".json" not in text and re.search(r"\b(?:Week|week|weeks|Weeks|weekly)\b", text):
        normalized = re.sub(r"\b(?:Week|week|weeks|Weeks|weekly)\b",
                            lambda m: {"Week":"Day", "week":"day", "weeks":"days", "Weeks":"Days", "weekly":"daily"}[m[0]], text)
        localized = translate(normalized, language)
        if localized != normalized:
            return weekly_chinese(localized)
    if "\n" in text:
        return "\n".join(translate(line, language) for line in text.split("\n"))
    if text != text.strip():
        return translate(text.strip(), language)
    t = lambda value: translate(value, language)
    patterns = [
        (r'COLONY CHRONICLE / Week (\d+)', lambda m: f'殖民地纪事 / 第{m[1]}周'),
        (r'Production ([A-E][1-5]): (PAUSED|RUNNING)\.', lambda m: f'生产设施{m[1]}：'+('已停用。' if m[2]=='PAUSED' else '已恢复。')),
        (r'Paused by you: (\d+)\. No power or output; timers continue\.', lambda m: f'主动停用：{m[1]}栋。不耗电、不产出；效果正常计时。'),
        (r'After (\d+) weeks, the landing site is silent\. No one answers the final signal\.',lambda m:f'第{m[1]}周后，着陆点归于寂静，最后一次信号无人回应。'),
        (r'Ration settlement: Day (\d+)\.',lambda m:f'配给生效结算：第{m[1]}天。'),
        (r'Meals (\d+) -> (\d+); Happiness (\d+) -> (\d+)\.',lambda m:f'口粮{m[1]} → {m[2]}；幸福度{m[3]} → {m[4]}。'),
        (r'Expected losses (\d+) -> (\d+)\.',lambda m:f'预计损失居民{m[1]} → {m[2]}。'),
        (r'Orders remaining before use: (\d+)\.',lambda m:f'使用前剩余次数：{m[1]}。'),
        (r'Rations ACTIVE: settlement (\d+) \((\d+) left\)',lambda m:f'配给已启用：第{m[1]}次结算（剩{m[2]}次）'),
        (r'Next: Food ([+-]\d+), Energy ([+-]\d+); losses (\d+)\.',lambda m:f'下次：食物{m[1]}，能源{m[2]}；损失居民{m[3]}。'),
        (r'Unlock: Week (\d+)\.',lambda m:f'第{m[1]}周解锁。'),
        (r'Need (\d+) more Materials / (\d+) more Energy\.',lambda m:f'还缺{m[1]}材料/{m[2]}能源。'),
        (r'Goal: survive \+ Beacon (\d)/3 \| (\d+)M \+ (\d+)E \| (.+) By Week 29\.',lambda m:f'目标：生存+信标{m[1]}/3 | {m[2]}材料+{m[3]}能源 | {t(m[4])} 期限第29周。'),
        (r'Life record: the first home lit up in Week (\d+)\.',lambda m:f'生活记录：第一间住宅在第{m[1]}周亮灯。'),
        (r'Engineering record: beacon completed in Week (\d+)\.',lambda m:f'工程记录：信标在第{m[1]}周完成。'),
        (r'Life record: (\d+) surveyors welcomed; (\d+) survival losses avoided by rationing\.',lambda m:f'生活记录：接纳{m[1]}名勘探员；配给累计避免{m[2]}次居民损失。'),
        (r"Next (week|day) ([+-]\d+)", lambda m: ("下周预测 " if m[1] == "week" else "次日预测 ") + m[2]),
        (r"Weather loss: (\d+) Food; filter power included: (\d+) Energy\.", lambda m: f"天气减产：{m[1]}食物；已计入过滤额外耗电：{m[2]}能源。"),
        (r"(Farms 75%|Solar 50% \(dust\)|Farm/Mine power \+1): (\d+) day\(s\)", lambda m: f"{t(m[1])}：剩余{m[2]}天"),
        (r"Next encounter: Day (\d+)\.", lambda m: f"下一次事件：第{m[1]}天。"),
        (r"Next beacon stage unlocks after Day (\d+)\.", lambda m: f"下个信标阶段在第{m[1]}天结算后解锁。"),
        (r"Beacon stage (\d)/3 complete: -(\d+) Materials, -(\d+) Energy; Happiness \+3 \(cap 100\)\.", lambda m: f"信标第{m[1]}/3阶段完成：材料-{m[2]}，能源-{m[3]}；幸福度+3（上限100）。"),
        (r"Beacon (\d)/3 \| Next: (\d+) Materials \+ (\d+) Energy \| Unlock: Day (\d+) \| Deadline: Day 30", lambda m: f"信标{m[1]}/3 | 下阶段：{m[2]}材料+{m[3]}能源 | 第{m[4]}天解锁 | 期限：第30天"),
        (r"Emergency rations \((\d) left\)", lambda m: f"应急配给（剩{m[1]}次）"),
        (r"Milestone: Day (\d+); (\d+) pioneers still together\.", lambda m: f"里程碑：第{m[1]}天，{m[2]}名先驱仍在一起。"),
        (r"Day (\d+) / (\d+)", lambda m: f"第{m[1]}天 / {m[2]}"),
        (r"(Food|Energy|Materials|Population|Happiness)\s+([+-]?\d+)( / \d+|/100)?", lambda m: f"{RESOURCES[m[1]]}  {m[2]}{m[3] or ''}"),
        (r"(.+)\s+\|\s+(\d+) Materials", lambda m: f"{t(m[1].strip())} | {m[2]}材料"),
        (r"Next settlement: (.+)", lambda m: "下次结算：" + _resources(m[1])),
        (r"Meals: (\d+)/day; offline: (\d+)\. (.+)", lambda m: f"每日口粮：{m[1]}；缺电设施：{m[2]}。{t(m[3])}"),
        (r"Active effects: (.+)\. Forecast includes growth; excludes new council choices\.", lambda m: f"持续效果：{t(m[1])}。预测包含人口增长，不含新的事件选择。"),
        (r"Expedition complete\. (.+) \| Score (\d+)", lambda m: f"远征结束。{t(m[1])} | 分数 {m[2]}"),
        (r"Last action: (.+)", lambda m: "上次操作：" + t(m[1])),
        (r"Tile ([A-E][1-5]): (.+)", lambda m: f"地块{m[1]}：{t(m[2])}"),
        (r"Build L1: (.+)", lambda m: "新建L1：" + t(m[1])),
        (r"L([12]): (.+)", lambda m: f"L{m[1]}：{t(m[2])}"),
        (r"Upgrade: (\d+) Materials -> (.+)", lambda m: f"升级：{m[1]}材料 → {t(m[2])}"),
        (r"Upgrade: (\d+) Materials", lambda m: f"升级：{m[1]}材料"),
        (r"\+(\d+) Energy/day", lambda m: f"每天产{m[1]}能源"),
        (r"\+(\d+) housing", lambda m: f"增加{m[1]}住房"),
        (r"(\d+) Energy/day", lambda m: f"每天消耗{m[1]}能源"),
        (r"(\d+) Energy -> (\d+) (Food|Materials)/day", lambda m: f"每天用{m[1]}能源产{m[2]}{RESOURCES[m[3]]}"),
        (r"Home neighbours: (\d+) farm\(s\)\. (.+)", lambda m: f"相邻农场：{m[1]}栋。{t(m[2])}"),
        (r"COUNCIL  /  (.+)", lambda m: "议会 / " + t(m[1])),
        (r"(SURVIVED|COLONY LOST)  /  (.+)", lambda m: t(m[1]) + " / " + t(m[2])),
        (r"Score: (\d+) \| Survivors: (\d+)", lambda m: f"分数：{m[1]} | 幸存者：{m[2]}"),
        (r"([12])\. (.+)", lambda m: f"{m[1]}. {t(m[2])}"),
        (r"(.+?)  \[Unavailable: (.+)\]", lambda m: f"{t(m[1])}  [无法选择：{t(m[2])}]"),
        (r"pay (\d+) (Food|Energy|Materials)", lambda m: f"支付{m[1]}{RESOURCES[m[2]]}"),
        (r"lose up to (\d+) (Food|Energy|Materials)", lambda m: f"最多失去{m[1]}{RESOURCES[m[2]]}"),
        (r"Solar 50%: (\d+) day\(s\)", lambda m: f"太阳能50%：剩余{m[1]}天"),
        (r"Mine bonus \+([48]) Materials: (\d+) day\(s\)", lambda m: f"矿场奖励+{m[1]}材料：剩余{m[2]}天"),
        (r"Need (\d+) (Food|Energy|Materials); (?:only )?(\d+) available\.", lambda m: f"需要{m[1]}{RESOURCES[m[2]]}，当前只有{m[3]}。"),
        (r"Need (\d+) (Food|Energy|Materials)\.", lambda m: f"需要{m[1]}{RESOURCES[m[2]]}。"),
        (r"Need housing for (\d+) people; capacity is (\d+)\.", lambda m: f"需要容纳{m[1]}人的住房，当前容量为{m[2]}。"),
        (r"Invalid (food|energy|materials) value\.", lambda m: f"{RESOURCES[m[1].title()]}数值无效。"),
        (r"Could not (save|load) colony: (.+)", lambda m: ("无法保存殖民地：" if m[1] == "save" else "无法读取殖民地：") + t(m[2])),
        (r"Saved to (.+)", lambda m: "已保存至 " + m[1]),
        (r"Next growth check: Day (\d+)\.", lambda m: f"下次人口增长检查：第{m[1]}天。"),
        (r"Growth paused: need (\d+) Food after meals\.", lambda m: f"人口增长暂停：用餐后需要至少{m[1]}食物。"),
        (r"NEXT: DAY (\d+) \(before a new council choice\)", lambda m: f"预测：第{m[1]}天（不含新的事件选择）"),
        (r"SETTLED: DAY (\d+)", lambda m: f"已结算：第{m[1]}天"),
        (r"Food: \+(\d+) produced \(home links \+(\d+)\); meals -(\d+)\.", lambda m: f"食物：产出+{m[1]}（住宅相邻加成+{m[2]}），口粮消耗{m[3]}。"),
        (r"Energy: HQ \+2, Solar \+(\d+); life support -2, homes -(\d+), facilities -(\d+)\.", lambda m: f"能源：总部+2，太阳能+{m[1]}；生命维持-2，住宅-{m[2]}，生产设施-{m[3]}。"),
        (r"Materials: \+(\d+) produced \(ore bonus \+(\d+)\)\.", lambda m: f"材料：产出+{m[1]}（矿藏奖励+{m[2]}）。"),
        (r"Offline sites: (\d+); food shortfall: (\d+); colonists lost: (\d+)\.", lambda m: f"缺电设施：{m[1]}；食物短缺：{m[2]}；损失居民：{m[3]}。"),
        (r"Happiness: (\d+) -> (\d+) \(mine noise -(\d+)/day\)\.", lambda m: f"幸福度：{m[1]} → {m[2]}（矿场噪声每天-{m[3]}）。"),
        (r"After settlement: Food (\d+), Energy (\d+), Materials (\d+), Population (\d+)\.", lambda m: f"结算后：食物{m[1]}，能源{m[2]}，材料{m[3]}，人口{m[4]}。"),
        (r"Effects used this day: (.+)", lambda m: "本日采用的持续效果：" + t(m[1])),
        (r"Day (\d+): Food \+(\d+) / meals -(\d+); Materials \+(\d+); Energy reserve (\d+); Happiness (\d+)\.", lambda m: f"第{m[1]}天：食物产出+{m[2]}、口粮-{m[3]}；材料+{m[4]}；能源储备{m[5]}；幸福度{m[6]}。"),
        (r"Crisis: food shortfall (\d+); offline (\d+); deaths (\d+)\.", lambda m: f"危机：食物短缺{m[1]}，缺电设施{m[2]}，损失居民{m[3]}。"),
        (r"Build: (.+) at \((\d+), (\d+)\); -(\d+) Materials\.", lambda m: f"建造：{t(m[1])}，坐标（{m[2]}，{m[3]}），材料-{m[4]}。"),
        (r"Upgrade: (.+) at \((\d+), (\d+)\) to L2; -(\d+) Materials; (.+)\.", lambda m: f"升级：{t(m[1])}，坐标（{m[2]}，{m[3]}），升至L2；材料-{m[4]}；{t(m[5])}。"),
        (r"Council alert: (.+)\.", lambda m: "议会警报：" + t(m[1]) + "。"),
        (r"Effect ended: (.+)\.", lambda m: "效果结束：" + t(m[1]) + "。"),
        (r"Council: (.+?)\. (.+)", lambda m: "议会决定：" + t(m[1]) + "。" + t(m[2])),
        (r"(.+?)\. Active effects: (.+)\.", lambda m: t(m[1]) + "。持续效果：" + t(m[2]) + "。"),
        (r"(No immediate resource change|No resource change)\.", lambda m: t(m[1]) + "。"),
        (r"(\d+) pioneers now call this world home: (.+?)\. Your (\d+) facilities include (\d+) L2 upgrades\. The supply ship finds (\d+) Food and (\d+) Materials in reserve\.", lambda m: f"{m[1]}名先驱已在这颗星球安家，形成{t(m[2])}。{m[3]}栋设施中有{m[4]}栋L2；补给船抵达时，库存还有{m[5]}食物和{m[6]}材料。"),
        (r"After (\d+) days, the landing site is silent\. Its empty homes are a reminder: expansion needs a food supply\.", lambda m: f"第{m[1]}天后，着陆基地归于寂静。空荡荡的住宅提醒着后来者：扩张必须有粮食支撑。"),
        (r"Community: Happiness ([+-]\d+) -> (\d+)/100\.", lambda m: f"社区：幸福度{m[1]}，现为{m[2]}/100。"),
        (r"Day (\d+): (\d+) farm\(s\), (\d+) mine\(s\) powered; Food \+(\d+) / -(\d+); Materials \+(\d+); Energy reserve (\d+)\.", lambda m: f"第{m[1]}天：{m[2]}农场、{m[3]}矿场有电；食物+{m[4]}、消耗{m[5]}；材料+{m[6]}；能源储备{m[7]}。"),
        (r"Power shortage: (\d+) facility/facilities offline \(farms have priority\)\.", lambda m: f"缺电：{m[1]}栋设施停机（农场优先供电）。"),
        (r"Survival crisis: (\d+) colonist\(s\) lost; food shortfall (\d+)\.", lambda m: f"生存危机：损失{m[1]}名居民，食物短缺{m[2]}。"),
    ]
    for pattern, render in patterns:
        match = re.fullmatch(pattern, text)
        if match:
            return render(match)
    # Remaining compound messages contain numeric resource effects only.
    if "   |   " in text:
        return " | ".join(t(part) for part in text.split("   |   "))
    if "; " in text and not ("\\" in text or "/" in text[:3]):
        return "；".join(t(part) for part in text.split("; "))
    if re.fullmatch(r"(?:Food|Energy|Materials|Population|Happiness) [+-]\d+(?:, (?:Food|Energy|Materials|Population|Happiness) [+-]\d+)*\.?", text):
        return _resources(text).removesuffix(".") + ("。" if text.endswith(".") else "")
    # Migration notices may combine two known sentences on one line.
    if text.endswith(" Buildings start at L1, Happiness at 70."):
        return t(text.removesuffix(" Buildings start at L1, Happiness at 70.")) + " " + t("Buildings start at L1, Happiness at 70.")
    return text
