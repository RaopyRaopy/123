"""
City attraction database with rich tags for keyword matching.
Each spot: (name, tags, morning, afternoon, evening)
"""

import re

CITY_SPOTS: dict[str, list[dict]] = {
    "重庆": [
        {"name": "解放碑与山城巷", "tags": ["城市", "夜景", "美食", "小众"],
         "morning": "山城巷台阶慢走", "afternoon": "十八梯和白象居机位", "evening": "解放碑周边轻松觅食"},
        {"name": "鹅岭二厂", "tags": ["文创", "城市", "风景", "小众"],
         "morning": "二厂文创街区", "afternoon": "鹅岭公园看江景", "evening": "佛图关步道轻徒步"},
        {"name": "李子坝与嘉陵江", "tags": ["城市", "风景", "美食", "夜景"],
         "morning": "李子坝轻轨观景", "afternoon": "嘉陵江边散步", "evening": "观音桥或江边小馆晚餐"},
        {"name": "磁器口", "tags": ["古镇", "美食", "商业", "城市"],
         "morning": "磁器口早到避开人流", "afternoon": "后街茶馆休息", "evening": "返回主城看夜景"},
        {"name": "南山", "tags": ["户外", "风景", "自然", "夜景"],
         "morning": "南山植物园", "afternoon": "老君洞或黄桷垭老街", "evening": "一棵树附近夜景"},
        {"name": "洪崖洞", "tags": ["夜景", "城市", "商业", "网红"],
         "morning": "戴家巷崖壁步道", "afternoon": "国泰艺术中心", "evening": "洪崖洞夜景后千厮门大桥散步"},
        {"name": "长江索道与南滨路", "tags": ["城市", "风景", "夜景", "户外"],
         "morning": "长江索道过江", "afternoon": "南滨路骑行", "evening": "弹子石老街夜景"},
        {"name": "武隆天生三桥", "tags": ["户外", "自然", "风景", "远郊"],
         "morning": "天生三桥景区", "afternoon": "龙水峡地缝", "evening": "武隆城区休息"},
        {"name": "大足石刻", "tags": ["历史文化", "远郊", "户外", "小众"],
         "morning": "宝顶山石刻", "afternoon": "北山石刻", "evening": "返回主城"},
        {"name": "缙云山", "tags": ["户外", "自然", "风景", "小众"],
         "morning": "缙云山步道登山", "afternoon": "缙云寺和观景台", "evening": "北碚老街晚餐"},
        {"name": "三峡博物馆与人民大礼堂", "tags": ["室内", "历史文化", "城市"],
         "morning": "三峡博物馆参观", "afternoon": "人民大礼堂外观", "evening": "学田湾美食街"},
    ],
    "北京": [
        {"name": "故宫与景山", "tags": ["历史文化", "城市", "户外", "网红"],
         "morning": "故宫中轴线", "afternoon": "景山俯瞰", "evening": "东四或隆福寺晚餐"},
        {"name": "什刹海", "tags": ["城市", "风景", "美食", "夜景"],
         "morning": "烟袋斜街早逛", "afternoon": "恭王府或郭守敬纪念馆", "evening": "后海周边安静散步"},
        {"name": "798艺术区", "tags": ["文创", "城市", "小众", "室内"],
         "morning": "画廊和展览", "afternoon": "郎园或将府公园", "evening": "三里屯周边晚餐"},
        {"name": "颐和园", "tags": ["风景", "历史文化", "户外", "城市"],
         "morning": "昆明湖西堤", "afternoon": "苏州街与长廊", "evening": "海淀小馆休息"},
        {"name": "前门与大栅栏", "tags": ["城市", "美食", "商业", "历史文化"],
         "morning": "前门老街", "afternoon": "杨梅竹斜街", "evening": "天桥艺术区看演出"},
        {"name": "天坛", "tags": ["历史文化", "城市", "户外", "风景"],
         "morning": "祈年殿和回音壁", "afternoon": "天坛公园古柏林散步", "evening": "红桥市场周边"},
        {"name": "国家博物馆", "tags": ["室内", "历史文化", "城市", "免费"],
         "morning": "古代中国展厅", "afternoon": "专题展览", "evening": "前门大街"},
        {"name": "圆明园", "tags": ["历史文化", "风景", "户外", "小众"],
         "morning": "西洋楼遗址", "afternoon": "福海划船", "evening": "清华西门周边"},
        {"name": "南锣鼓巷与鼓楼", "tags": ["城市", "美食", "商业", "小众"],
         "morning": "南锣鼓巷早逛", "afternoon": "鼓楼和钟楼", "evening": "什刹海酒吧街"},
        {"name": "慕田峪长城", "tags": ["户外", "历史文化", "风景", "远郊", "小众"],
         "morning": "缆车上山登长城", "afternoon": "长城徒步", "evening": "怀柔虹鳟鱼晚餐"},
        {"name": "雍和宫与五道营", "tags": ["历史文化", "城市", "小众", "美食"],
         "morning": "雍和宫祈福", "afternoon": "五道营胡同咖啡馆", "evening": "簋街吃小龙虾"},
    ],
    "上海": [
        {"name": "武康路与衡复街区", "tags": ["城市", "历史文化", "小众", "美食"],
         "morning": "武康大楼周边慢走", "afternoon": "安福路与湖南路小店", "evening": "静安寺周边晚餐"},
        {"name": "外滩源", "tags": ["城市", "风景", "夜景", "历史文化"],
         "morning": "圆明园路建筑群", "afternoon": "外白渡桥和苏州河", "evening": "北外滩夜景"},
        {"name": "浦东滨江", "tags": ["城市", "风景", "户外", "夜景"],
         "morning": "陆家嘴滨江步道", "afternoon": "艺仓美术馆", "evening": "滨江安静餐厅"},
        {"name": "田子坊", "tags": ["文创", "城市", "美食", "商业"],
         "morning": "泰康路弄堂", "afternoon": "思南公馆", "evening": "衡山路夜间散步"},
        {"name": "上海博物馆东馆", "tags": ["室内", "历史文化", "城市", "免费"],
         "morning": "上博东馆展览", "afternoon": "世纪公园", "evening": "浦东商圈晚餐"},
        {"name": "豫园与城隍庙", "tags": ["历史文化", "美食", "商业", "城市"],
         "morning": "豫园园林", "afternoon": "城隍庙小吃", "evening": "外滩夜景"},
        {"name": "迪士尼乐园", "tags": ["亲子", "户外", "网红", "远郊"],
         "morning": "奇幻童话城堡", "afternoon": "创极速光轮", "evening": "夜光幻影秀"},
        {"name": "上海自然博物馆", "tags": ["室内", "亲子", "城市", "免费"],
         "morning": "恐龙展厅", "afternoon": "蝴蝶温室", "evening": "静安雕塑公园"},
        {"name": "朱家角古镇", "tags": ["古镇", "美食", "风景", "远郊"],
         "morning": "放生桥和北大街", "afternoon": "课植园", "evening": "水巷游船晚餐"},
        {"name": "徐汇滨江龙美术馆", "tags": ["文创", "城市", "小众", "风景"],
         "morning": "龙美术馆展览", "afternoon": "滨江滑板公园", "evening": "西岸营地简餐"},
        {"name": "1933老场坊", "tags": ["小众", "城市", "文创", "室内"],
         "morning": "建筑空间探索", "afternoon": "周边创意园区", "evening": "虹口龙之梦美食"},
    ],
    "成都": [
        {"name": "人民公园", "tags": ["城市", "美食", "小众", "风景"],
         "morning": "鹤鸣茶社喝茶", "afternoon": "人民公园慢走", "evening": "奎星楼街小吃"},
        {"name": "宽窄巷子周边", "tags": ["城市", "美食", "商业", "历史文化"],
         "morning": "少城片区早逛", "afternoon": "小通巷咖啡", "evening": "泡桐树街晚餐"},
        {"name": "东郊记忆", "tags": ["文创", "城市", "小众", "夜景"],
         "morning": "东郊记忆展览", "afternoon": "建设路小吃", "evening": "玉林小酒馆周边"},
        {"name": "锦里与武侯祠", "tags": ["历史文化", "美食", "商业", "城市"],
         "morning": "武侯祠", "afternoon": "锦里错峰走", "evening": "高升桥附近吃川菜"},
        {"name": "都江堰", "tags": ["户外", "历史文化", "风景", "远郊"],
         "morning": "都江堰景区", "afternoon": "灌县古城", "evening": "南桥夜景"},
        {"name": "大熊猫繁育基地", "tags": ["亲子", "户外", "自然", "网红"],
         "morning": "太阳产房看熊猫", "afternoon": "月亮产房", "evening": "熊猫广场简餐"},
        {"name": "青城山", "tags": ["户外", "自然", "风景", "历史文化", "远郊"],
         "morning": "前山道教宫观", "afternoon": "后山徒步", "evening": "青城山镇温泉"},
        {"name": "金沙遗址博物馆", "tags": ["室内", "历史文化", "小众", "城市"],
         "morning": "遗迹馆参观", "afternoon": "陈列馆精品展", "evening": "一品天下美食街"},
        {"name": "太古里与春熙路", "tags": ["商业", "城市", "美食", "夜景"],
         "morning": "太古里街区拍照", "afternoon": "IFS爬楼熊猫", "evening": "春熙路夜市"},
        {"name": "文殊院", "tags": ["历史文化", "美食", "小众", "城市"],
         "morning": "文殊院祈福", "afternoon": "文殊坊素食与茶馆", "evening": "骡马市周边"},
        {"name": "西岭雪山", "tags": ["户外", "自然", "风景", "远郊"],
         "morning": "缆车上山", "afternoon": "日月坪观景", "evening": "滑雪场或花水湾温泉"},
    ],
    "杭州": [
        {"name": "西湖西线", "tags": ["风景", "户外", "城市", "历史文化"],
         "morning": "曲院风荷", "afternoon": "杨公堤和茅家埠", "evening": "湖滨或上天竺晚餐"},
        {"name": "龙井村", "tags": ["风景", "美食", "户外", "小众"],
         "morning": "龙井茶田步道", "afternoon": "九溪烟树", "evening": "茶村小馆休息"},
        {"name": "良渚古城遗址", "tags": ["历史文化", "户外", "小众", "风景"],
         "morning": "良渚博物院", "afternoon": "遗址公园", "evening": "瓶窑老街简餐"},
        {"name": "京杭大运河", "tags": ["城市", "历史文化", "风景", "夜景"],
         "morning": "桥西历史街区", "afternoon": "小河直街", "evening": "运河边夜游"},
        {"name": "西溪湿地", "tags": ["自然", "户外", "风景", "小众"],
         "morning": "西溪慢步道", "afternoon": "河渚街", "evening": "蒋村周边晚餐"},
        {"name": "灵隐寺与飞来峰", "tags": ["历史文化", "户外", "风景", "网红"],
         "morning": "灵隐寺祈福", "afternoon": "飞来峰石窟", "evening": "天竺路素食"},
        {"name": "雷峰塔与净慈寺", "tags": ["历史文化", "风景", "城市", "夜景"],
         "morning": "雷峰塔俯瞰西湖", "afternoon": "净慈寺", "evening": "南山路酒吧街"},
        {"name": "中国美院象山校区", "tags": ["文创", "小众", "风景", "城市"],
         "morning": "建筑群参观", "afternoon": "象山艺术公社", "evening": "转塘美食街"},
        {"name": "千岛湖", "tags": ["户外", "自然", "风景", "远郊"],
         "morning": "中心湖区游船", "afternoon": "环湖骑行", "evening": "湖边鱼头晚餐"},
        {"name": "南宋御街与河坊街", "tags": ["商业", "美食", "历史文化", "城市"],
         "morning": "御街漫步", "afternoon": "胡庆余堂与方回春堂", "evening": "高银街美食"},
        {"name": "云栖竹径", "tags": ["户外", "自然", "小众", "风景"],
         "morning": "竹径徒步", "afternoon": "梅家坞茶村", "evening": "之江周边"},
    ],
    "西安": [
        {"name": "城墙与碑林", "tags": ["历史文化", "城市", "户外", "风景"],
         "morning": "西安城墙骑行", "afternoon": "碑林博物馆", "evening": "书院门和湘子庙街"},
        {"name": "陕西历史博物馆", "tags": ["室内", "历史文化", "免费", "城市"],
         "morning": "陕历博预约参观", "afternoon": "小寨周边午餐", "evening": "大兴善寺散步"},
        {"name": "大雁塔", "tags": ["历史文化", "夜景", "城市", "网红"],
         "morning": "大慈恩寺", "afternoon": "大唐不夜城错峰", "evening": "曲江池夜间散步"},
        {"name": "回民街背街", "tags": ["美食", "城市", "小众", "历史文化"],
         "morning": "洒金桥早餐", "afternoon": "学习巷和大皮院", "evening": "钟楼周边夜景"},
        {"name": "兵马俑", "tags": ["历史文化", "网红", "远郊", "户外"],
         "morning": "兵马俑博物馆", "afternoon": "华清宫或骊山", "evening": "返城休整"},
        {"name": "大唐芙蓉园", "tags": ["风景", "夜景", "历史文化", "城市"],
         "morning": "园林景观", "afternoon": "唐风表演", "evening": "水幕电影"},
        {"name": "钟楼鼓楼", "tags": ["城市", "历史文化", "夜景", "商业"],
         "morning": "钟楼登顶", "afternoon": "鼓楼与回民街", "evening": "钟鼓楼夜景"},
        {"name": "华山", "tags": ["户外", "自然", "风景", "远郊"],
         "morning": "北峰索道上山", "afternoon": "长空栈道", "evening": "西峰日落"},
        {"name": "大明宫遗址公园", "tags": ["历史文化", "户外", "城市", "小众"],
         "morning": "遗址博物馆", "afternoon": "公园骑行", "evening": "大明宫万达"},
        {"name": "永兴坊", "tags": ["美食", "城市", "网红", "商业"],
         "morning": "非遗美食体验", "afternoon": "摔碗酒与民俗", "evening": "城墙根散步"},
        {"name": "秦岭野生动物园", "tags": ["亲子", "户外", "自然", "远郊"],
         "morning": "猛兽区游览", "afternoon": "步行区互动", "evening": "返回市区"},
    ],
    "广州": [
        {"name": "广州老城", "tags": ["城市", "美食", "历史文化", "小众"],
         "morning": "恩宁路和永庆坊早茶", "afternoon": "粤剧艺术博物馆和荔枝湾", "evening": "西关小巷觅食后回酒店休息"},
        {"name": "沙面", "tags": ["历史文化", "风景", "城市", "小众"],
         "morning": "沙面建筑群慢走", "afternoon": "沿江西路和人民桥周边", "evening": "珠江边散步，避开人挤人的夜游码头"},
        {"name": "黄埔古港", "tags": ["历史文化", "美食", "小众", "户外"],
         "morning": "古港村和粤海第一关", "afternoon": "黄埔村小店与古码头", "evening": "回市区吃清淡粤菜"},
        {"name": "沙湾古镇", "tags": ["古镇", "美食", "历史文化", "小众"],
         "morning": "沙湾古镇清晨入园", "afternoon": "何氏大宗祠和广东音乐馆", "evening": "姜撞奶、鱼皮角和古镇夜色"},
        {"name": "海鸥岛", "tags": ["户外", "自然", "小众", "远郊"],
         "morning": "海鸥岛骑行或村道散步", "afternoon": "莲藕田和江边咖啡", "evening": "番禺本地农庄晚餐"},
        {"name": "广州塔与花城广场", "tags": ["城市", "夜景", "网红", "风景"],
         "morning": "海心沙散步", "afternoon": "广东省博物馆", "evening": "广州塔夜景"},
        {"name": "白云山", "tags": ["户外", "自然", "风景", "城市"],
         "morning": "云台花园上山", "afternoon": "摩星岭观景", "evening": "白云晚望"},
        {"name": "陈家祠", "tags": ["历史文化", "城市", "室内", "小众"],
         "morning": "陈家祠建筑参观", "afternoon": "西关大屋社区", "evening": "龙津路美食"},
        {"name": "长隆旅游度假区", "tags": ["亲子", "户外", "网红", "远郊"],
         "morning": "野生动物世界", "afternoon": "欢乐世界", "evening": "大马戏表演"},
        {"name": "岭南印象园", "tags": ["历史文化", "户外", "小众", "亲子"],
         "morning": "岭南建筑群", "afternoon": "手工艺体验", "evening": "大学城周边"},
        {"name": "珠江夜游", "tags": ["夜景", "城市", "风景", "网红"],
         "morning": "天字码头周边早茶", "afternoon": "海心桥", "evening": "珠江夜游游船"},
    ],
    "桂林": [
        {"name": "象鼻山与两江四湖", "tags": ["风景", "城市", "夜景", "网红"],
         "morning": "象鼻山错峰入园", "afternoon": "靖江王府周边", "evening": "两江四湖夜景"},
        {"name": "阳朔遇龙河", "tags": ["风景", "户外", "自然", "小众"],
         "morning": "遇龙河竹筏", "afternoon": "旧县村骑行", "evening": "西街外围安静晚餐"},
        {"name": "兴坪古镇", "tags": ["古镇", "风景", "小众", "历史文化"],
         "morning": "兴坪码头和老街", "afternoon": "二十元人民币观景点", "evening": "漓江边小馆"},
        {"name": "龙脊梯田", "tags": ["风景", "自然", "户外", "远郊", "小众"],
         "morning": "平安寨观景", "afternoon": "梯田步道", "evening": "寨子客栈休息"},
        {"name": "东西巷", "tags": ["商业", "美食", "城市", "历史文化"],
         "morning": "东西巷慢逛", "afternoon": "逍遥楼", "evening": "本地米粉和夜间散步"},
        {"name": "漓江精华游", "tags": ["风景", "户外", "自然", "网红"],
         "morning": "磨盘山码头乘船", "afternoon": "九马画山到兴坪", "evening": "阳朔西街"},
        {"name": "世外桃源", "tags": ["风景", "自然", "小众", "亲子"],
         "morning": "乘船游湖", "afternoon": "侗族风雨桥", "evening": "返回阳朔"},
        {"name": "银子岩", "tags": ["自然", "室内", "小众", "风景"],
         "morning": "溶洞参观", "afternoon": "十里画廊骑行", "evening": "西街闲逛"},
        {"name": "古东瀑布", "tags": ["户外", "自然", "亲子", "远郊"],
         "morning": "瀑布攀爬", "afternoon": "森林步道", "evening": "返回桂林"},
        {"name": "独秀峰王城", "tags": ["历史文化", "城市", "风景", "小众"],
         "morning": "靖江王城", "afternoon": "独秀峰登顶", "evening": "正阳步行街"},
        {"name": "大圩古镇", "tags": ["古镇", "小众", "历史文化", "美食"],
         "morning": "古镇石板街漫步", "afternoon": "毛洲岛农家乐", "evening": "漓江日落"},
    ],
    "苏州": [
        {"name": "平江路", "tags": ["城市", "美食", "历史文化", "夜景"],
         "morning": "平江路早到慢走", "afternoon": "昆曲评弹体验", "evening": "十全街或观前街简餐"},
        {"name": "拙政园", "tags": ["历史文化", "风景", "城市", "网红"],
         "morning": "拙政园", "afternoon": "园林博物馆", "evening": "附近茶馆休息"},
        {"name": "苏州博物馆", "tags": ["室内", "历史文化", "免费", "城市"],
         "morning": "苏州博物馆预约参观", "afternoon": "忠王府", "evening": "平江支巷晚餐"},
        {"name": "山塘街", "tags": ["城市", "美食", "夜景", "商业"],
         "morning": "山塘街错峰", "afternoon": "虎丘或留园", "evening": "运河夜色"},
        {"name": "同里古镇", "tags": ["古镇", "风景", "远郊", "小众"],
         "morning": "同里古镇清晨入园", "afternoon": "退思园", "evening": "水巷边晚餐"},
        {"name": "虎丘", "tags": ["历史文化", "风景", "城市", "户外"],
         "morning": "虎丘塔和剑池", "afternoon": "后山茶园", "evening": "山塘街乘船"},
        {"name": "狮子林", "tags": ["历史文化", "风景", "亲子", "城市"],
         "morning": "假山迷宫", "afternoon": "园林茶室", "evening": "观前街夜景"},
        {"name": "周庄", "tags": ["古镇", "风景", "远郊", "网红"],
         "morning": "双桥和沈厅", "afternoon": "周庄博物馆", "evening": "水乡夜色"},
        {"name": "金鸡湖", "tags": ["城市", "夜景", "风景", "商业"],
         "morning": "李公堤漫步", "afternoon": "诚品书店", "evening": "月光码头喷泉"},
        {"name": "穹窿山", "tags": ["户外", "自然", "远郊", "小众"],
         "morning": "穹窿山步道", "afternoon": "孙武苑", "evening": "木渎古镇"},
        {"name": "沧浪亭与可园", "tags": ["历史文化", "小众", "城市", "风景"],
         "morning": "沧浪亭", "afternoon": "可园与文庙", "evening": "十全街美食"},
    ],
    "长沙": [
        {"name": "岳麓山", "tags": ["户外", "风景", "历史文化", "城市"],
         "morning": "岳麓书院", "afternoon": "爱晚亭和山路慢走", "evening": "大学城小吃"},
        {"name": "橘子洲", "tags": ["风景", "城市", "户外", "网红"],
         "morning": "橘子洲步道", "afternoon": "湘江中路咖啡", "evening": "杜甫江阁夜景"},
        {"name": "湖南博物院", "tags": ["室内", "历史文化", "免费", "城市"],
         "morning": "湖南博物院预约参观", "afternoon": "烈士公园", "evening": "开福寺周边晚餐"},
        {"name": "潮宗街", "tags": ["城市", "美食", "小众", "历史文化"],
         "morning": "潮宗街老街", "afternoon": "北正街和文和友外围", "evening": "湘江边散步"},
        {"name": "谢子龙影像艺术馆", "tags": ["文创", "室内", "小众", "城市"],
         "morning": "谢子龙影像艺术馆", "afternoon": "李自健美术馆", "evening": "洋湖湿地轻松收尾"},
        {"name": "太平街与坡子街", "tags": ["美食", "商业", "城市", "网红"],
         "morning": "太平街早逛", "afternoon": "贾谊故居", "evening": "坡子街火宫殿小吃"},
        {"name": "IFS国金中心", "tags": ["商业", "城市", "夜景", "网红"],
         "morning": "KAWS雕塑打卡", "afternoon": "国金中心购物", "evening": "黄兴南路步行街"},
        {"name": "梅溪湖国际文化艺术中心", "tags": ["文创", "城市", "小众", "风景"],
         "morning": "建筑参观", "afternoon": "梅溪湖公园", "evening": "文化艺术表演"},
        {"name": "靖港古镇", "tags": ["古镇", "美食", "远郊", "小众"],
         "morning": "古镇石板街", "afternoon": "宏泰坊和手工作坊", "evening": "江边日落返回"},
        {"name": "世界之窗与海底世界", "tags": ["亲子", "户外", "网红", "城市"],
         "morning": "世界之窗主题乐园", "afternoon": "海底世界", "evening": "广电中心周边"},
        {"name": "铜官窑古镇", "tags": ["历史文化", "远郊", "小众", "风景"],
         "morning": "铜官窑遗址", "afternoon": "陶艺体验工坊", "evening": "湘江边返回"},
    ],
}

