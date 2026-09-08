# 智能问数系统(Text-to-SQL Agent)

基于 LangGraph 构建的自然语言转 SQL 问答系统:通过语义层配置 + 多路召回(向量检索 + 全文检索)+ LLM 生成/校验/自纠错 SQL
的完整链路,让用户用自然语言查询结构化数据库。

> 本项目为个人学习实现,用于系统性掌握智能问数场景下的语义层设计、多路召回、LangGraph Agent 编排等核心技术。

## ✨ 特性

- 🗂️ **语义层建模**:以配置化方式管理数据库表/字段/指标的业务含义(名称、描述、别名、口径),运行时与真实数仓 schema(
  字段类型、样例数据)自动合并
- 🔍 **多路召回**:字段与指标走向量语义检索(Qdrant),具体取值走全文关键词检索(Elasticsearch),兼顾语义相似匹配与精确值匹配
- 🧩 **多向量索引设计**:同一实体的名称、描述、每个别名分别生成独立向量,避免拼接文本导致语义稀释、影响召回
- 🤖 **LangGraph 编排**:关键词提取 → 三路召回(字段/指标/取值)→ 合并 → LLM 筛选 → 上下文补全 → SQL 生成 → 校验/自纠错(上限3次)→ 执行,支持流式过程输出
- 🌊 **对外服务**:FastAPI + SSE 流式问答接口,配套 Vue3 前端

## 🏗️ 技术栈

| 分类           | 技术                                       |
|--------------|------------------------------------------|
| Agent 编排     | LangGraph                                |
| Web 框架       | FastAPI                                  |
| ORM / 数据库    | SQLAlchemy(Async) + MySQL                |
| 向量检索         | Qdrant                                   |
| 全文检索         | Elasticsearch(IK 中文分词)                   |
| Embedding 服务 | HuggingFace TEI(bge-large-zh-v1.5,1024维) |
| LLM          | DeepSeek                                 |
| 配置管理         | OmegaConf(结构化配置 + 类型校验)                  |
| 日志           | Loguru                                   |
| 依赖管理         | uv                                       |

## 📐 架构设计

### 分层结构(依赖严格自上而下,下层不感知上层)

api/ 对外接口层(FastAPI 路由 / 依赖注入 / 请求响应模型)
service/ 业务编排(离线知识库构建 / 在线问答服务)
agent/ LangGraph 节点与图(在线问答流程)
repository/ 数据存取(按存储介质划分)
clients/ 外部服务连接管理
models/ 数据结构定义
config/ 配置加载(yaml → 类型安全对象)
prompts/ LLM 提示词模板
scripts/ 离线任务入口(建库脚本)

### 离线知识库构建流程

meta_config.yaml(语义配置)
│
├─→ 与真实数仓 schema 合并 → 存入 MySQL(结构化元数据)
│ │
│ ├─→ 多向量展开 + Embedding → Qdrant(语义检索)
│ └─→ 抽取真实取值 → Elasticsearch(关键词检索)
│
└─→ 指标信息 → MySQL → 多向量展开 → Qdrant

### 在线问答流程(LangGraph)

用户问题 → 关键词抽取(一次 LLM 产出 字段/指标/取值 三类词)
  → 三路并行召回(Qdrant 字段向量 / Qdrant 指标向量 / ES 取值全文)
  → 合并去重排序(按相关度截断,缺失信息回查 MySQL 补全)
  → LLM 筛选表/字段/指标 → 补全时间/库上下文
  → LLM 生成 SQL → EXPLAIN 校验(失败自动纠错,最多 3 次)→ 执行并流式返回

## 📁 目录结构

conf/ 配置文件(连接信息 + 语义层配置)
app/
config/ 配置加载
clients/ 连接管理(MySQL / Qdrant / ES / Embedding)
models/ 数据结构定义
repository/ 数据存取
service/ 业务编排
scripts/ 一次性任务(离线建库等)
core/ 日志、上下文、中间件等基础设施
agent/ LangGraph 节点与图
api/ FastAPI 路由与依赖注入(api/schemas/ 为请求/响应模型)
prompts/ LLM 提示词模板
main.py 服务入口

## 🚀 快速开始

### 前置依赖

需要以下服务(建议用 Docker 部署):

- MySQL ×2(业务数仓库 + 元数据库)
- Qdrant
- Elasticsearch(需安装 IK 分词插件)
- Embedding 服务(TEI,加载 `bge-large-zh-v1.5`)

### 安装依赖

```bash
uv sync
```

### 配置

- conf/app_config.yaml:各服务连接信息
- conf/meta_config.yaml:语义层配置(表/字段/指标的业务含义)

### 启动依赖服务

```bash
docker compose -f docker/docker-compose.yaml up -d
```

首次启动会自动执行 `docker/mysql/meta.sql`,创建 meta/dw 数据库及其表结构、初始化数仓样例数据。

### 初始化元数据库表结构

若 meta 库已存在但表结构缺失(例如未通过上述 docker 初始化),执行:

```bash
python -m app.scripts.init_db
```

### 构建离线知识库

```bash
python -m app.scripts.build_meta_knowledge -c conf/meta_config.yaml
```

> ✅ 该脚本为全量重建:每次执行会先清空 MySQL 元数据表、重建 Qdrant collection 与 ES 索引,
> 再按当前 `meta_config.yaml` 重新生成全部数据,因此可安全重复执行。

### 启动在线问答 API

```bash
uvicorn main:app --reload --port 8000
```

- 交互式文档: http://localhost:8000/docs
- 问答接口(SSE 流式): `POST http://localhost:8000/api/query`,请求体 `{"query": "统计一下华东地区的销售额"}`


⚠️ 已知限制

- 离线建库为全量重建,数据量较大时耗时随语义层规模线性增长(可重复执行,无需手工清理)
- 部分语义配置存在有意保留的示例性错误,用于验证语义层配置错误对最终结果的影响
