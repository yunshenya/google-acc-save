import datetime
from typing import List, Dict, Any
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from app.config import Config
from app.dependencies.auth_middleware import verify_token
from app.dependencies.utils import get_pad_code_list
from app.services.logger import get_logger

router = APIRouter()
logger = get_logger("pad_code_router")


class PadCodeInfo(BaseModel):
    """Pad代码信息模型"""
    padCode: str
    deviceIp: str
    padIp: str
    cvmStatus: int
    padName: str
    androidVersion: str
    goodName: str
    signExpirationTime: str
    status: int
    bootTime: int


class PadCodeSyncRequest(BaseModel):
    """同步请求模型"""
    selected_codes: List[str] = []  # 选择的代码列表，空列表表示同步所有


class PadCodeSyncResponse(BaseModel):
    """同步响应模型"""
    success: bool
    message: str
    added_codes: List[str]
    updated_codes: List[str]
    total_available: int
    total_synced: int


@router.get("/api/pad-codes/available", response_model=Dict[str, Any])
async def get_available_pad_codes(_: str = Depends(verify_token)) -> Dict[str, Any]:
    """获取云端可用的 pad_code 列表"""
    try:
        logger.info("开始获取云端可用的 pad_code 列表")

        # 调用云端API获取pad_code列表
        response = await get_pad_code_list()

        if not response or response.get("code") != 200:
            error_msg = response.get("msg", "未知错误") if response else "API调用失败"
            raise HTTPException(status_code=500, detail=f"获取云端pad_code失败: {error_msg}")

        pad_data = response.get("data", [])

        # 格式化数据
        formatted_data = []
        for pad in pad_data:
            expirationTime = pad.get("signExpirationTime")
            timestamp_seconds = expirationTime / 1000
            dt = datetime.datetime.fromtimestamp(timestamp_seconds)
            formatted_data.append({
                "padCode": pad.get("padCode"),
                "deviceIp": pad.get("deviceIp"),
                "padIp": pad.get("padIp"),
                "cvmStatus": pad.get("cvmStatus"),
                "padName": pad.get("padName"),
                "androidVersion": pad.get("androidVersion"),
                "goodName": pad.get("goodName"),
                "signExpirationTime": dt.strftime('%Y年%m月%d日'),
                "status": pad.get("status"),
                "bootTime": pad.get("bootTime"),
                "isInConfig": pad.get("padCode") in Config.PAD_CODES  # 是否已在配置中
            })

        # 获取当前配置的pad_codes
        current_codes = set(Config.PAD_CODES)
        available_codes = {pad.get("padCode") for pad in pad_data if pad.get("padCode")}

        logger.info(f"云端可用pad_code数量: {len(formatted_data)}")

        return {
            "success": True,
            "data": formatted_data,
            "summary": {
                "total_available": len(formatted_data),
                "total_in_config": len(current_codes),
                "not_in_config": len(available_codes - current_codes),
                "config_not_available": len(current_codes - available_codes)
            },
            "timestamp": response.get("ts")
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取可用pad_code列表失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取可用pad_code列表失败: {str(e)}")


@router.get("/api/pad-codes/current", response_model=Dict[str, Any])
async def get_current_pad_codes(_: str = Depends(verify_token)) -> Dict[str, Any]:
    """获取当前配置中的 pad_code 列表"""
    try:
        current_codes = Config.PAD_CODES.copy()

        return {
            "success": True,
            "data": current_codes,
            "total": len(current_codes)
        }

    except Exception as e:
        logger.error(f"获取当前pad_code配置失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取当前配置失败: {str(e)}")


@router.post("/api/pad-codes/sync", response_model=PadCodeSyncResponse)
async def sync_pad_codes(
        sync_request: PadCodeSyncRequest,
        _: str = Depends(verify_token)
) -> PadCodeSyncResponse:
    """同步 pad_code 到配置中"""
    try:
        logger.info(f"开始同步pad_code，选择的代码数量: {len(sync_request.selected_codes)}")

        # 获取云端可用的pad_code
        response = await get_pad_code_list()

        if not response or response.get("code") != 200:
            error_msg = response.get("msg", "未知错误") if response else "API调用失败"
            raise HTTPException(status_code=500, detail=f"获取云端pad_code失败: {error_msg}")

        available_pads = response.get("data", [])
        available_codes = {pad.get("padCode") for pad in available_pads if pad.get("padCode")}

        # 确定要同步的代码
        if sync_request.selected_codes:
            # 同步指定的代码
            codes_to_sync = set(sync_request.selected_codes)
            # 验证选择的代码是否都在可用列表中
            invalid_codes = codes_to_sync - available_codes
            if invalid_codes:
                raise HTTPException(
                    status_code=400,
                    detail=f"以下代码在云端不可用: {', '.join(invalid_codes)}"
                )
        else:
            # 同步所有可用代码
            codes_to_sync = available_codes

        # 获取当前配置
        current_codes = set(Config.PAD_CODES)

        # 计算新增和更新的代码
        added_codes = list(codes_to_sync - current_codes)
        updated_codes = list(codes_to_sync & current_codes)

        # 更新配置
        new_pad_codes = list(current_codes | codes_to_sync)

        # 使用配置更新方法
        Config.update_config({
            "pad_codes": new_pad_codes
        })

        logger.info(f"同步完成 - 新增: {len(added_codes)}, 已存在: {len(updated_codes)}")

        return PadCodeSyncResponse(
            success=True,
            message=f"成功同步 {len(codes_to_sync)} 个pad_code (新增: {len(added_codes)}, 已存在: {len(updated_codes)})",
            added_codes=added_codes,
            updated_codes=updated_codes,
            total_available=len(available_codes),
            total_synced=len(codes_to_sync)
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"同步pad_code失败: {e}")
        raise HTTPException(status_code=500, detail=f"同步失败: {str(e)}")


@router.post("/api/pad-codes/add", response_model=Dict[str, str])
async def add_pad_codes(
        sync_request: PadCodeSyncRequest,
        _: str = Depends(verify_token)
) -> Dict[str, str]:
    """添加指定的 pad_code 到配置中（不替换现有配置）"""
    try:
        if not sync_request.selected_codes:
            raise HTTPException(status_code=400, detail="请提供要添加的pad_code列表")

        logger.info(f"开始添加pad_code: {sync_request.selected_codes}")

        # 验证这些代码是否在云端可用
        response = await get_pad_code_list()

        if not response or response.get("code") != 200:
            error_msg = response.get("msg", "未知错误") if response else "API调用失败"
            raise HTTPException(status_code=500, detail=f"验证pad_code失败: {error_msg}")

        available_pads = response.get("data", [])
        available_codes = {pad.get("padCode") for pad in available_pads if pad.get("padCode")}

        # 验证所有选择的代码都在可用列表中
        codes_to_add = set(sync_request.selected_codes)
        invalid_codes = codes_to_add - available_codes
        if invalid_codes:
            raise HTTPException(
                status_code=400,
                detail=f"以下代码在云端不可用: {', '.join(invalid_codes)}"
            )

        # 获取当前配置并添加新代码
        current_codes = set(Config.PAD_CODES)
        already_exists = codes_to_add & current_codes
        new_codes = codes_to_add - current_codes

        if not new_codes:
            return {
                "success": "true",
                "message": f"所有提供的代码都已存在于配置中: {', '.join(already_exists)}"
            }

        # 更新配置
        updated_codes = list(current_codes | codes_to_add)
        Config.update_config({
            "pad_codes": updated_codes
        })

        logger.info(f"成功添加 {len(new_codes)} 个新的pad_code")

        message_parts = [f"成功添加 {len(new_codes)} 个新的pad_code"]
        if already_exists:
            message_parts.append(f"{len(already_exists)} 个代码已存在")

        return {
            "success": "true",
            "message": "，".join(message_parts)
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"添加pad_code失败: {e}")
        raise HTTPException(status_code=500, detail=f"添加失败: {str(e)}")


@router.delete("/api/pad-codes/remove", response_model=Dict[str, str])
async def remove_pad_codes(
        sync_request: PadCodeSyncRequest,
        _: str = Depends(verify_token)
) -> Dict[str, str]:
    """从配置中移除指定的 pad_code"""
    try:
        if not sync_request.selected_codes:
            raise HTTPException(status_code=400, detail="请提供要移除的pad_code列表")

        logger.info(f"开始移除pad_code: {sync_request.selected_codes}")

        current_codes = set(Config.PAD_CODES)
        codes_to_remove = set(sync_request.selected_codes)

        # 检查要移除的代码是否存在
        not_exists = codes_to_remove - current_codes
        if not_exists:
            logger.warning(f"以下代码不在当前配置中: {not_exists}")

        # 计算移除后的代码
        remaining_codes = current_codes - codes_to_remove
        actually_removed = current_codes & codes_to_remove

        if not actually_removed:
            return {
                "success": "true",
                "message": "指定的代码都不在当前配置中"
            }

        # 更新配置
        Config.update_config({
            "pad_codes": list(remaining_codes)
        })

        logger.info(f"成功移除 {len(actually_removed)} 个pad_code")

        return {
            "success": "true",
            "message": f"成功移除 {len(actually_removed)} 个pad_code"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"移除pad_code失败: {e}")
        raise HTTPException(status_code=500, detail=f"移除失败: {str(e)}")


@router.post("/api/pad-codes/replace", response_model=Dict[str, str])
async def replace_pad_codes(
        sync_request: PadCodeSyncRequest,
        _: str = Depends(verify_token)
) -> Dict[str, str]:
    """完全替换配置中的 pad_code（慎用）"""
    try:
        if not sync_request.selected_codes:
            raise HTTPException(status_code=400, detail="请提供要设置的pad_code列表")

        logger.warning(f"开始替换所有pad_code为: {sync_request.selected_codes}")

        # 验证这些代码是否在云端可用
        response = await get_pad_code_list()

        if not response or response.get("code") != 200:
            error_msg = response.get("msg", "未知错误") if response else "API调用失败"
            raise HTTPException(status_code=500, detail=f"验证pad_code失败: {error_msg}")

        available_pads = response.get("data", [])
        available_codes = {pad.get("padCode") for pad in available_pads if pad.get("padCode")}

        # 验证所有选择的代码都在可用列表中
        codes_to_set = set(sync_request.selected_codes)
        invalid_codes = codes_to_set - available_codes
        if invalid_codes:
            raise HTTPException(
                status_code=400,
                detail=f"以下代码在云端不可用: {', '.join(invalid_codes)}"
            )

        old_count = len(Config.PAD_CODES)

        # 完全替换配置
        Config.update_config({
            "pad_codes": sync_request.selected_codes
        })

        logger.warning(f"已完全替换pad_code配置，从 {old_count} 个变为 {len(sync_request.selected_codes)} 个")

        return {
            "success": "true",
            "message": f"已完全替换pad_code配置 (原有: {old_count} 个，现有: {len(sync_request.selected_codes)} 个)"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"替换pad_code失败: {e}")
        raise HTTPException(status_code=500, detail=f"替换失败: {str(e)}")


@router.get("/api/pad-codes/compare", response_model=Dict[str, Any])
async def compare_pad_codes(_: str = Depends(verify_token)) -> Dict[str, Any]:
    """比较云端和本地配置的 pad_code 差异"""
    try:
        # 获取云端数据
        response = await get_pad_code_list()

        if not response or response.get("code") != 200:
            error_msg = response.get("msg", "未知错误") if response else "API调用失败"
            raise HTTPException(status_code=500, detail=f"获取云端pad_code失败: {error_msg}")

        available_pads = response.get("data", [])
        cloud_codes = {pad.get("padCode") for pad in available_pads if pad.get("padCode")}
        local_codes = set(Config.PAD_CODES)

        # 计算差异
        only_in_cloud = cloud_codes - local_codes  # 云端有但本地没有
        only_in_local = local_codes - cloud_codes  # 本地有但云端没有
        in_both = cloud_codes & local_codes        # 两边都有

        return {
            "success": True,
            "cloud_total": len(cloud_codes),
            "local_total": len(local_codes),
            "in_both": len(in_both),
            "only_in_cloud": {
                "count": len(only_in_cloud),
                "codes": list(only_in_cloud)
            },
            "only_in_local": {
                "count": len(only_in_local),
                "codes": list(only_in_local)
            },
            "sync_recommendation": {
                "can_add_from_cloud": len(only_in_cloud),
                "should_remove_invalid": len(only_in_local)
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"比较pad_code失败: {e}")
        raise HTTPException(status_code=500, detail=f"比较失败: {str(e)}")