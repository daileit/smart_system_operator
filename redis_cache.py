import redis
import json
import os
import jsonlog
import config as env_config

logger = jsonlog.setup_logger("cache")

redis_config = env_config.Config(group="REDIS")
redisHost = redis_config.get("REDIS_HOST")
redisPassword = redis_config.get("REDIS_PASSWORD")

init_default_data = [
    {'role': 'system', 'content': 'Initialize the system with default data'},
]

class RedisClient:
    def __init__(self, host=redisHost, port=6379, db=0):
        # Initialize the Redis connection
        self.client = redis.Redis(host=host, port=port, db=db, decode_responses=True)
        self.init_default_data = init_default_data
        try:
            self.set_json("init_default_data", init_default_data)
        except redis.RedisError:
            return None
    def delete_key(self, key):
        try:
            return self.client.delete(key) > 0
        except redis.RedisError as e:
            logger.warning(f"Error deleting key {key}: {e}")
            return False

    def set_string(self, key, value):
        # Set a string value in Redis
        self.client.set(key, value)

    def get_string(self, key):
        # Retrieve a string value from Redis
        return self.client.get(key)

    def set_json(self, key, value, ttl=None):
        # Serialize the JSON object and set it in Redis
        json_value = json.dumps(value)
        self.client.set(key, json_value)
        if ttl:
            self.client.expire(key, ttl)

    def get_json(self, key):
        # Retrieve and deserialize the JSON object from Redis
        json_value = self.client.get(key)
        return json.loads(json_value) if json_value else None

    def set_json_list(self, key, values):
        # Serialize the list of JSON objects and set it in Redis
        json_values = json.dumps(values)
        self.client.set(key, json_values)

    def get_json_list(self, key):
        # Retrieve and deserialize the list of JSON objects from Redis
        json_values = self.client.get(key)
        if json_values:
            logger.info("Found cached %s"%key)
        return json.loads(json_values) if json_values else None

    def append_json_list_with_limit(self, key, value, limit, ttl=None, position=0):
        try:
            # Retrieve the current list from Redis
            current_list = self.get_json_list(key)
            if current_list is None:
                current_list = []
            else:
                logger.info("Append to %s"%key)

            # If the key exists and is a list, append the new value at the start
            current_list.insert(position, value)
            logger.debug("Append to the %s: %s"%(key,current_list))

            # Trim the list to ensure the length does not exceed the limit
            if len(current_list) > limit:
                current_list = current_list[:limit]
                logger.info("Trim the list to %s items"%(limit))

            # Set the updated list back to Redis
            self.client.set(key, json.dumps(current_list))

            # Set the TTL if specified
            if ttl:
                self.client.expire(key, ttl)
        except Exception as e:
            logger.warning(f"Error in append_json_list_with_limit: {str(e)}")

    def exists(self, key):
        # Check if the key exists in the Redis database
        return self.client.exists(key) > 0