TICKER="${1}"
curl -s "https://query1.finance.yahoo.com/v7/finance/chart/${TICKER}?period1=$(expr $(date +%s) - 7 \* 24 \* 3600)&period2=$(date +%s)" | jq '[.chart.result[0].indicators.quote[0].close,.chart.result[0].timestamp] | transpose | .[-1] | {close:.[0], time:.[1]|todateiso8601}'
curl -s "https://query1.finance.yahoo.com/v7/finance/chart/${TICKER}?period1=$(expr $(date +%s) - 7 \* 24 \* 3600)&period2=$(date +%s)" | jq '[.chart.result[0].indicators.quote[0].close,.chart.result[0].timestamp] | transpose | .[-1][0]'
