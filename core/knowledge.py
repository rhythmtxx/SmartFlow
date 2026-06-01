"""
知识库管理模块（RAG - Retrieval-Augmented Generation）

职责：
  1. 文档导入：读取文本文件，切片，向量化，存入 ChromaDB
  2. 知识检索：把用户问题向量化，检索最相似的 Top-K 片段
  3. 持久化：知识库存在 workspace/knowledge_db/，重启不丢失

依赖：
  pip install chromadb sentence-transformers
"""
import os
import hashlib
from typing import List, Dict, Any

# 延迟导入，避免启动时就加载大模型（首次使用时才加载）
_embedding_model = None
_chroma_client = None


def _get_embedding_model():
    """懒加载 Embedding 模型（首次调用时下载/加载，约 3-5 秒）"""
    global _embedding_model
    if _embedding_model is None:
        from sentence_transformers import SentenceTransformer
        # paraphrase-multilingual-MiniLM-L12-v2：支持中英文，体积小（~120MB），效果好
        _embedding_model = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")
    return _embedding_model


def _get_chroma_client(db_path: str):
    """懒加载 ChromaDB 客户端"""
    global _chroma_client
    if _chroma_client is None:
        import chromadb
        os.makedirs(db_path, exist_ok=True)
        _chroma_client = chromadb.PersistentClient(path=db_path)
    return _chroma_client


