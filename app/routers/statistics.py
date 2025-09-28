from datetime import datetime, timedelta
from typing import Dict, Any

from fastapi import APIRouter
from sqlalchemy import select, text, func

from app.services.database import SessionLocal, Status

router = APIRouter()


@router.get("/statistics/hourly-growth", response_model=Dict[str, Any])
async def get_hourly_account_growth():
    """获取每小时账号增长统计（按设备数量平均）"""
    async with SessionLocal() as db:
        # 获取过去24小时的账号创建数据
        now = datetime.now()
        start_time = now - timedelta(hours=24)

        # 查询过去24小时的账号创建数据，按小时分组，包含转发邮箱统计
        query = text("""
                     SELECT DATE_TRUNC('hour', created_at) as hour,
                            COUNT(*)                       as account_count,
                            COUNT(CASE WHEN for_email IS NOT NULL AND for_email != '' THEN 1 END) as forward_email_count
                     FROM google_account
                     WHERE created_at >= :start_time
                     GROUP BY DATE_TRUNC('hour', created_at)
                     ORDER BY hour
                     """)

        result = await db.execute(query, {"start_time": start_time})
        rows = result.fetchall()

        # 获取设备总数
        device_count_query = select(func.count(Status.pad_code.distinct()))
        device_count_result = await db.execute(device_count_query)
        total_devices = device_count_result.scalar() or 1  # 避免除零

        # 生成过去24小时的时间点
        time_points = []
        current = now.replace(minute=0, second=0, microsecond=0)
        for i in range(24):
            time_points.append(current - timedelta(hours=i))
        time_points.reverse()

        # 整理数据结构
        hourly_data = {}
        for row in rows:
            hourly_data[row.hour] = {
                'account_count': row.account_count,
                'forward_email_count': row.forward_email_count
            }

        # 构建时间序列数据
        total_accounts_data = []  # 每小时总账号数
        forward_email_data = []   # 每小时转发邮箱数
        avg_per_device_data = []  # 每小时平均每台设备账号数
        avg_forward_per_device_data = []  # 每小时平均每台设备转发邮箱数
        total_24h = 0
        total_forward_24h = 0

        for time_point in time_points:
            hour_data = hourly_data.get(time_point, {'account_count': 0, 'forward_email_count': 0})
            hour_count = hour_data['account_count']
            hour_forward_count = hour_data['forward_email_count']

            avg_per_device = round(hour_count / total_devices, 2) if total_devices > 0 else 0
            avg_forward_per_device = round(hour_forward_count / total_devices, 2) if total_devices > 0 else 0

            total_accounts_data.append(hour_count)
            forward_email_data.append(hour_forward_count)
            avg_per_device_data.append(avg_per_device)
            avg_forward_per_device_data.append(avg_forward_per_device)
            total_24h += hour_count
            total_forward_24h += hour_forward_count

        # 计算转发邮箱占比
        forward_email_rate_24h = round((total_forward_24h / total_24h) * 100, 2) if total_24h > 0 else 0

        # 构建返回数据
        chart_data = {
            "time_points": [tp.strftime("%Y-%m-%d %H:00") for tp in time_points],
            "total_accounts_data": total_accounts_data,
            "forward_email_data": forward_email_data,
            "avg_per_device_data": avg_per_device_data,
            "avg_forward_per_device_data": avg_forward_per_device_data,
            "summary": {
                "total_devices": total_devices,
                "time_range": f"{start_time.strftime('%Y-%m-%d %H:00')} - {now.strftime('%Y-%m-%d %H:00')}",
                "total_accounts_24h": total_24h,
                "total_forward_emails_24h": total_forward_24h,
                "forward_email_rate_24h": forward_email_rate_24h,
                "avg_per_device_24h": round(total_24h / total_devices, 2) if total_devices > 0 else 0,
                "avg_forward_per_device_24h": round(total_forward_24h / total_devices, 2) if total_devices > 0 else 0,
                "avg_per_device_per_hour": round((total_24h / 24) / total_devices, 2) if total_devices > 0 else 0,
                "avg_forward_per_device_per_hour": round((total_forward_24h / 24) / total_devices, 2) if total_devices > 0 else 0
            }
        }

        return chart_data


