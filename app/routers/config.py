from typing import Dict, Any, List

from fastapi import APIRouter, HTTPException, Depends

from app.config import Config
from app.dependencies.auth_middleware import verify_token
from app.models.config import (
    ConfigUpdateRequest, ConfigResponse, EnvVarUpdateRequest,
    EnvVarDeleteRequest
)
from app.services.logger import get_logger
from app.services.websocket_manager import ws_manager

router = APIRouter()
logger = get_logger("config_router")


@router.get("/config", response_model=ConfigResponse)
async def get_config(_: str = Depends(verify_token)) -> ConfigResponse:
    """获取当前配置"""
    try:
        current_config = Config.get_current_config()

        # 获取自定义环境变量
        custom_env_vars = []
        # 读取 .env 文件中的所有变量
        from pathlib import Path
        env_file = Path(".env")
        if env_file.exists():
            with open(env_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split(sep='=')
                        # 跳过系统配置的变量
                        if key not in ['DEBUG', 'DATABASE_URL', 'JWT_SECRET_KEY', 'ADMIN_USERNAME',
                                       'ADMIN_PASSWORD', 'PADE_CODE_LIST', 'PACKAGE_NAMES',
                                       'PROXY_CONFIG', 'APP_URLS', 'GLOBAL_TIMEOUT_MINUTES',
                                       'CHECK_TASK_TIMEOUT_MINUTES', 'TEMPLE_IDS']:
                            custom_env_vars.append({
                                'key': key,
                                'value': value.strip('"\''),
                                'description': f'自定义环境变量: {key}'
                            })

        return ConfigResponse(
            pad_codes=current_config["pad_codes"],
            package_names=current_config["package_names"],
            temple_ids=current_config["temple_ids"],
            default_proxy=current_config["default_proxy"],
            app_urls=current_config["app_urls"],
            timeouts=current_config["timeouts"],
            debug=current_config["debug"],
            jwt_secret_key=current_config["jwt_secret_key"],
            admin_credentials=current_config["admin_credentials"],
            database_url=current_config["database_url"],
            custom_env_vars=custom_env_vars
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

        if config_update.jwt_secret_key is not None:
            updates["jwt_secret_key"] = config_update.jwt_secret_key

        if config_update.admin_credentials is not None:
            updates["admin_credentials"] = config_update.admin_credentials.model_dump()

        if config_update.database_url is not None:
            updates["database_url"] = config_update.database_url

        # 处理自定义环境变量
        if config_update.custom_env_vars is not None:
            for env_var in config_update.custom_env_vars:
                Config.add_custom_env_var(env_var.key, env_var.value)

        if not updates and not config_update.custom_env_vars:
            raise HTTPException(status_code=400, detail="没有提供要更新的配置项")

        # 执行更新
        if updates:
            Config.update_config(updates)

        try:
            await ws_manager.broadcast({
                "type": "config_updated",
                "data": {
                    "updated_fields": list(updates.keys()) +
                                      ([f"custom_env_var_{var.key}" for var in config_update.custom_env_vars]
                                       if config_update.custom_env_vars else []),
                    "message": f"系统配置已更新并持久化：{', '.join(list(updates.keys()) + ([f'环境变量_{var.key}' for var in config_update.custom_env_vars] if config_update.custom_env_vars else []))}"
                }
            })
        except Exception as e:
            logger.warning(f"发送配置更新通知失败: {e}")

        logger.info(f"配置更新成功: {list(updates.keys())}")
        return {"message": f"配置更新成功并已持久化，更新了 {len(updates)} 项配置"}

    except Exception as e:
        logger.error(f"更新配置失败: {e}")
        raise HTTPException(status_code=500, detail=f"更新配置失败: {str(e)}")


@router.post("/config/reset", response_model=Dict[str, str])
async def reset_config(_: str = Depends(verify_token)) -> Dict[str, str]:
    """重置配置为默认值"""
    try:
        Config.reset_to_defaults()
        logger.info("配置已重置为默认值并持久化")

        try:
            await ws_manager.broadcast({
                "type": "config_updated",
                "data": {
                    "updated_fields": ["ALL"],
                    "message": "系统配置已重置为默认值"
                }
            })
        except Exception as e:
            logger.warning(f"发送配置重置通知失败: {e}")

        return {"message": "配置已重置为默认值并已持久化"}

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

        # 验证数据库URL
        if not current_config["database_url"]:
            validation_results["errors"].append("数据库URL不能为空")
            validation_results["valid"] = False

        # 验证JWT密钥
        if len(current_config["jwt_secret_key"]) < 32:
            validation_results["warnings"].append("JWT密钥长度建议至少32字符")

        # 验证管理员凭据
        admin_creds = current_config["admin_credentials"]
        if not admin_creds["username"] or not admin_creds["password"]:
            validation_results["errors"].append("管理员用户名和密码不能为空")
            validation_results["valid"] = False

        if len(admin_creds["password"]) < 6:
            validation_results["warnings"].append("管理员密码建议至少6个字符")

        logger.info(f"配置验证完成: valid={validation_results['valid']}")
        return validation_results

    except Exception as e:
        logger.error(f"配置验证失败: {e}")
        raise HTTPException(status_code=500, detail=f"配置验证失败: {str(e)}")


@router.post("/config/env-var", response_model=Dict[str, str])
async def add_env_var(
        env_var: EnvVarUpdateRequest,
        _: str = Depends(verify_token)
) -> Dict[str, str]:
    """添加或更新自定义环境变量"""
    try:
        Config.add_custom_env_var(env_var.key, env_var.value)

        logger.info(f"环境变量 {env_var.key} 已添加/更新")

        try:
            await ws_manager.broadcast({
                "type": "config_updated",
                "data": {
                    "updated_fields": [f"env_var_{env_var.key}"],
                    "message": f"环境变量 {env_var.key} 已更新"
                }
            })
        except Exception as e:
            logger.warning(f"发送环境变量更新通知失败: {e}")

        return {"message": f"环境变量 {env_var.key} 已成功添加/更新并持久化"}

    except Exception as e:
        logger.error(f"添加环境变量失败: {e}")
        raise HTTPException(status_code=500, detail=f"添加环境变量失败: {str(e)}")


@router.delete("/config/env-var", response_model=Dict[str, str])
async def delete_env_var(
        env_var: EnvVarDeleteRequest,
        _: str = Depends(verify_token)
) -> Dict[str, str]:
    """删除自定义环境变量"""
    try:
        # 防止删除系统核心变量
        protected_vars = [
            'DEBUG', 'DATABASE_URL', 'JWT_SECRET_KEY', 'ADMIN_USERNAME',
            'ADMIN_PASSWORD', 'PADE_CODE_LIST', 'PACKAGE_NAMES',
            'PROXY_CONFIG', 'APP_URLS', 'GLOBAL_TIMEOUT_MINUTES',
            'CHECK_TASK_TIMEOUT_MINUTES', 'TEMPLE_IDS'
        ]

        if env_var.key in protected_vars:
            raise HTTPException(
                status_code=400,
                detail=f"不能删除系统核心变量: {env_var.key}"
            )

        # 检查变量是否存在
        if not Config.get_custom_env_var(env_var.key):
            raise HTTPException(
                status_code=404,
                detail=f"环境变量 {env_var.key} 不存在"
            )

        Config.remove_env_var(env_var.key)

        logger.info(f"环境变量 {env_var.key} 已删除")

        try:
            await ws_manager.broadcast({
                "type": "config_updated",
                "data": {
                    "updated_fields": [f"deleted_env_var_{env_var.key}"],
                    "message": f"环境变量 {env_var.key} 已删除"
                }
            })
        except Exception as e:
            logger.warning(f"发送环境变量删除通知失败: {e}")

        return {"message": f"环境变量 {env_var.key} 已成功删除"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除环境变量失败: {e}")
        raise HTTPException(status_code=500, detail=f"删除环境变量失败: {str(e)}")


@router.get("/config/env-vars", response_model=List[Dict[str, Any]])
async def get_all_env_vars(_: str = Depends(verify_token)) -> List[Dict[str, Any]]:
    """获取所有环境变量"""
    try:
        env_vars = []

        # 读取 .env 文件
        from pathlib import Path
        env_file = Path(".env")
        if env_file.exists():
            with open(env_file, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)

                        # 标记系统变量和自定义变量
                        is_system = key in [
                            'DEBUG', 'DATABASE_URL', 'JWT_SECRET_KEY', 'ADMIN_USERNAME',
                            'ADMIN_PASSWORD', 'PADE_CODE_LIST', 'PACKAGE_NAMES',
                            'PROXY_CONFIG', 'APP_URLS', 'GLOBAL_TIMEOUT_MINUTES',
                            'CHECK_TASK_TIMEOUT_MINUTES', 'TEMPLE_IDS'
                        ]

                        env_vars.append({
                            'key': key,
                            'value': value.strip('"\'') if not is_system else '***',  # 隐藏系统变量值
                            'is_system': is_system,
                            'description': f'{"系统变量" if is_system else "自定义变量"}: {key}',
                            'line_number': line_num
                        })

        return env_vars

    except Exception as e:
        logger.error(f"获取环境变量列表失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取环境变量列表失败: {str(e)}")


@router.post("/config/backup", response_model=Dict[str, Any])
async def backup_config(_: str = Depends(verify_token)) -> Dict[str, Any]:
    """备份当前配置"""
    try:
        import datetime
        from pathlib import Path

        current_config = Config.get_current_config()
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

        # 创建备份目录
        backup_dir = Path("config_backups")
        backup_dir.mkdir(exist_ok=True)

        # 备份文件路径
        backup_file = backup_dir / f"config_backup_{timestamp}.json"

        # 保存配置到备份文件
        import json
        with open(backup_file, 'w', encoding='utf-8') as f:
            json.dump(current_config, f, ensure_ascii=False, indent=2)

        # 同时备份 .env 文件
        env_backup_file = backup_dir / f"env_backup_{timestamp}.env"
        env_file = Path(".env")
        if env_file.exists():
            import shutil
            shutil.copy2(env_file, env_backup_file)

        logger.info(f"配置备份完成: {backup_file}")

        return {
            "message": "配置备份成功",
            "backup_file": str(backup_file),
            "env_backup_file": str(env_backup_file) if env_file.exists() else None,
            "timestamp": timestamp
        }

    except Exception as e:
        logger.error(f"配置备份失败: {e}")
        raise HTTPException(status_code=500, detail=f"配置备份失败: {str(e)}")


@router.get("/config/backups", response_model=List[Dict[str, Any]])
async def list_config_backups(_: str = Depends(verify_token)) -> List[Dict[str, Any]]:
    """列出所有配置备份"""
    try:
        from pathlib import Path
        import os

        backup_dir = Path("config_backups")
        if not backup_dir.exists():
            return []

        backups = []
        for backup_file in backup_dir.glob("config_backup_*.json"):
            stat = backup_file.stat()
            backups.append({
                "filename": backup_file.name,
                "timestamp": backup_file.stem.replace("config_backup_", ""),
                "size": stat.st_size,
                "created_at": stat.st_ctime,
                "path": str(backup_file)
            })

        # 按创建时间倒序排列
        backups.sort(key=lambda x: x["created_at"], reverse=True)

        return backups

    except Exception as e:
        logger.error(f"获取备份列表失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取备份列表失败: {str(e)}")


@router.post("/config/restore/{backup_filename}", response_model=Dict[str, str])
async def restore_config(
        backup_filename: str,
        _: str = Depends(verify_token)
) -> Dict[str, str]:
    """从备份恢复配置"""
    try:
        from pathlib import Path
        import json

        backup_file = Path("config_backups") / backup_filename
        if not backup_file.exists():
            raise HTTPException(status_code=404, detail="备份文件不存在")

        # 读取备份配置
        with open(backup_file, 'r', encoding='utf-8') as f:
            backup_config_json = json.load(f)

        # 恢复配置
        Config.update_config(backup_config_json)

        logger.info(f"配置已从备份恢复: {backup_filename}")

        try:
            await ws_manager.broadcast({
                "type": "config_updated",
                "data": {
                    "updated_fields": ["ALL"],
                    "message": f"配置已从备份 {backup_filename} 恢复"
                }
            })
        except Exception as e:
            logger.warning(f"发送配置恢复通知失败: {e}")

        return {"message": f"配置已成功从备份 {backup_filename} 恢复"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"配置恢复失败: {e}")
        raise HTTPException(status_code=500, detail=f"配置恢复失败: {str(e)}")


@router.delete("/config/backup/{backup_filename}", response_model=Dict[str, str])
async def delete_backup(
        backup_filename: str,
        _: str = Depends(verify_token)
) -> Dict[str, str]:
    """删除指定的备份文件"""
    try:
        from pathlib import Path
        import os

        # 验证文件名安全性，防止路径遍历攻击
        if '..' in backup_filename or '/' in backup_filename or '\\' in backup_filename:
            raise HTTPException(status_code=400, detail="非法的文件名")

        backup_file = Path("config_backups") / backup_filename

        if not backup_file.exists():
            raise HTTPException(status_code=404, detail="备份文件不存在")

        # 检查文件是否是配置备份文件
        if not backup_filename.startswith('config_backup_') or not backup_filename.endswith('.json'):
            raise HTTPException(status_code=400, detail="只能删除配置备份文件")

        # 删除主备份文件
        os.remove(backup_file)

        # 尝试删除对应的环境变量备份文件
        env_backup_file = Path("config_backups") / backup_filename.replace('config_backup_', 'env_backup_').replace('.json', '.env')
        if env_backup_file.exists():
            os.remove(env_backup_file)

        logger.info(f"备份文件删除成功: {backup_filename}")

        try:
            await ws_manager.broadcast({
                "type": "config_updated",
                "data": {
                    "updated_fields": ["backup_deleted"],
                    "message": f"备份文件 {backup_filename} 已删除"
                }
            })
        except Exception as e:
            logger.warning(f"发送备份删除通知失败: {e}")

        return {"message": f"备份文件 {backup_filename} 删除成功"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除备份文件失败: {e}")
        raise HTTPException(status_code=500, detail=f"删除备份文件失败: {str(e)}")