class KnowledgeBase:
    """
    本地向量知识库。

    使用方式：
      kb = KnowledgeBase(workspace_dir)
      kb.add_document("path/to/file.txt")          # 导入文档
      results = kb.search("什么是 RAG？", top_k=3)  # 检索
    """

    def __init__(self, workspace_dir: str, chunk_size: int = 300, chunk_overlap: int = 50):
        self.db_path = os.path.join(workspace_dir, "knowledge_db")
        self.chunk_size = chunk_size        # 每个切片的最大字符数
        self.chunk_overlap = chunk_overlap  # 相邻切片的重叠字符数（保证语义连续）

    def _get_collection(self):
        """获取 ChromaDB 集合（相当于一张表）"""
        client = _get_chroma_client(self.db_path)
        return client.get_or_create_collection(
            name="documents",
            metadata={"hnsw:space": "cosine"}  # 用余弦相似度衡量向量距离
        )

    def _chunk_text(self, text: str) -> List[str]:
        """
        把长文本切成小块。
        策略：优先按段落切，段落太长再按固定长度切，相邻块有重叠。
        """
        # 先按段落分割
        paragraphs = [p.strip() for p in text.split("\n") if p.strip()]
        chunks = []
        current = ""

        for para in paragraphs:
            # 当前块加上新段落不超过 chunk_size，直接拼接
            if len(current) + len(para) <= self.chunk_size:
                current += (" " if current else "") + para
            else:
                # 当前块已满，保存并开始新块（带重叠）
                if current:
                    chunks.append(current)
                    # 重叠：把当前块的末尾 chunk_overlap 个字符带入下一块
                    overlap = current[-self.chunk_overlap:] if len(current) > self.chunk_overlap else current
                    current = overlap + " " + para
                else:
                    # 单个段落就超过 chunk_size，强制按长度切
                    for i in range(0, len(para), self.chunk_size - self.chunk_overlap):
                        chunks.append(para[i:i + self.chunk_size])
                    current = ""

        if current:
            chunks.append(current)

        return [c for c in chunks if len(c.strip()) > 10]  # 过滤太短的碎片

    def add_document(self, file_path: str) -> Dict[str, Any]:
        """
        导入一个文档到知识库。
        支持 .txt / .md 格式（PDF 需要额外依赖，暂不支持）。
        返回导入统计信息。
        """
        if not os.path.exists(file_path):
            return {"success": False, "error": f"文件不存在: {file_path}"}

        ext = os.path.splitext(file_path)[1].lower()
        if ext not in [".txt", ".md"]:
            return {"success": False, "error": f"暂不支持 {ext} 格式，请使用 .txt 或 .md 文件"}

        try:
            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                text = f.read()
        except Exception as e:
            return {"success": False, "error": f"读取文件失败: {e}"}

        if not text.strip():
            return {"success": False, "error": "文件内容为空"}

        # 切片
        chunks = self._chunk_text(text)
        if not chunks:
            return {"success": False, "error": "文档切片后内容为空"}

        # 向量化（批量处理，效率更高）
        model = _get_embedding_model()
        embeddings = model.encode(chunks, show_progress_bar=False).tolist()

        # 生成唯一 ID（文件名 + chunk 序号 + 内容 hash，防止重复导入）
        file_hash = hashlib.md5(text.encode()).hexdigest()[:8]
        file_name = os.path.basename(file_path)
        ids = [f"{file_name}_{file_hash}_{i}" for i in range(len(chunks))]
        metadatas = [{"source": file_name, "chunk_index": i} for i in range(len(chunks))]

        # 存入 ChromaDB（如果 ID 已存在会自动跳过，实现幂等导入）
        collection = self._get_collection()
        collection.upsert(
            documents=chunks,
            embeddings=embeddings,
            ids=ids,
            metadatas=metadatas
        )

        return {
            "success": True,
            "file": file_name,
            "chunks": len(chunks),
            "total_chars": len(text)
        }

    def add_text(self, text: str, source_name: str = "manual") -> Dict[str, Any]:
        """直接导入一段文本（不需要文件）"""
        chunks = self._chunk_text(text)
        if not chunks:
            return {"success": False, "error": "文本内容为空"}

        model = _get_embedding_model()
        embeddings = model.encode(chunks, show_progress_bar=False).tolist()

        text_hash = hashlib.md5(text.encode()).hexdigest()[:8]
        ids = [f"{source_name}_{text_hash}_{i}" for i in range(len(chunks))]
        metadatas = [{"source": source_name, "chunk_index": i} for i in range(len(chunks))]

        collection = self._get_collection()
        collection.upsert(
            documents=chunks,
            embeddings=embeddings,
            ids=ids,
            metadatas=metadatas
        )

        return {"success": True, "source": source_name, "chunks": len(chunks)}

    def search(self, query: str, top_k: int = 3) -> List[Dict[str, Any]]:
        """
        检索与 query 最相关的 top_k 个文本片段。
        返回列表，每项包含 text（内容）、source（来源文件）、score（相似度）。
        """
        collection = self._get_collection()

        # 知识库为空时直接返回
        if collection.count() == 0:
            return []

        model = _get_embedding_model()
        query_embedding = model.encode([query], show_progress_bar=False).tolist()

        results = collection.query(
            query_embeddings=query_embedding,
            n_results=min(top_k, collection.count()),  # 防止 top_k 超过总数
            include=["documents", "metadatas", "distances"]
        )

        output = []
        for i, doc in enumerate(results["documents"][0]):
            distance = results["distances"][0][i]
            # ChromaDB 余弦距离：0 = 完全相同，2 = 完全相反
            # 转换为相似度分数（0~1，越高越相关）
            score = round(1 - distance / 2, 4)
            output.append({
                "text": doc,
                "source": results["metadatas"][0][i].get("source", "unknown"),
                "score": score
            })

        # 按相似度降序排列
        output.sort(key=lambda x: x["score"], reverse=True)
        return output

    def get_stats(self) -> Dict[str, Any]:
        """获取知识库统计信息"""
        try:
            collection = self._get_collection()
            count = collection.count()
            return {"total_chunks": count, "status": "ready" if count > 0 else "empty"}
        except Exception:
            return {"total_chunks": 0, "status": "empty"}

    def clear(self) -> None:
        """清空知识库"""
        try:
            client = _get_chroma_client(self.db_path)
            client.delete_collection("documents")
        except Exception:
            pass