# Scene activities for each spot — maps name → (morning, afternoon, evening)
SCENE_BANK: dict[str, tuple[str, str, str]] = {}
for _city_spots in CITY_SPOTS.values():
    for _spot in _city_spots:
        SCENE_BANK[_spot["name"]] = (_spot["morning"], _spot["afternoon"], _spot["evening"])

# Flattened name → tags lookup
SPOT_TAGS: dict[str, list[str]] = {}
for _city_spots in CITY_SPOTS.values():
    for _spot in _city_spots:
        SPOT_TAGS[_spot["name"]] = _spot["tags"]

# City name → ordered spot list (original interface)
CITY_LIBRARY: dict[str, list[str]] = {
    city: [s["name"] for s in spots] for city, spots in CITY_SPOTS.items()
}


TAG_KEYWORDS: dict[str, str] = {
    "小众": "小众", "安静": "小众", "人少": "小众", "避开人多": "小众",
    "网红": "网红", "打卡": "网红", "出片": "网红", "拍照": "网红",
    "商业": "商业", "购物": "商业", "逛街": "商业",
    "风景": "风景", "自然": "自然", "山水": "风景", "美景": "风景",
    "户外": "户外", "登山": "户外", "徒步": "户外", "骑行": "户外", "运动": "户外",
    "历史文化": "历史文化", "历史": "历史文化", "文化": "历史文化", "古迹": "历史文化", "博物馆": "历史文化",
    "美食": "美食", "好吃": "美食", "小吃": "美食", "吃": "美食", "火锅": "美食",
    "夜景": "夜景", "晚上": "夜景", "夜间": "夜景",
    "亲子": "亲子", "孩子": "亲子", "小孩": "亲子", "带娃": "亲子",
    "城市": "城市", "市区": "城市", "室内": "室内",
    "古镇": "古镇", "文创": "文创", "艺术": "文创",
    "免费": "免费", "不要钱": "免费", "便宜": "免费",
}

