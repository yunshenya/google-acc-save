from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, Any

from app.config import Config
from app.models.config import ConfigUpdateRequest, ConfigResponse
from app.dependencies.auth_middleware import verify_token
from app.services.logger import get_logger
from app.services.websocket_manager import ws_manager

router = APIRouter()
logger = get_logger("config_router")


@router.get("/config", response_model=ConfigResponse)
async def get_config(_: str = Depends(verify_token)) -> ConfigResponse:
    """获取当前配置"""
    try:
        current_config = Config.get_current_config()

        return ConfigResponse(
            pad_codes=current_config["pad_codes"],
            package_names=current_config["package_names"],
            temple_ids=current_config["temple_ids"],
            default_proxy=current_config["default_proxy"],
            app_urls=current_config["app_urls"],
            timeouts=current_config["timeouts"],
            debug=current_config["debug"]
        )
    except Exception as e:
        logger.error(f"获取配置失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取配置失败: {str(e)}")


@router.post("/config", response_model=Dict[str, str])
async def update_config(
        config_update: ConfigUpdateRequest,
        _: str = Depends(verify_token)
) -> Dict[str, str]:
    """更新配置"""
    try:
        # 构建更新数据
        updates = {}

        if config_update.pad_codes is not None:
            updates["pad_codes"] = config_update.pad_codes

        if config_update.package_names is not None:
            updates["package_names"] = config_update.package_names

        if config_update.temple_ids is not None:
            updates["temple_ids"] = config_update.temple_ids

        if config_update.default_proxy is not None:
            updates["default_proxy"] = config_update.default_proxy.model_dump()

        if config_update.app_urls is not None:
            updates["app_urls"] = config_update.app_urls.model_dump()

        if config_update.timeouts is not None:
            updates["timeouts"] = config_update.timeouts.model_dump()

        if config_update.debug is not None:
            updates["debug"] = config_update.debug

        if not updates:
            raise HTTPException(status_code=400, detail="没有提供要更新的配置项")

        # 执行更新
        Config.update_config(updates)

        try:
            await ws_manager.broadcast({
                "type": "config_updated",
                "data": {
                    "updated_fields": list(updates.keys()),
                    "message": f"系统配置已更新：{', '.join(updates.keys())}"
                }
            })
        except Exception as e:
            logger.warning(f"发送配置更新通知失败: {e}")

        logger.info(f"配置更新成功: {list(updates.keys())}")
        return {"message": f"配置更新成功，更新了 {len(updates)} 项配置"}

    except Exception as e:
        logger.error(f"更新配置失败: {e}")
        raise HTTPException(status_code=500, detail=f"更新配置失败: {str(e)}")


@router.post("/config/reset", response_model=Dict[str, str])
async def reset_config(_: str = Depends(verify_token)) -> Dict[str, str]:
    """重置配置为默认值"""
    try:
        Config.reset_to_defaults()
        logger.info("配置已重置为默认值")
        return {"message": "配置已重置为默认值"}

    except Exception as e:
        logger.error(f"重置配置失败: {e}")
        raise HTTPException(status_code=500, detail=f"重置配置失败: {str(e)}")


@router.get("/config/validate", response_model=Dict[str, Any])
async def validate_config(_: str = Depends(verify_token)) -> Dict[str, Any]:
    """验证当前配置的有效性"""
    try:
        current_config = Config.get_current_config()

        validation_results = {
            "valid": True,
            "warnings": [],
            "errors": []
        }

        # 验证 PAD_CODES
        if not current_config["pad_codes"]:
            validation_results["errors"].append("PAD_CODES 不能为空")
            validation_results["valid"] = False
        elif len(current_config["pad_codes"]) > 100:
            validation_results["warnings"].append("PAD_CODES 数量过多，可能影响性能")

        # 验证 TEMPLE_IDS
        if not current_config["temple_ids"]:
            validation_results["errors"].append("TEMPLE_IDS 不能为空")
            validation_results["valid"] = False

        # 验证包名
        for pkg_type, pkg_name in current_config["package_names"].items():
            if not pkg_name or not pkg_name.strip():
                validation_results["errors"].append(f"包名 {pkg_type} 不能为空")
                validation_results["valid"] = False

        # 验证 APP_URLS
        for app_name, url in current_config["app_urls"].items():
            if not url or not url.startswith(("http://", "https://")):
                validation_results["errors"].append(f"应用URL {app_name} 格式无效")
                validation_results["valid"] = False

        # 验证超时配置
        if current_config["timeouts"]["global_timeout"] <= 0:
            validation_results["errors"].append("全局超时时间必须大于0")
            validation_results["valid"] = False

        if current_config["timeouts"]["check_task_timeout"] <= 0:
            validation_results["errors"].append("任务检查超时时间必须大于0")
            validation_results["valid"] = False

        # 验证默认代理
        proxy = current_config["default_proxy"]
        if not proxy["country"] or not proxy["code"]:
            validation_results["errors"].append("默认代理的国家和代码不能为空")
            validation_results["valid"] = False

        if not (-90 <= proxy["latitude"] <= 90):
            validation_results["errors"].append("纬度必须在 -90 到 90 之间")
            validation_results["valid"] = False

        if not (-180 <= proxy["longitude"] <= 180):
            validation_results["errors"].append("经度必须在 -180 到 180 之间")
            validation_results["valid"] = False

        logger.info(f"配置验证完成: valid={validation_results['valid']}")
        return validation_results

    except Exception as e:
        logger.error(f"配置验证失败: {e}")
        raise HTTPException(status_code=500, detail=f"配置验证失败: {str(e)}")