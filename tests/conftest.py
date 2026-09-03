"""
pytest 全局配置：让 tests/ 下的测试能 import 项目根目录的 core / eval，
并自动清理测试产生的临时目录（防止残留 SQLite 数据导致跨运行失败）。
"""
import os
import shutil
import sys

import pytest

# 项目根目录（conftest.py 所在目录的上一级）
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)


@pytest.fixture(scope="session", autouse=True)
def clean_test_tmp():
    """每个 pytest 会话开始前清理测试临时目录（兼容直接运行脚本时不清理的残留）。"""
    for d in ["_test_compress_tmp", "_test_rag_tmp", "_test_session_tmp", "_test_obs_tmp"]:
        shutil.rmtree(os.path.join(ROOT, "tests", d), ignore_errors=True)
        shutil.rmtree(os.path.join(ROOT, d), ignore_errors=True)
    yield