NEGATIVE_HINTS = ("不去", "不要", "避开", "不喜欢", "讨厌")


def wanted_tags_from_text(message: str) -> set[str]:
    return {tag for keyword, tag in TAG_KEYWORDS.items() if keyword in message}


def avoid_tags_from_text(message: str, profile: dict | None = None, wanted_tags: set[str] | None = None) -> set[str]:
    avoid_tags: set[str] = set()
    for pattern in (r"不去([^，。,.；;]+)", r"不要([^，。,.；;]+)", r"避开([^，。,.；;]+)", r"不喜欢([^，。,.；;]+)", r"讨厌([^，。,.；;]+)"):
        for fragment in re.findall(pattern, message):
            avoid_tags.update(wanted_tags_from_text(fragment))

    for tag in (profile or {}).get("tags", []):
        if any(hint in tag for hint in NEGATIVE_HINTS):
            fragment = tag
            for hint in NEGATIVE_HINTS:
                fragment = fragment.replace(hint, "")
            avoid_tags.update(wanted_tags_from_text(fragment))
    if wanted_tags:
        avoid_tags -= wanted_tags
    return avoid_tags


def rank_spots_for_request(
    city: str,
    message: str,
    days: int,
    avoid: list[str] | None = None,
    profile: dict | None = None,
) -> list[str]:
    """Rank one attraction per day using only local city/tag data."""
    spots = CITY_LIBRARY.get(city, [])
    if not spots:
        return []

    wanted_tags = wanted_tags_from_text(message)
    avoid_tags = avoid_tags_from_text(message, profile, wanted_tags)
    avoid = avoid or []

    ranked: list[tuple[str, int]] = []
    for index, spot_name in enumerate(spots):
        spot_tags = SPOT_TAGS.get(spot_name, [])
        if any(a and (a in spot_name or spot_name in a) for a in avoid):
            continue
        if avoid_tags and any(tag in spot_tags for tag in avoid_tags):
            continue
        score = sum(3 for tag in spot_tags if tag in wanted_tags)
        score += sum(1 for tag in spot_tags if tag in wanted_tags and tag in {"小众", "网红", "室内"})
        ranked.append((spot_name, score * 100 - index))

    ranked.sort(key=lambda item: item[1], reverse=True)
    result = [name for name, _score in ranked]
    if not result:
        result = spots.copy()
    return result[:max(1, days)]


