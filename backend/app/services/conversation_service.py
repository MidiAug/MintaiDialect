"""
对话/会话管理服务
职责：管理对话历史、会话元数据、持久化存储
"""
from typing import Dict, List, Optional
from pathlib import Path
from datetime import datetime, timedelta
import json
import uuid
import logging

logger = logging.getLogger(__name__)

# ================== 内部状态 ==================
# 内存缓存（生产环境建议使用Redis）
_conversation_history: Dict[str, List[Dict[str, str]]] = {}
_session_metadata: Dict[str, Dict[str, any]] = {}

# JSON文件存储路径
CONVERSATIONS_DIR = Path("conversations")
CONVERSATIONS_DIR.mkdir(exist_ok=True)


# ================== 公开 API ==================

def generate_session_id() -> str:
    """生成新的会话ID"""
    return str(uuid.uuid4())


def get_or_create_session(session_id: Optional[str]) -> str:
    """
    获取或创建会话ID
    
    Args:
        session_id: 可选的现有会话ID
        
    Returns:
        会话ID（新创建或已存在的）
    """
    if not session_id:
        session_id = generate_session_id()
        _conversation_history[session_id] = []
        _session_metadata[session_id] = {
            "created_at": datetime.now(),
            "last_activity": datetime.now(),
            "message_count": 0
        }
        # 保存到文件
        _save_conversation_to_file(session_id, [])
        _save_session_metadata_to_file(session_id, _session_metadata[session_id])
    else:
        # 更新最后活动时间
        if session_id in _session_metadata:
            _session_metadata[session_id]["last_activity"] = datetime.now()
        else:
            # 如果会话ID不存在，尝试从文件加载
            loaded_history = _load_conversation_from_file(session_id)
            loaded_metadata = _load_session_metadata_from_file(session_id)
            
            if loaded_history or loaded_metadata:
                # 从文件恢复会话
                _conversation_history[session_id] = loaded_history
                _session_metadata[session_id] = loaded_metadata
                _session_metadata[session_id]["last_activity"] = datetime.now()
                logger.info(f"[CONV] 从文件恢复会话: {session_id}")
            else:
                # 创建新会话
                _conversation_history[session_id] = []
                _session_metadata[session_id] = {
                    "created_at": datetime.now(),
                    "last_activity": datetime.now(),
                    "message_count": 0
                }
                _save_conversation_to_file(session_id, [])
                _save_session_metadata_to_file(session_id, _session_metadata[session_id])
    return session_id


def add_to_conversation_history(session_id: str, user_input: str, ai_response: str):
    """
    添加对话到历史记录
    
    Args:
        session_id: 会话ID
        user_input: 用户输入
        ai_response: AI回复
    """
    if session_id not in _conversation_history:
        _conversation_history[session_id] = []
    
    _conversation_history[session_id].append({
        "role": "user",
        "content": user_input,
        "timestamp": datetime.now().isoformat()
    })
    _conversation_history[session_id].append({
        "role": "assistant",
        "content": ai_response,
        "timestamp": datetime.now().isoformat()
    })
    
    # 更新会话元数据
    if session_id in _session_metadata:
        _session_metadata[session_id]["message_count"] += 1
        _session_metadata[session_id]["last_activity"] = datetime.now()
    
    # 保存到文件
    _save_conversation_to_file(session_id, _conversation_history[session_id])
    _save_session_metadata_to_file(session_id, _session_metadata[session_id])


def get_conversation_history(session_id: str) -> List[Dict[str, str]]:
    """
    获取会话历史
    
    Args:
        session_id: 会话ID
        
    Returns:
        对话历史列表
    """
    return _conversation_history.get(session_id, [])


def get_session_metadata(session_id: str) -> Optional[Dict[str, any]]:
    """
    获取会话元数据
    
    Args:
        session_id: 会话ID
        
    Returns:
        会话元数据，如果不存在则返回 None
    """
    return _session_metadata.get(session_id)


def delete_session(session_id: str):
    """
    删除会话
    
    Args:
        session_id: 会话ID
    """
    _conversation_history.pop(session_id, None)
    _session_metadata.pop(session_id, None)
    
    # 删除对应的JSON文件
    try:
        (CONVERSATIONS_DIR / f"{session_id}.json").unlink(missing_ok=True)
        (CONVERSATIONS_DIR / f"{session_id}_metadata.json").unlink(missing_ok=True)
    except Exception as e:
        logger.error(f"[CONV] 删除会话文件失败 {session_id}: {e}")


def list_all_sessions() -> List[Dict[str, any]]:
    """
    获取所有会话列表
    
    Returns:
        会话信息列表
    """
    sessions = []
    for session_id, metadata in _session_metadata.items():
        history_count = len(_conversation_history.get(session_id, []))
        sessions.append({
            "session_id": session_id,
            "created_at": metadata.get("created_at").isoformat() if metadata.get("created_at") else None,
            "last_activity": metadata.get("last_activity").isoformat() if metadata.get("last_activity") else None,
            "message_count": metadata.get("message_count", 0),
            "history_count": history_count
        })
    return sessions


def cleanup_old_sessions(hours: int = 24):
    """
    清理超过指定时长的旧会话
    
    Args:
        hours: 保留时长（小时）
    """
    cutoff_time = datetime.now() - timedelta(hours=hours)
    sessions_to_remove = []
    
    for session_id, metadata in _session_metadata.items():
        if metadata["last_activity"] < cutoff_time:
            sessions_to_remove.append(session_id)
    
    for session_id in sessions_to_remove:
        delete_session(session_id)
        logger.info(f"[CONV] 清理过期会话: {session_id}")


# ================== 内部辅助函数 ==================

def _load_conversation_from_file(session_id: str) -> List[Dict[str, str]]:
    """从JSON文件加载会话历史"""
    file_path = CONVERSATIONS_DIR / f"{session_id}.json"
    if file_path.exists():
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"[CONV] 加载会话文件失败 {session_id}: {e}")
    return []


def _save_conversation_to_file(session_id: str, history: List[Dict[str, str]]):
    """保存会话历史到JSON文件"""
    file_path = CONVERSATIONS_DIR / f"{session_id}.json"
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(history, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"[CONV] 保存会话文件失败 {session_id}: {e}")


def _load_session_metadata_from_file(session_id: str) -> Dict[str, any]:
    """从JSON文件加载会话元数据"""
    file_path = CONVERSATIONS_DIR / f"{session_id}_metadata.json"
    if file_path.exists():
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                # 转换时间字符串回datetime对象
                if 'created_at' in data and isinstance(data['created_at'], str):
                    data['created_at'] = datetime.fromisoformat(data['created_at'])
                if 'last_activity' in data and isinstance(data['last_activity'], str):
                    data['last_activity'] = datetime.fromisoformat(data['last_activity'])
                return data
        except Exception as e:
            logger.error(f"[CONV] 加载会话元数据失败 {session_id}: {e}")
    return {}


def _save_session_metadata_to_file(session_id: str, metadata: Dict[str, any]):
    """保存会话元数据到JSON文件"""
    file_path = CONVERSATIONS_DIR / f"{session_id}_metadata.json"
    try:
        # 转换datetime对象为字符串
        data = metadata.copy()
        if 'created_at' in data and isinstance(data['created_at'], datetime):
            data['created_at'] = data['created_at'].isoformat()
        if 'last_activity' in data and isinstance(data['last_activity'], datetime):
            data['last_activity'] = data['last_activity'].isoformat()
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"[CONV] 保存会话元数据失败 {session_id}: {e}")

