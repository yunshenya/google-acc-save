from fastapi import FastAPI, status, HTTPException
from fastapi.responses import JSONResponse
import asyncio
from collections import defaultdict
import threading

app = FastAPI()

# 共享状态，用于存储 identifier 和对应的数据
operations = defaultdict(bool)
lock = threading.Lock()  # 线程锁，保护共享状态

async def handle_timeout(identifier: str, data: str):
    # 等待五分钟
    await asyncio.sleep(10)

    # 超时后执行操作
    with lock:
        if identifier in operations:
            # 模拟基于 identifier 执行的操作
            print(f"Timeout reached for identifier: {identifier}. Performing operation with data: {data}")
            # 调用你的具体函数
            some_function(identifier, data)
            # 清理已处理的操作
            del operations[identifier]
        else:
            print(f"Identifier {identifier} not found in operations.")

# 模拟你的操作函数
def some_function(identifier: str, data: str):
    print(f"Executing function for identifier: {identifier} with data: {data}")

@app.get("/")
async def handle_request(identifier: str):
    # 验证 identifier 是否为空
    if not identifier:
        raise HTTPException(status_code=400, detail="Identifier is required")

    # 模拟请求携带的数据
    request_data = f"Request data for {identifier}"

    # 存储 identifier 和数据
    with lock:
        if identifier in operations:
            raise HTTPException(status_code=400, detail=f"Identifier {identifier} is already in use")
        operations[identifier] = True

    # 启动超时任务
    asyncio.create_task(handle_timeout(identifier, request_data))

    # 返回响应
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"message": f"Request processed with identifier: {identifier}. Operation will timeout in 5 minutes."}
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)