# Local coordinate fallback for fast rule mode and no-key previews.
# Amap REST remains the authoritative source when a key is configured.
SPOT_COORDS: dict[str, tuple[float, float]] = {
    "广州老城": (113.2498, 23.1182),
    "沙面": (113.2467, 23.1087),
    "黄埔古港": (113.3904, 23.0928),
    "沙湾古镇": (113.3422, 22.9168),
    "海鸥岛": (113.4889, 22.9344),
    "广州塔与花城广场": (113.3309, 23.1133),
    "白云山": (113.2976, 23.1820),
    "陈家祠": (113.2564, 23.1251),
    "长隆旅游度假区": (113.3290, 22.9998),
    "岭南印象园": (113.3946, 23.0431),
    "珠江夜游": (113.2709, 23.1124),
    "解放碑与山城巷": (106.5757, 29.5570),
    "鹅岭二厂": (106.5393, 29.5546),
    "李子坝与嘉陵江": (106.5316, 29.5524),
    "磁器口": (106.4493, 29.5817),
    "南山": (106.5990, 29.5320),
    "洪崖洞": (106.5839, 29.5637),
    "故宫与景山": (116.3970, 39.9180),
    "什刹海": (116.3862, 39.9402),
    "798艺术区": (116.5017, 39.9842),
    "颐和园": (116.2755, 39.9999),
    "国家博物馆": (116.4010, 39.9051),
    "武康路与衡复街区": (121.4404, 31.2115),
    "外滩源": (121.4908, 31.2434),
    "浦东滨江": (121.5036, 31.2391),
    "上海博物馆东馆": (121.5500, 31.2290),
    "人民公园": (104.0630, 30.6598),
    "宽窄巷子周边": (104.0565, 30.6696),
    "东郊记忆": (104.1230, 30.6716),
    "金沙遗址博物馆": (104.0128, 30.6832),
    "西湖西线": (120.1390, 30.2440),
    "龙井村": (120.1061, 30.2247),
    "良渚古城遗址": (119.9906, 30.3950),
    "京杭大运河": (120.1468, 30.3160),
    "城墙与碑林": (108.9470, 34.2587),
    "陕西历史博物馆": (108.9596, 34.2190),
    "大雁塔": (108.9641, 34.2183),
    "回民街背街": (108.9397, 34.2651),
    "象鼻山与两江四湖": (110.2962, 25.2709),
    "阳朔遇龙河": (110.4773, 24.7785),
    "兴坪古镇": (110.5268, 24.9212),
    "龙脊梯田": (110.1212, 25.7984),
    "平江路": (120.6345, 31.3180),
    "拙政园": (120.6298, 31.3242),
    "苏州博物馆": (120.6287, 31.3247),
    "山塘街": (120.5980, 31.3197),
    "岳麓山": (112.9388, 28.1865),
    "橘子洲": (112.9580, 28.1965),
    "湖南博物院": (112.9838, 28.2134),
    "潮宗街": (112.9795, 28.2024),
}


def spot_coord(name: str) -> tuple[float, float] | None:
    if name in SPOT_COORDS:
        return SPOT_COORDS[name]
    for spot_name, coord in SPOT_COORDS.items():
        if spot_name in name or name in spot_name:
            return coord
    return None