@router.get("/statistics/overall-summary", response_model=Dict[str, Any])
async def get_overall_summary():
    """获取总体统计摘要"""
    async with SessionLocal() as db:
        # 获取设备总数
        device_count_query = select(func.count(Status.pad_code.distinct()))
        device_count_result = await db.execute(device_count_query)
        total_devices = device_count_result.scalar() or 0

        # 获取账号统计数据，包含转发邮箱统计
        account_stats_query = text("""
                                   SELECT COUNT(*)                                                              as total_accounts,
                                          COUNT(CASE WHEN for_email IS NOT NULL AND for_email != '' THEN 1 END) as total_forward_emails,
                                          MIN(created_at)                                                       as first_account_time,
                                          MAX(created_at)                                                       as last_account_time,
                                          COUNT(CASE WHEN created_at >= NOW() - INTERVAL '24 hours' THEN 1 END) as accounts_24h,
                                          COUNT(CASE WHEN created_at >= NOW() - INTERVAL '24 hours' AND for_email IS NOT NULL AND for_email != '' THEN 1 END) as forward_emails_24h,
                                          COUNT(CASE WHEN created_at >= NOW() - INTERVAL '1 hour' THEN 1 END)   as accounts_1h,
                                          COUNT(CASE WHEN created_at >= NOW() - INTERVAL '1 hour' AND for_email IS NOT NULL AND for_email != '' THEN 1 END) as forward_emails_1h,
                                          COUNT(CASE WHEN created_at >= NOW() - INTERVAL '7 days' THEN 1 END)   as accounts_7d,
                                          COUNT(CASE WHEN created_at >= NOW() - INTERVAL '7 days' AND for_email IS NOT NULL AND for_email != '' THEN 1 END) as forward_emails_7d
                                   FROM google_account
                                   """)

        result = await db.execute(account_stats_query)
        row = result.fetchone()

        if row and total_devices > 0:
            # 计算转发邮箱占比
            forward_rate_total = round((row.total_forward_emails / row.total_accounts) * 100, 2) if row.total_accounts > 0 else 0
            forward_rate_24h = round((row.forward_emails_24h / row.accounts_24h) * 100, 2) if row.accounts_24h > 0 else 0
            forward_rate_1h = round((row.forward_emails_1h / row.accounts_1h) * 100, 2) if row.accounts_1h > 0 else 0
            forward_rate_7d = round((row.forward_emails_7d / row.accounts_7d) * 100, 2) if row.accounts_7d > 0 else 0

            summary = {
                "total_devices": total_devices,
                "total_accounts": row.total_accounts,
                "total_forward_emails": row.total_forward_emails,
                "forward_rate_total": forward_rate_total,
                "accounts_24h": row.accounts_24h,
                "forward_emails_24h": row.forward_emails_24h,
                "forward_rate_24h": forward_rate_24h,
                "accounts_1h": row.accounts_1h,
                "forward_emails_1h": row.forward_emails_1h,
                "forward_rate_1h": forward_rate_1h,
                "accounts_7d": row.accounts_7d,
                "forward_emails_7d": row.forward_emails_7d,
                "forward_rate_7d": forward_rate_7d,
                "first_account_time": row.first_account_time.isoformat() if row.first_account_time else None,
                "last_account_time": row.last_account_time.isoformat() if row.last_account_time else None,
                # 平均数计算
                "avg_total_per_device": round(row.total_accounts / total_devices, 2),
                "avg_forward_total_per_device": round(row.total_forward_emails / total_devices, 2),
                "avg_24h_per_device": round(row.accounts_24h / total_devices, 2),
                "avg_forward_24h_per_device": round(row.forward_emails_24h / total_devices, 2),
                "avg_1h_per_device": round(row.accounts_1h / total_devices, 2),
                "avg_forward_1h_per_device": round(row.forward_emails_1h / total_devices, 2),
                "avg_7d_per_device": round(row.accounts_7d / total_devices, 2),
                "avg_forward_7d_per_device": round(row.forward_emails_7d / total_devices, 2),
                "avg_per_device_per_hour_24h": round((row.accounts_24h / 24) / total_devices, 2),
                "avg_forward_per_device_per_hour_24h": round((row.forward_emails_24h / 24) / total_devices, 2),
            }
        else:
            summary = {
                "total_devices": total_devices,
                "total_accounts": 0,
                "total_forward_emails": 0,
                "forward_rate_total": 0,
                "accounts_24h": 0,
                "forward_emails_24h": 0,
                "forward_rate_24h": 0,
                "accounts_1h": 0,
                "forward_emails_1h": 0,
                "forward_rate_1h": 0,
                "accounts_7d": 0,
                "forward_emails_7d": 0,
                "forward_rate_7d": 0,
                "first_account_time": None,
                "last_account_time": None,
                "avg_total_per_device": 0,
                "avg_forward_total_per_device": 0,
                "avg_24h_per_device": 0,
                "avg_forward_24h_per_device": 0,
                "avg_1h_per_device": 0,
                "avg_forward_1h_per_device": 0,
                "avg_7d_per_device": 0,
                "avg_forward_7d_per_device": 0,
                "avg_per_device_per_hour_24h": 0,
                "avg_forward_per_device_per_hour_24h": 0,
            }

        return summary