# Skill Contract Schema · use block

<aside>
🔩

**`use` block 是 KiU 的最小硬铉子**。一条 skill 有没有合法的 `use` block,决定它是契约还是笔记。

</aside>

## Schema v0.1 (YAML)

```yaml
use:
  # ◆◆◆  REQUIRED: trigger  ◆◆◆
  trigger:
    patterns:              # ≥1 条,机器可匹配的场景模式
      - <pattern_id>       # e.g. user_considering_capital_allocation
    exclusions:            # 可选, 显式排除的场景
      - <pattern_id>

  # ◆◆◆  REQUIRED: intake  ◆◆◆
  intake:
    required:              # ≥1 字段, 从场境抽取的必须变量
      - name: <field_name>
        type: string | number | enum | entity | list
        description: <one-line>
    optional:
      - name: <field_name>
        type: ...
        description: ...

  # ◆◆◆  REQUIRED: judgment_schema  ◆◆◆
  judgment_schema:
    output:
      type: enum | structured
      schema:              # JSON-schema-lite
        <field>: <type>
    reasoning_chain_required: true | false

  # ◆◆◆  REQUIRED: boundary  ◆◆◆
  boundary:
    fails_when:            # ≥1 条, 它会误导使用者的场景
      - <failure_pattern>
    do_not_fire_when:      # ≥1 条, 应主动拒绝触发的场景
      - <exclusion_pattern>
```

## 校验规则 (硬性)

| 规则 | 不过后果 |
| --- | --- |
| `use` block 缺失 | → rejected/ |
| 4 个子块任一缺失 | → rejected/ |
| `trigger.patterns` < 1 | → rejected/ |
| `intake.required` < 1 | → rejected/ |
| `boundary.fails_when` < 1 | → rejected/ |
| `boundary.do_not_fire_when` < 1 | → rejected/ |
| `trigger.patterns` 中任一不是机器可匹配的 pattern_id | → rejected/ |

## 完整示例 · circle-of-competence

```yaml
skill: circle-of-competence

use:
  trigger:
    patterns:
      - user_considering_investment_decision
      - user_evaluating_domain_familiarity_for_decision
      - user_uncertain_about_understanding_depth
    exclusions:
      - user_asking_factual_question_only
      - user_making_non_capital_decision

  intake:
    required:
      - name: subject_entity
        type: entity
        description: company, asset, or domain under consideration
      - name: user_domain_exposure
        type: structured
        description: "{years: number, depth: enum[casual|professional|expert]}"
      - name: decision_stakes
        type: structured
        description: "{capital_at_risk: number, reversibility: enum}"
    optional:
      - name: time_horizon
        type: string
        description: "e.g. '3y', '20y'"

  judgment_schema:
    output:
      type: structured
      schema:
        verdict: enum[IN_CIRCLE, MARGINAL, OUT_OF_CIRCLE]
        reasoning_chain: list[check_result]
        required_further_investigation: list[topic]
    reasoning_chain_required: true

  boundary:
    fails_when:
      - user_conflates_familiarity_with_understanding
      - subject_is_in_rapidly_changing_domain_where_past_familiarity_is_misleading
      - user_has_strong_incentive_to_rationalize_inclusion
    do_not_fire_when:
      - decision_is_not_capital_allocation
      - subject_is_explicitly_speculative_position
      - decision_is_below_material_threshold
```

## [SKILL.md](http://SKILL.md) 完整结构

`use` block 放在文档的**第一块**, 教梳位置:

```markdown
# skill: <name>

## use
```

[use block —— machine-readable contract]

```

## usage traces
- trace_1: [完整 trace 结构, ≥3 条]
- trace_2: ...
- trace_3: ...

## rationale
[散文部分 · 给人读 · RIA++ 其他维度 (R/I/A2/E)]

## anchors
[provenance: node_id 全清单]

## tests
[test-prompts.json 引用]
```

## 为什么是 YAML 而不是 JSON / 散文

- **不用散文**: LLM 每次 parse 散文都会引入解释偏差, 契约需要确定性
- **不用 JSON**: 人写/人读体验差; 评审时需要可读性
- **用 YAML**: 机器可解析 + 人类友好 + 支持注释 + 更接近配置语言的角色定位

## 运行时审订

未来的 agent 运行时**直接 parse `use` block 来调用 skill**，不是 LLM 通读 markdown:

```python
def dispatch(situation: Situation) -> List[SkillInvocation]:
    candidates = []
    for skill in skill_registry:
        if matches(situation, skill.use.trigger.patterns):
            if not matches(situation, skill.use.trigger.exclusions):
                if not matches(situation, skill.use.boundary.do_not_fire_when):
                    candidates.append(skill)
    return candidates
```

散文部分只在生成 / 编辑 / 人工审核时被用到。**执行路径完全不依赖散文**。

这就是 "面向 agent 执行而非面向阅读的蒸馏" 的结构化落地。