from pyvivado import redis_connection, redis_utils

Connection = redis_connection.Connection

get_projdir_hwcode = redis_utils.get_projdir_hwcode
get_free_hwcode = redis_utils.get_free_hwcode

get_hardware_usage = redis_utils.get_hardware_usage
