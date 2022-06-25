from argparse import ArgumentParser
from datetime import (
    datetime,
    timedelta,
    timezone,
)
from time import time

import aiohttp
from aiohttp import web
from aiohttp.web_request import Request

routes = web.RouteTableDef()
local_timezone = timezone(timedelta(hours=3))


def try_get(data, path):
    if not path:
        return data
    (key, default), *path = path
    if isinstance(data, list):
        try:
            value = data[key]
        except IndexError:
            value = default
    elif isinstance(data, dict):
        value = data.get(key, default)
    else:
        return None
    return try_get(value, path)


def dict_to_xml(data, root='data'):
    xml = f'<{root}>'
    if isinstance(data, dict):
        for key, value in data.items():
            xml += dict_to_xml(value, key)
    elif isinstance(data, (list, tuple, set)):
        for item in data:
            xml += dict_to_xml(item, 'item')
    else:
        xml += str(data)
    xml += f'</{root}>'
    return xml


@routes.get('/api/data/moex/{code}')
async def get_moex(request: Request) -> web.Response:
    params = {
        'interval': request.query.get('interval', '24'),
        'from': request.query.get('from', '2019-01-01'),
    }
    code = request.match_info['code'].upper()
    url = 'https://iss.moex.com/iss/engines/stock/markets/' \
          f'shares/securities/{code}/candles.json'
    async with aiohttp.ClientSession() as session:
        async with session.get(url, params=params) as response:
            data = await response.json()
    timestamps = []
    values = []
    for (
            open_, close, high, low, value, volume, begin, end
    ) in data['candles']['data']:
        timestamps.append(begin[:10])
        values.append(close)

    return web.json_response(
        data={
            'timestamps': timestamps,
            'values': values,
        },
    )


@routes.get('/api/data/yahoo/{code}')
async def get_yahoo(request: Request) -> web.Response:
    from_date = request.query.get('from', '2020-01-01')
    params = {
        'interval': request.query.get('interval', '1d'),
        'period1': int(datetime.fromisoformat(from_date).timestamp()),
        'period2': int(time()),
    }
    code = request.match_info['code'].upper()
    url = f'https://query1.finance.yahoo.com/v7/finance/chart/{code}'
    async with aiohttp.ClientSession() as session:
        async with session.get(url, params=params) as response:
            data = await response.json()
            if response.status != 200:
                return web.json_response({
                    'status': 'error',
                    'message': f'Yahoo returned status {response.status}',
                    'content': data,
                })

    try:
        result = data['chart']['result'][0]
    except (KeyError, IndexError) as error:
        raise ValueError(
            f'Unexpected content (error {error!r}): {data}',
        )

    return web.json_response(
        data={
            'timestamps': [
                datetime.fromtimestamp(t).date().isoformat()
                for t in result['timestamp']
            ],
            'values': result['indicators']['quote'][0]['close'],
        },
    )


@routes.get('/api/current_price/yahoo/{code}')
async def get_current_price(request: Request) -> web.Response:
    from_date = request.query.get(
        'from', (datetime.now() - timedelta(days=7)).date().isoformat(),
    )
    params = {
        'interval': request.query.get('interval', '1d'),
        'period1': int(datetime.fromisoformat(from_date).timestamp()),
        'period2': int(time()),
    }
    code = request.match_info['code'].upper()
    url = f'https://query1.finance.yahoo.com/v7/finance/chart/{code}'
    async with aiohttp.ClientSession() as session:
        async with session.get(url, params=params) as response:
            data = await response.json()
    last_price = try_get(data, (
        ('chart', {}),
        ('result', []),
        (0, {}),
        ('indicators', {}),
        ('quote', []),
        (0, {}),
        ('close', []),
        (-1, None)
    ))
    xml_body = dict_to_xml({
        'price': last_price,
        'params': params,
        'raw': data,
    })
    return web.Response(
        body=f'<?xml version="1.0" encoding="UTF-8"?>{xml_body}',
        headers={
            'content-type': 'application/xml; charset=utf-8',
        },
    )


@routes.get('/api/current_price/moex/{code}')
async def get_moex(request: Request) -> web.Response:
    code = request.match_info['code'].upper()
    url = 'https://iss.moex.com/iss/engines/stock/markets' \
          f'/shares/securities/{code}/candles.json'
    date_url = 'https://iss.moex.com/iss' \
               '/history/engines/stock/markets/shares/dates.json'
    params = {
        'interval': '1',
    }
    now = datetime.now(local_timezone)
    today_str = now.strftime('%Y-%m-%d')
    async with aiohttp.ClientSession() as session:
        async with session.get(date_url) as response:
            raw_dates = await response.json()
        last_date = raw_dates['dates']['data'][0][1]
        if last_date != today_str:
            params['from'] = f'{last_date} 23:15:00'
        else:
            ten_min_ago = datetime.now(local_timezone) - timedelta(minutes=15)
            params['from'] = ten_min_ago.isoformat()
        async with session.get(url, params=params) as response:
            data = await response.json()

    resp_data = data['candles']['data']
    last_time = resp_data[-1] if resp_data else []
    last_price = last_time[1] if len(last_time) > 1 else None
    xml_body = dict_to_xml({
        'price': last_price,
        'params': params,
        'raw': data,
    })
    return web.Response(
        body=f'<?xml version="1.0" encoding="UTF-8"?>{xml_body}',
        headers={
            'content-type': 'application/xml; charset=utf-8',
        },
    )


if __name__ == '__main__':
    def main():
        parser = ArgumentParser()
        parser.add_argument('-p', '--port', type=int, default=8080)
        args = parser.parse_args()
        app = web.Application()
        app.add_routes(routes)
        web.run_app(app, port=args.port)


    main()
