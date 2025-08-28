import redis
import json
import traceback
from lark.settings import REDIS_HOST
from typing import Any, Optional


r = redis.Redis(host=REDIS_HOST, port=6379, decode_responses=True)
key_prefix = 'lark:'


def set_(key, val, ex):
    if type(val) == dict:
        val = json.dumps(val)
    r.set(key_prefix+key, val, ex=ex)


def get(key: str) -> Optional[Any]:
    """Get value from Redis and deserialize from JSON if needed"""
    try:
        value = r.get(key_prefix+key)
        if value is None:
            return None
        return json.loads(value)
    except Exception as e:
        print(f"Error getting key {key} from Redis: {e}")
        return None


def set_nx(key, ex=60):
    if r.setnx(key_prefix+key, 1):
        r.expire(key_prefix+key, ex)
        return True
    elif r.ttl(key_prefix+key) == -1:
        r.expire(key_prefix + key, ex)

    return False


def del_(key):
    return r.delete(key_prefix+key)


def exist(key):
    return r.exists(key_prefix+key)


def rpush(key, values):
    if type(values) == list:
        if len(values) > 0:
            return r.rpush(key_prefix+key, *values)
    else:
        return r.rpush(key_prefix + key, values)


def lpop(key):
    return r.lpop(key_prefix+key)


def llen(key):
    return r.llen(key_prefix+key)


def lrange(key, start, end):
    return r.lrange(key_prefix+key, start, end)


def sadd(key, values):
    if type(values) == set or type(values) == list:
        if len(values) > 0:
            return r.sadd(key_prefix+key, *values)
    else:
        return r.sadd(key_prefix+key, values)


def spop(key, count=None):
    return r.spop(key_prefix+key, count)


def scard(key):
    return r.scard(key_prefix+key)


def smembers(key):
    return r.smembers(key_prefix+key)


def expire(key, expire_seconds):
    return r.expire(key_prefix+key, expire_seconds)


def set(key: str, value: Any, ex: Optional[int] = None) -> bool:
    """Set value in Redis with JSON serialization"""
    try:
        json_value = json.dumps(value)
        return r.set(key_prefix+key, json_value, ex=ex)
    except Exception as e:
        print(f"Error setting key {key} in Redis: {e}")
        return False


def setex(key: str, time: int, value: Any) -> bool:
    """Set value in Redis with expiration time and JSON serialization"""
    try:
        json_value = json.dumps(value)
        return r.setex(key_prefix+key, time, json_value)
    except Exception as e:
        print(f"Error setting key {key} in Redis with expiration: {e}")
        return False


#for hash operations

def hget(key: str, field: str) -> Optional[Any]:
    """Get value from Redis hash and deserialize from JSON if needed"""
    try:
        value = r.hget(key_prefix+key, field)
        if value is None:
            return None
        return json.loads(value)
    except Exception as e:
        print(f"Error getting hash field {field} from key {key} in Redis: {e}")
        return None


def hset(key: str, field: str, value: Any) -> bool:
    """Set value in Redis hash with JSON serialization"""
    try:
        json_value = json.dumps(value)
        result = r.hset(key_prefix+key, field, json_value)
        # Redis hset returns number of fields added (1 for new, 0 for existing)
        # We want to return True if the operation succeeded
        return result >= 0  # Any non-negative result means success
    except Exception as e:
        print(f"Error setting hash field {field} in key {key} in Redis: {e}")
        return False


def hgetall(key: str) -> dict:
    """Get all fields and values from Redis hash"""
    try:
        hash_data = r.hgetall(key_prefix+key)
        result = {}
        for field, value in hash_data.items():
            try:
                result[field] = json.loads(value)
            except:
                result[field] = value  # Keep as string if not JSON
        return result
    except Exception as e:
        print(f"Error getting all hash fields from key {key} in Redis: {e}")
        return {}


def hdel(key: str, *fields: str) -> int:
    """Delete fields from Redis hash"""
    try:
        return r.hdel(key_prefix+key, *fields)
    except Exception as e:
        print(f"Error deleting hash fields from key {key} in Redis: {e}")
        return 0


def hexists(key: str, field: str) -> bool:
    """Check if field exists in Redis hash"""
    try:
        return r.hexists(key_prefix+key, field)
    except Exception as e:
        print(f"Error checking hash field existence for key {key} in Redis: {e}")
        return False


def ttl(key: str) -> int:
    """Get time to live for a key in seconds"""
    try:
        return r.ttl(key_prefix+key)
    except Exception as e:
        print(f"Error getting TTL for key {key} in Redis: {e}")
        return -1


def delete(key: str) -> int:
    """Delete a key from Redis"""
    try:
        return r.delete(key_prefix+key)
    except Exception as e:
        print(f"Error deleting key {key} from Redis: {e}")
        return 0
