# XHunt KOL Fetcher

Fetch XHunt KOL data for a local list of Twitter/X usernames.

The script reads `twitter_user_name` from a CSV/TSV/JSON/JSONL file, requests:

- KOL ability model
- Soul index

It writes a final JSON array, a JSONL checkpoint file for resume, a cache directory, and a log file with rate-limit warnings.

## Usage

Test a small batch first:

```bash
python3 fetch_xhunt_kol_data.py \
  --input data/kol_list.csv \
  --field twitter_user_name \
  --output outputs/xhunt_kol_data.json \
  --jsonl outputs/xhunt_kol_data.jsonl \
  --log outputs/xhunt_kol_fetch.log \
  --cache-dir .cache/xhunt_kol \
  --limit 50
```

Run the full list:

```bash
python3 fetch_xhunt_kol_data.py \
  --input data/kol_list.csv \
  --field twitter_user_name \
  --output outputs/xhunt_kol_data.json \
  --jsonl outputs/xhunt_kol_data.jsonl \
  --log outputs/xhunt_kol_fetch.log \
  --cache-dir .cache/xhunt_kol
```

Resume with the same command. Finished rows are skipped from the JSONL checkpoint.

## Output Shape

```json
{
  "kolId": "wolfyxbt",
  "handle": "wolfyxbt",
  "kolName": "杀破狼 WolfyXBT",
  "x链接": "https://x.com/wolfyxbt",
  "能力模型json": {},
  "灵魂指数json": {},
  "fetchStatus": {
    "ability": "ok",
    "soul": "ok"
  }
}
```

The final output file is a JSON array of objects with this shape.

## Status Values

- `ok` - Data was fetched and parsed.
- `missing` - XHunt returned a valid response, but this KOL does not have that section.
- `failed:rate_limit` - XHunt rate-limited the request after retries.
- `failed:http_429` or similar - HTTP or network failure after retries.

## Rate Limit Notes

The defaults are intentionally slow: one KOL every 20-30 seconds, with a 5-10 second pause between ability and soul requests. For large lists, keep the defaults unless you have confirmed the service tolerates a faster pace.
