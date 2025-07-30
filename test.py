# import requests
#
# try:
#     url = "http://103.118.254.151/status"
#     # url = "http://localhost:5000/accounts"
#     # url = "http://localhost:5000/status"
#     headers = {"Content-Type": "application/json"}
#     data = {"id": "use33611", "model": "xyz789"}
#
#     response = requests.post(url, json=data, headers=headers)
#     response.raise_for_status()
#
#     print("Status Code:", response.status_code)
#     print("Response:", response.json())
#
# except requests.exceptions.HTTPError as http_err:
#     print(f"HTTP error occurred: {http_err}")
# except requests.exceptions.ConnectionError:
#     print("Error: Could not connect to the server. Is it running at http://localhost:8000/?")
# except requests.exceptions.JSONDecodeError:
#     print("Error: Response is not valid JSON.")
# except requests.exceptions.RequestException as err:
#     print(f"An error occurred: {err}")

import asyncio
import random
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

app = FastAPI()

# 模拟缓存（共享，但不影响超时逻辑）
cache = {"result": random.random()}

# 超时时间
TIMEOUT_SECONDS = 5

# 模拟第一个异步任务
async def async_task_1():
    await asyncio.sleep(7)  # 模拟耗时 7 秒
    return {"task": "task1", "result": random.random()}

# 模拟第二个异步任务
async def async_task_2():
    await asyncio.sleep(6)  # 模拟耗时 6 秒
    return {"task": "task2", "result": random.random()}

# 超时后执行的操作
async def timeout_action(request: Request):
    if getattr(request.state, "timeout_flag", False):
        # 超时后的操作，返回缓存数据
        return {
            "message": "Timeout occurred",
            "cache_result": cache["result"],
            "timeout": True
        }
    return None

# 端点处理请求
@app.post("/run-tasks")
async def run_tasks(request: Request):
    # 为每个请求初始化超时标志
    request.state.timeout_flag = False

    # 启动两个异步任务
    tasks = [async_task_1(), async_task_2()]

    try:
        # 使用 asyncio.wait_for 设置超时
        results = await asyncio.wait_for(
            asyncio.gather(*tasks, return_exceptions=True),
            timeout=TIMEOUT_SECONDS
        )
        # 任务正常完成，返回结果
        return {"results": results, "timeout": False}
    except asyncio.TimeoutError:
        # 超时后修改该请求的超时标志
        request.state.timeout_flag = True
        timeout_result = await timeout_action(request)
        return JSONResponse(
            content=timeout_result,
            status_code=200
        )

# 模拟更新缓存的端点（可选，用于测试）
@app.get("/update-cache")
async def update_cache():
    cache["result"] = random.random()
    return {"message": "Cache updated", "new_cache": cache["result"]}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)