"""系统健康检查脚本

用法:
    uv run python scripts/health_check.py
    uv run python scripts/health_check.py --url http://localhost:8000
"""

import argparse
import httpx
import asyncio
import sys


async def check(url: str):
    endpoints = [
        f"{url}/api/v1/admin/health",
        f"{url}/api/v1/admin/stats",
        f"{url}/docs",
    ]

    async with httpx.AsyncClient(timeout=10) as client:
        for ep in endpoints:
            try:
                r = await client.get(ep, headers={"X-Admin-Key": "admin-secret-key"})
                print(f"  ✓ {ep} -> {r.status_code}")
            except Exception as e:
                print(f"  ✗ {ep} -> {e}")
                return False
    return True


def main():
    parser = argparse.ArgumentParser(description="AiCustomerService 健康检查")
    parser.add_argument("--url", default="http://localhost:8000", help="服务地址")
    args = parser.parse_args()

    print(f"健康检查: {args.url}")
    success = asyncio.run(check(args.url))
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
