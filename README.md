接入了两家身份提供方之后，同一个邮箱在两边各有一个账号，权限被叠加成了管理员：本仓库给出一套身份联合映射的参考实现，用于把外部身份安全地落到唯一本地账号上，并保留可审计的映射记录。实现包含解析断言、校验提供方、映射属性、检查唯一性、建立链接、检查合并、校验映射定义和批量处理八个公开函数，配套公开测试用于检验行为是否符合契约与不变量。

## 契约

- 外部身份必须映射到唯一本地账号，一个外部身份永远只对应一个本地账号。
- 属性映射必须按映射声明中的来源字段执行，不得按目标名称猜测。
- 同一邮箱出现在不同提供方时不得自动合并为同一个本地账号。
- 映射的新增与变更必须写入审计记录，记录包含提供方、外部标识、本地账号和时间。
- 未受信任的提供方一律拒绝，受信任列表为空时全部拒绝。
- 批量处理时每个身份相互独立，单个身份的失败不得影响其他身份。

## 不变量

- 一个外部身份永远只对应一个本地账号。
- 未登记提供方的断言不被采用。

## 数据形态

断言文档：

```json
{
  "provider": "idp-a",
  "subject": "u-1",
  "attributes": {"mail": "alice@example.com"},
  "trusted": ["idp-a"],
  "mapping": [{"source": "mail", "target": "email", "type": "str"}],
  "local_id": "local-1"
}
```

映射声明是一个字段列表，每一项包含 source、target、type，type 取 str、int、bool、list。

存储对象：

```json
{"links": [], "audit": []}
```

链接记录包含 provider、external_id、local_id、email、ts；审计记录包含 action、provider、external_id、local_id、ts。

## 公开函数

| 函数 | 说明 |
| --- | --- |
| parse_assertion(doc) | 解析断言，返回 provider、external_id 和 attributes |
| check_provider(doc, trusted) | 判断断言提供方是否在受信列表内 |
| map_identity(assertion, mapping) | 按声明把断言属性映射为本地字段 |
| check_unique(store, provider, external_id) | 判断外部身份当前是否尚未建立链接 |
| link(store, external, local, now) | 建立外部身份到本地账号的链接并留痕 |
| check_merge(external, local) | 判断两个身份是否可作为同一账号处理 |
| validate_mapping(mapping) | 返回映射声明中的问题列表 |
| federation_batch(assertions, store, now) | 批量处理断言，返回 linked 与 failed |

## 测试

```bash
python -m pytest tests -q
```

## 字段表

| 字段 | 取值 |
| --- | --- |
| 所属领域 | 安全 |
| 子方向 | 漏洞检测与攻防 |
| 任务类型 | Bugfix |
| 语言/框架 | Python 3, pytest |
| 环境可复现等级 | 无外部依赖 |

