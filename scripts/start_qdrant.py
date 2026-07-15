"""
Qdrant 启动脚本 — 自动检测并启动 Qdrant

用法:
  uv run python scripts/start_qdrant.py               # docker-compose 启动 Qdrant
  uv run python scripts/start_qdrant.py --up          # 启动全部服务 (api + qdrant)
  uv run python scripts/start_qdrant.py --check       # 仅检查状态
  uv run python scripts/start_qdrant.py --down        # 停止所有服务
"""

import argparse
import http.client
import json
import logging
import subprocess
import sys
import time
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)

QDRANT_HOST = "localhost"
QDRANT_HTTP_PORT = 6333
QDRANT_GRPC_PORT = 6334

# docker-compose.yml 路径（项目根目录下的 docker/）
COMPOSE_FILE = (
    Path(__file__).resolve().parent.parent / "docker" / "docker-compose.yml"
)


def check_qdrant() -> bool:
    """检查 Qdrant 是否已运行"""
    try:
        conn = http.client.HTTPConnection(QDRANT_HOST, QDRANT_HTTP_PORT, timeout=3)
        conn.request("GET", "/healthz")
        resp = conn.getresponse()
        conn.close()
        return resp.status == 200
    except (ConnectionRefusedError, TimeoutError, OSError):
        return False
    except Exception:
        return False


def docker_compose_cmd(*args) -> subprocess.CompletedProcess:
    """执行 docker compose 命令"""
    cmd = ["docker", "compose", "-f", str(COMPOSE_FILE), *args]
    return subprocess.run(cmd, capture_output=True, text=True, timeout=120)


def main():
    parser = argparse.ArgumentParser(description="Qdrant / 全部服务 Docker 启动")
    parser.add_argument("--check", action="store_true", help="仅检查状态")
    parser.add_argument("--down", action="store_true", help="停止所有服务")
    parser.add_argument("--up", action="store_true", help="启动全部服务 (api + qdrant)")
    args = parser.parse_args()

    if not COMPOSE_FILE.exists():
        logger.error("找不到 docker-compose.yml: %s", COMPOSE_FILE)
        return 1

    # ── 仅检查 ──
    if args.check:
        if check_qdrant():
            conn = http.client.HTTPConnection(QDRANT_HOST, QDRANT_HTTP_PORT, timeout=5)
            conn.request("GET", "/collections")
            resp = conn.getresponse()
            data = json.loads(resp.read().decode())
            conn.close()
            collections = data.get("result", {}).get("collections", [])
            names = [c["name"] for c in collections]
            logger.info("Qdrant 运行中 | 集合: %s", names or "(空)")
            return 0
        else:
            logger.info("Qdrant 未运行")
            return 1

    # ── 停止 ──
    if args.down:
        logger.info("停止所有服务...")
        r = docker_compose_cmd("down")
        if r.returncode == 0:
            logger.info("已停止")
        else:
            logger.error("停止失败:\n%s", r.stderr)
        return r.returncode

    # ── 启动全部服务 ──
    if args.up:
        logger.info("启动全部服务...")
        r = docker_compose_cmd("up", "-d")
        if r.returncode != 0:
            logger.error("启动失败:\n%s", r.stderr)
            return 1
        logger.info("等待 Qdrant 就绪...")
        for i in range(30):
            if check_qdrant():
                logger.info("Qdrant 就绪 ✓")
                break
            time.sleep(2)
        else:
            logger.warning("Qdrant 启动超时，可稍后检查日志")
        logger.info("全部服务已启动")
        logger.info("  API:     http://localhost:8000/docs")
        logger.info("  Qdrant:  http://localhost:6333/dashboard")
        return 0

    # ── 默认：仅启动 Qdrant ──
    if check_qdrant():
        logger.info("Qdrant 已在运行 ✓")
        return 0

    logger.info("通过 docker-compose 启动 Qdrant...")
    r = docker_compose_cmd("up", "-d", "qdrant")
    if r.returncode != 0:
        logger.error("启动失败:\n%s", r.stderr)
        logger.info("请手动执行: docker compose -f %s up -d", COMPOSE_FILE)
        return 1

    logger.info("等待 Qdrant 就绪...")
    for i in range(30):
        if check_qdrant():
            logger.info("Qdrant 就绪 ✓ (%.1fs)", (i + 1) * 2)
            return 0
        time.sleep(2)

    logger.warning("Qdrant 启动超时，执行以下命令查看日志:")
    logger.warning("  docker compose -f %s logs qdrant", COMPOSE_FILE)
    return 1


if __name__ == "__main__":
    sys.exit(main())
