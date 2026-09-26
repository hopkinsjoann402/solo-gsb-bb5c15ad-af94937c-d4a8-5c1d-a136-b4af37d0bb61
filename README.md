# 无线麦克风频点协调 API

基于 FastAPI 的演出无线麦克风频点协调服务。提交最多 **8 支**麦克风，每支给出最多 **6 个**候选整数频点（kHz）及可选的原频点，并指定正整数保护间隔；服务为每支麦克风选择一个候选频点，求出**全局最优**分配方案。

## 约束与优化目标

**硬约束**（guard 为保护间隔，单位 kHz）：

1. 任意两支麦克风：`|fi − fj| ≥ guard`
2. 任意三支不同麦克风的所有有序组合 (i, j, k)：`|2fi − fj − fk| ≥ guard`（三阶互调约束）

**优化目标**（按优先级）：

1. 最小化"有原频点且被换频"的麦克风数量
2. 在上述前提下，按输入顺序的频点数组取字典序最小

求解采用回溯搜索 + 分支限界，上限规模（8 支 × 6 候选）单次求解约百毫秒内完成。无解时返回明确的无解结果。

## 启动（Docker Compose，单命令）

```bash
docker compose up --build
```

容器构建时自动完成依赖安装（见 `Dockerfile`），无需任何手动步骤。

- **访问端口**：宿主机 `8000`（可用环境变量覆盖：`PORT=9000 docker compose up --build`）
- **API 地址**：`http://localhost:8000/api/v1/coordinate`
- **交互式文档**：`http://localhost:8000/docs`（Swagger UI）
- **健康检查**：`http://localhost:8000/health`

停止服务：`docker compose down`。

## 配置说明

| 配置项 | 方式 | 默认值 | 说明 |
| --- | --- | --- | --- |
| 宿主机端口 | 环境变量 `PORT` | `8000` | 映射到容器内 8000 端口 |

服务本身无其他必需配置，不依赖外部数据库或文件。

## API 使用示例

### 请求

`POST /api/v1/coordinate`，Content-Type: `application/json`

```bash
curl -X POST http://localhost:8000/api/v1/coordinate \
  -H "Content-Type: application/json" \
  -d @examples/request.json
```

`examples/request.json` 内容：

```json
{
  "guard_interval": 100,
  "microphones": [
    {"id": "mic-1", "candidates": [470000, 470200, 470400], "original": 470000},
    {"id": "mic-2", "candidates": [470100, 470300, 470500], "original": 470100},
    {"id": "mic-3", "candidates": [470600, 470800, 471000]}
  ]
}
```

字段说明：

| 字段 | 类型 | 必填 | 校验规则 |
| --- | --- | --- | --- |
| `guard_interval` | int | 是 | 正整数（kHz） |
| `microphones` | array | 是 | 1～8 支，`id` 须唯一 |
| `microphones[].id` | string | 是 | 1～64 字符 |
| `microphones[].candidates` | int[] | 是 | 1～6 个正整数频点（kHz） |
| `microphones[].original` | int | 否 | 正整数（kHz）；选中等于它的候选则不计换频 |

### 响应（有解，HTTP 200）

```json
{
  "feasible": true,
  "changed_count": 0,
  "assignments": [
    {"id": "mic-1", "frequency": 470000, "changed": false},
    {"id": "mic-2", "frequency": 470100, "changed": false},
    {"id": "mic-3", "frequency": 470600, "changed": false}
  ],
  "message": "求解成功：共 0 支有原频点的麦克风需要换频"
}
```

### 响应（无解，HTTP 200）

```json
{
  "feasible": false,
  "changed_count": 0,
  "assignments": [],
  "message": "无解：在给定候选频点与保护间隔下，不存在满足全部约束的分配方案"
}
```

### 响应（请求非法，HTTP 422）

请求体不符合校验规则（如麦克风超过 8 支、候选超过 6 个、保护间隔非正整数、id 重复等）时，返回 FastAPI 标准的 422 错误及具体字段错误信息。

## 本地开发与测试

```bash
pip install -r requirements-dev.txt
uvicorn app.main:app --reload          # 本地启动，端口 8000
pytest                                 # 运行测试（含与暴力枚举的随机对拍）
```

## 项目结构

```
app/
  main.py      # FastAPI 入口与接口定义
  models.py    # 请求/响应模型与校验
  solver.py    # 回溯 + 分支限界求解器
tests/         # 求解器单测（含随机对拍）与 API 测试
examples/      # 示例请求体
Dockerfile
docker-compose.yml
requirements.txt
```
