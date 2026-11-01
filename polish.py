"""Presentation text and non-economic story variants for the V3.2 expedition."""

STORY_VARIANTS = {
    'storm': ('A Line Across the Sky','天空中的一道线',
        'The radio crackles before anyone sees the light. A bright line is moving over the ridge. For two weeks the arrays will need protection or patient use of stored power. Someone tapes a simple reminder beside the switch: leave enough for the lights.',
        '还没看到闪光，电台已先响起杂音。一道亮线正越过山脊。未来两周，阵列需要防护，或谨慎使用储能。有人在开关旁贴了张纸条：给灯留一点电。'),
    'medical': ('A Quiet Shift','安静的一班',
        'The shift begins more quietly than usual. Cups of water wait beside the sleeping area, and someone has folded the spare blankets. A powered medical heater could help the crew recover. Rest and recovery rations would keep the machinery bill smaller, but draw on food.',
        '这一班比平时安静。休息区旁摆着水杯，备用毯子已被叠好。医疗加热器能帮助大家恢复；休息和康复口粮能省些设备费用，却要消耗食物。'),
    'festival': ('The Evening We Kept','留下的那个夜晚',
        'A paper sign appears beside HQ: tools down after supper? The crew has kept a few tiny lights for an evening like this. A shared celebration would cost supplies. Another workshop shift would bring useful parts. Both plans say something about the place you are building.',
        '总部旁多了张纸条：晚饭后可以放下工具吗？大家为这样的夜晚留了几盏小灯。共同庆祝需要补给，加一班则能换来零件。两种安排，都在塑造这个地方。'),
    'fault': ('The Part on the Table','桌上的那个零件',
        'A worn casing sits beside the converter log. The technician has drawn a small circle around the crack. Repairing it would protect the stored charge. Draining it would make reusable parts available now. The crew waits to hear which resource matters more this week.',
        '磨损的外壳被放在转换器记录旁，技术员在裂缝周围画了个圈。维修能保住储能，放空则能立刻回收零件。施工队等着知道：这周哪种资源更重要？'),
    'immigrants': ('Room Beside the Door','门旁的位置',
        'The nearby survey team sends two names and asks if they should cross the valley. Their small shuttle can reach the landing site, but cannot take them home. Welcoming them means more meals and a larger community. A farewell signal would keep the colony smaller.',
        '附近勘探队发来两个名字，询问是否可以穿过山谷。他们的小飞船能抵达着陆点，却无法带他们返乡。接纳意味着更多口粮和更大的社区，告别则能维持较小规模。'),
    'community': ('Names on the Crates','箱子上的名字',
        'There is a name on every supply crate. Some are written carefully over older tape. The residents want to prepare a full allocation for the weeks ahead. A smaller shared pack would save food. The argument is quiet, but everyone is listening.',
        '每只补给箱上都有一个名字，有些认真写在旧胶带上。居民希望为接下来的几周准备足额补给。小份共享包可以省粮。讨论很轻，但每个人都在听。'),
}

BULLETINS = {
    'week4': ('Engineering record: the map now has paths made by footsteps. We are beginning to know the ground.', '工程记录：地图上的道路开始有了脚印的形状。我们正逐渐熟悉这里。'),
    'week8': ('Life record: someone marks our eighth week on a supply crate. A calendar can begin almost anywhere.', '生活记录：有人在补给箱上记下第八周。日历可以从任何地方开始。'),
    'week11': ('Engineering record: a clear silence between radio checks. We keep listening.', '工程记录：两次电台测试之间，是清晰的寂静。我们继续倾听。'),
    'week19': ('Life record: supper is being discussed before the shift ends. Small routines can make unfamiliar places gentler.', '生活记录：还没下班，大家已开始讨论晚餐。小小的习惯，让陌生地方温柔了一些。'),
    'week23': ('Engineering record: the approach checklist is on the wall. A signal must be ready before a ship can answer.', '工程记录：接应清单贴在墙上。先准备好信号，飞船才能回应。'),
    'week27': ('Life record: we leave a little space on the noticeboard for news. Waiting is work of its own.', '生活记录：公告板上为新消息留了一点位置。等待也是一种工作。'),
}

TEXT = {
    'Build / upgrade / HQ share one crew action.':'新建/升级/总部共用一次施工。',
    'Hover or focus Emergency rations to see its effects.':'悬停或聚焦应急配给，可提前查看效果。',
    'Close':'关闭','Confirm':'确认','Back':'返回', 'Ration preview':'应急配给预览',
    'Activate rations':'启用应急配给','Continue anyway':'仍然推进',
    'Next settlement only: meals halved (round up), Happiness -8, no growth.':'仅下一次结算：口粮减半（向上取整），幸福度-8，暂停增长。',
    'Two orders per expedition. No crew action. No Food is created.':'每局两次，不占施工机会，不会产生食物。',
    'Cancel leaves resources and remaining orders unchanged.':'返回不会扣除资源或配给次数。',
    'Signal deadline':'信标截止提醒',
    'Advancing into Week 30 without beacon 3/3 ends this expedition as Stranded Colony.':'信标未达3/3时推进到第30周，本次远征将以失联殖民地结束。',
    'Return to inspect the colony, or continue knowing the outcome. No automatic repair is performed.':'可返回查看基地，或知情后仍推进。系统不会自动修复。',
    'Too few crew opportunities remain.':'剩余施工机会已不足。',
    'READY TO REPAIR':'可修复',
    'Goal: survive to Week 30. Beacon 3/3 READY.':'目标：存活到第30周，信标3/3已就绪。',
    'Beacon reminder: a new HQ stage is unlocked. Finish all stages by Week 29.':'信标提醒：新的总部阶段已解锁，请在第29周前完成全部阶段。',
    'Legacy expedition: no new historical memories are invented.':'兼容模式：不补写未记录的历史经历。',
    'New Eden: Population 13+, Happiness 80+, Score 390+.':'新伊甸：人口13+、幸福度80+、分数390+。',
    'Prosperous Colony: Population 11+, Happiness 65+, Score 300+.':'繁荣殖民地：人口11+、幸福度65+、分数300+。',
    'This choice ends the colony.':'此选择将结束殖民地。',
    'Sound starts off. Switch it on for short action cues.':'音效默认关闭，可开启体验短操作提示。',
    'V3.2 late choices: arrivals bring 6 Materials; converter repair gives 4 Energy; full community supply gives 12 Happiness.':'新版中后期选择：接纳移民贡献6材料，维修转换器获得4能源，足额社区补给获得12幸福度。',
    'Late cost weights: Immigration F1; Fault M1; Community F2/E1. Other weights unchanged.':'中后期费用权重：移民食物1，故障材料1，社区食物2/能源1；其余不变。',
}

ERRORS = {
    'Unsupported save version; V3.2 reads versions 1 through 6.':'不支持的存档版本；当前支持格式1至6。',
    'Invalid story seed.':'故事种子无效。','Invalid colony memories.':'基地经历记录无效。',
    'Invalid memory date.':'经历记录日期无效。','Invalid memory counters.':'经历计数无效。',
    'Invalid bulletin history.':'通讯历史无效。','Bulletin is from a future week.':'通讯日期晚于当前周。',
    'Home memory does not match the map.':'住宅经历与地图不一致。','Beacon memory does not match progress.':'信标经历与进度不一致。',
    'Beacon memory predates unlock.':'信标经历早于解锁。','Ration memory has no order.':'配给经历没有使用记录。',
    'Immigration memory predates the choice.':'移民经历早于实际选择。','Legacy memories must remain empty.':'旧存档的新经历字段必须为空。',
}
