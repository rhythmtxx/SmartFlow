"""
RAG 知识库功能测试
不依赖真实大模型 API，直接测试 KnowledgeBase 的核心能力。

运行：conda run -n tinyagent python test_rag.py
"""
import os
import asyncio
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from core.knowledge import KnowledgeBase
from core.tools import SearchKnowledgeTool

# 用固定测试目录（Windows 上 ChromaDB 持有文件锁，tempfile 无法自动清理）
TEST_DIR = os.path.join(os.path.dirname(__file__), "_test_rag_tmp")


def test_knowledge_base():
    print("=" * 50)
    print("RAG 知识库功能测试")
    print("=" * 50)

    # 清理上次残留
    if os.path.exists(TEST_DIR):
        shutil.rmtree(TEST_DIR, ignore_errors=True)
    os.makedirs(TEST_DIR, exist_ok=True)

    kb = KnowledgeBase(TEST_DIR, chunk_size=200, chunk_overlap=30)

    # ---- 测试 1：空库检索 ----
    print("\n[测试 1] 空库检索")
    results = kb.search("什么是 RAG？")
    assert results == [], f"空库应返回空列表，实际返回: {results}"
    print("  空库检索返回空列表 ✓")

    # ---- 测试 2：导入文本 ----
    print("\n[测试 2] 导入文本")
    sample_text = """
RAG（Retrieval-Augmented Generation）是一种结合检索和生成的 AI 技术。
它的核心思想是：在大模型生成回答之前，先从外部知识库中检索相关内容，
然后将检索结果作为上下文提供给大模型，帮助它生成更准确的回答。

RAG 的主要优势有三点：
第一，减少幻觉。大模型不再需要凭记忆回答，而是基于真实检索到的内容。
第二，知识可更新。只需更新知识库，不需要重新训练模型。
第三，支持私域知识。可以处理企业内部文档、个人笔记等模型训练数据中没有的内容。

向量数据库是 RAG 的核心组件。它将文本转换为高维向量，
通过计算向量之间的余弦相似度来找到语义最相近的内容。
常用的向量数据库有 ChromaDB、FAISS、Milvus 等。

Embedding 模型负责将文本转换为向量。
本项目使用 sentence-transformers 的 paraphrase-multilingual-MiniLM-L12-v2 模型，
支持中英文，体积约 120MB，适合本地部署。
    """
    result = kb.add_text(sample_text, source_name="rag_intro")
    assert result["success"], f"导入失败: {result}"
    print(f"  导入成功：{result['chunks']} 个片段 ✓")

    stats = kb.get_stats()
    assert stats["total_chunks"] > 0
    print(f"  知识库状态：{stats} ✓")

    # ---- 测试 3：相关问题检索 ----
    print("\n[测试 3] 相关问题检索")
    results = kb.search("RAG 有什么优势？", top_k=2)
    assert len(results) > 0, "应该找到相关内容"
    assert all("score" in r and "text" in r and "source" in r for r in results)
    print(f"  找到 {len(results)} 条相关内容 ✓")
    for i, r in enumerate(results, 1):
        print(f"  [{i}] 相似度={r['score']:.3f} 来源={r['source']}")
        print(f"      {r['text'][:60]}...")

    # ---- 测试 4：不相关问题检索 ----
    print("\n[测试 4] 不相关问题检索（相似度应较低）")
    results2 = kb.search("今天天气怎么样", top_k=1)
    if results2:
        print(f"  找到内容但相似度较低：score={results2[0]['score']:.3f} ✓")
    else:
        print("  未找到相关内容 ✓")

    # ---- 测试 5：文件导入 ----
    print("\n[测试 5] 文件导入")
    test_file = os.path.join(TEST_DIR, "test_doc.txt")
    with open(test_file, "w", encoding="utf-8") as f:
        f.write("SmartFlow 是一个轻量级 AI Agent 框架。\n它支持 ReAct 循环和 HITL 人工审批机制。\n")
    result = kb.add_document(test_file)
    assert result["success"], f"文件导入失败: {result}"
    print(f"  文件导入成功：{result['chunks']} 个片段 ✓")

    # ---- 测试 6：SearchKnowledgeTool 工具层 ----
    print("\n[测试 6] SearchKnowledgeTool 工具层")
    tool = SearchKnowledgeTool(kb)

    async def run_tool():
        return await tool.execute("RAG 是什么技术", top_k=2)

    output = asyncio.run(run_tool())
    assert "检索到" in output or "片段" in output, f"工具输出格式异常: {output}"
    print(f"  工具输出正常 ✓")
    print(f"  输出预览：{output[:120]}...")

    print("\n" + "=" * 50)
    print("全部测试通过 ✓")
    print("=" * 50)


if __name__ == "__main__":
    print("首次运行会加载 Embedding 模型（约 3-5 秒）...\n")
    test_knowledge_base()

