import redis

redis_instance = redis.StrictRedis(host='127.0.0.1', port=6379, db=0,
                                   password="")

redis_instance.set('key', 'qwerty')
print(redis_instance.get('key'))
redis_instance.delete('key')
print(redis_instance.get('key'))

