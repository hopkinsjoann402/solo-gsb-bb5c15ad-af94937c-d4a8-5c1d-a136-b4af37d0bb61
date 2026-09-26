# 演出无线麦克风频点协调 API

基于 **Python + FastAPI** 的演出无线麦克风频点协调服务：为每支麦克风从候选频点中选出最终频点，满足两两频差与三阶互调约束，并给出全局最优方案。

## 问题定义

- 输入 **1~8 支**麦克风，每支 **1~6 个**候选整数频点（kHz），可选原频点；
- 输入一个**正整数保护间隔** `g`（kHz）。
- 约束：
  1. 任意两支麦克风 `i、j`：`|fi − fj| ≥ g`；
  2. 任意三支不同麦克风，遍历**所有有序组合** `(i, j, k)`：`|2fi − fj − fk| ≥ g`。
- 目标（全局最优，按优先级）：
  1. **最少换频**：提供了原频点且最终频点 ≠ 原频点的麦克风数量最少；
  2. 换频数相同时，按输入顺序的**频点数组字典序最小**。
- 无解时返回明确的 `no_solution` 结果。

求解采用按输入顺序的回溯搜索 + 分支定界剪枝（8×6 规模毫秒级），保证全局最优。

## 启动（Docker Compose，单命令）

仓库根目录执行：

```bash
docker compose up --build
```

容器构建时自动完成依赖安装（`pip install -r requirements.txt`），无需任何手工配置。

- **访问端口**：`8000`（宿主机）→ `8000`（容器）
- **API 地址**：`http://localhost:8000`
- **交互式文档（可直接调用）**：`http://localhost:8000/docs`（Swagger UI）
- 健康检查：`GET http://localhost:8000/health`

### 所需配置

无必填配置，开箱即用。可选环境变量：

| 变量 | 默认值 | 说明 |
| ---- | ------ | ---- |
| 无   | —      | 端口映射在 `docker-compose.yml` 中修改（如改为 `"8080:8000"`） |

## 本地开发（不用 Docker）

```bash
pip install -r requirements-dev.txt
uvicorn app.main:app --reload --port 8000
pytest            # 运行测试
```

## API 说明

### `POST /api/v1/coordinate`

**请求体**

| 字段 | 类型 | 约束 | 说明 |
| ---- | ---- | ---- | ---- |
| `guard_interval` | int | 正整数 | 保护间隔（kHz） |
| `microphones` | array | 1~8 个 | 麦克风列表 |
| `microphones[].id` | string? | ≤64 字符、唯一 | 可选标识，缺省自动生成 `mic-1…` |
| `microphones[].candidates` | int[] | 1~6 个、非负整数 | 候选频点（kHz），服务端去重升序 |
| `microphones[].original` | int? | 非负整数 | 原频点（kHz） |

校验失败返回 **422** 及具体错误明细。

**curl 示例**

```bash
curl -X POST http://localhost:8000/api/v1/coordinate \
  -H "Content-Type: application/json" \
  -d '{
    "guard_interval": 200,
    "microphones": [
      {"id": "lead-vocal", "candidates": [600100, 600400, 600900], "original": 600400},
      {"id": "backing-1",  "candidates": [601000, 601300, 601600], "original": 601300},
      {"id": "backing-2",  "candidates": [602000, 602300, 602600]}
    ]
  }'
```

**成功响应（`status = ok`）**

```json
{
  "status": "ok",
  "guard_interval": 200,
  "changed_count": 0,
  "frequencies": [600400, 601300, 602000],
  "assignments": [
    {"id": "lead-vocal", "frequency": 600400, "original": 600400, "changed": false},
    {"id": "backing-1",  "frequency": 601300, "original": 601300, "changed": false},
    {"id": "backing-2",  "frequency": 602000, "original": null,   "changed": false}
  ],
  "checked_triples": 36,
  "detail": null
}
```

**无解响应（`status = no_solution`）**

```json
{
  "status": "no_solution",
  "guard_interval": 1000,
  "changed_count": null,
  "frequencies": null,
  "assignments": null,
  "checked_triples": 0,
  "detail": "在给定的候选频点与保护间隔下，不存在同时满足两两频差约束和三频互调约束 |2fi−fj−fk|≥g 的方案；请扩大候选频点或减小保护间隔。"
}
```

### 其他端点

| 方法 | 路径 | 说明 |
| ---- | ---- | ---- |
| GET  | `/` | 服务信息 |
| GET  | `/health` | 健康检查 |
| GET  | `/docs` | Swagger UI（可在线试调用） |
| GET  | `/openapi.json` | OpenAPI 规范 |

## 项目结构

```
├── app/
│   ├── main.py      # FastAPI 入口与路由
│   ├── models.py    # 请求/响应模型与校验
│   └── solver.py    # 回溯 + 分支定界求解器
├── tests/           # 求解器单测（含全枚举对照）与 API 集成测试
├── requirements.txt
├── requirements-dev.txt
├── Dockerfile
└── docker-compose.yml
```
