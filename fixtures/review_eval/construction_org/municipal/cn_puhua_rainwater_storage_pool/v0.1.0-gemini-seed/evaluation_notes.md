# evaluation_notes

## purpose
- 用作市政深基坑类施工组织设计的 bootstrap seed case
- 用作正向 rule hit case
- 验证危大工程识别、专项方案计划、深基坑参数抽取、微顶管识别

## primary_checks
- 是否能识别 7.7 危大工程清单
- 是否能识别 4.5 施工方案编制计划
- 是否能抽出最大开挖深度 22.05m
- 是否能抽出调蓄池规模 10400m3
- 是否能识别微顶管长度约 37m
- 是否能保留“危大工程识别完整”的正向 rule hit 定位而不过度误报

## known_limitations
- 成本管理计划缺失仍是 Gemini seed issue，尚未专家确认
- 第三方监测主体表述需要后续人工复核
- 该 case 同时作为 positive sample 和 seeded issue sample

## next_review_actions
- 为深基坑 / 微顶管 / 支撑体系补充更细粒度 expected rule hits
- 增加周边管线与环境保护等级 facts
- 后续接入 structured_review 时优先作为正向命中 case
