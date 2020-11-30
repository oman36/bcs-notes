from argparse import ArgumentParser
from datetime import datetime
from time import time

import aiohttp
from aiohttp import web
from aiohttp.web_request import Request

routes = web.RouteTableDef()


@routes.get('/api/data/moex/{code}')
async def get_moex(request: Request) -> web.Response:
    params = {
        'interval': '24',
        'from': request.query.get('from', '2019-01-01'),
    }
    code = request.match_info['code'].upper()
    url = f'https://iss.moex.com/iss/engines/stock/markets/shares/securities/{code}/candles.json'
    async with aiohttp.ClientSession() as session:
        async with session.get(url, params=params) as response:
            data = await response.json()
    timestamps = []
    values = []
    for open_, close, high, low, value, volume, begin, end in data['candles']['data']:
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
        'interval': '1d',
        'period1': int(datetime.fromisoformat(from_date).timestamp()),
        'period2': int(time()),
    }
    code = request.match_info['code'].upper()
    url = f'https://query1.finance.yahoo.com/v7/finance/chart/{code}'
    async with aiohttp.ClientSession() as session:
        async with session.get(url, params=params) as response:
            data = await response.json()

    result = data['chart']['result'][0]
    return web.json_response(
        data={
            'timestamps': [
                datetime.fromtimestamp(t).date().isoformat()
                for t in result['timestamp']
            ],
            'values': result['indicators']['quote'][0]['close'],
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
