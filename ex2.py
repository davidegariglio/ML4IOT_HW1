import redis
import uuid
import psutil
from datetime import datetime
from time import sleep
from time import time
import argparse as ap

# Connect to Redis
parser = ap.ArgumentParser()
parser.add_argument('--host',type=str)
parser.add_argument('--port',type=int)
parser.add_argument('--user',type=str)
parser.add_argument('--password',type=str)

args = parser.parse_args()

redis_client = redis.Redis(host=args.host, port=args.port, username=args.user, password=args.password)
is_connected = redis_client.ping()
#redis_client.flushdb()
print('Redis Connected:', is_connected)

mac_address = hex(uuid.getnode())
one_day_in_ms = 24 * 60 * 60 * 1000


# Create the time-series 
# By default, compression is enabled
try:
    redis_client.ts().create(f'{mac_address}:battery', chunk_size=128)
except redis.ResponseError:
    pass


try:
    redis_client.ts().create(f'{mac_address}:power', chunk_size=128)
except redis.ResponseError:
    pass


try:
    redis_client.ts().create(f'{mac_address}:plugged_seconds', chunk_size=128)
    # define the aggregation rule
    redis_client.ts().createrule(f'{mac_address}:power', f'{mac_address}:plugged_seconds', 'sum', bucket_size_msec = one_day_in_ms)
except redis.ResponseError:
    pass
 

# Set the retention time

# second to milliseconds
rt_battery = 3276800*1000
rt_power = 3276800*1000

#days to milliseconds
rt_plugged = 655360*24*60*60*1000

redis_client.ts().alter(f'{mac_address}:battery', retention_msecs=rt_battery)
redis_client.ts().alter(f'{mac_address}:power', retention_msecs=rt_power)
redis_client.ts().alter(f'{mac_address}:plugged_seconds', retention_msecs=rt_plugged)

# Data acquisition and storage
while True:
    
    redis_client.ts().add(f'{mac_address}:battery', int(time()*1000), psutil.sensors_battery().percent)

    redis_client.ts().add(f'{mac_address}:power', int(time()*1000), int(psutil.sensors_battery().power_plugged))
    
    # print commented in order to avoid useless data sending in the network
    # print('\n\n battery level:')
    # data, val = redis_client.ts().get(f'{mac_address}:battery')
    # print(datetime.fromtimestamp(data/1000).strftime('%Y-%m-%d %H:%M:%S.%f'), val)

    # print('power: ')
    # data, val = redis_client.ts().get(f'{mac_address}:power')
    # print(datetime.fromtimestamp(data/1000).strftime('%Y-%m-%d %H:%M:%S.%f'), val)

    # print('plugged: ')
    # try:
    #     data, val = redis_client.ts().get(f'{mac_address}:plugged_seconds')
    #     print(datetime.fromtimestamp(data/1000).strftime('%Y-%m-%d %H:%M:%S.%f'), val)
    # except: 
    #     print('not enough data to compute aggregation')
    
    sleep(1)
