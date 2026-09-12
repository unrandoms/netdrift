import requests
import logging
from datetime import datetime


class HunterHow:
    def auth(api_key):
        try:
            params = {
                "query": "ip:1.1.1.1",
                "auth_key": api_key,
                "page": 1,
                "page_size": 1,
                "start_time": "2024-01-01",
                "end_time": "2024-12-31"
            }
            response = requests.get(
                "https://hunter.how/open-api",
                params=params,
                timeout=10
            )
            if response.status_code == 200:
                js = response.json()
                if js.get("code") == 200:
                    logging.info("Authentication successful for hunterhow")
                    return True
                else:
                    logging.error(f"HunterHow auth error: {js.get('message')}")
                    return False
            else:
                return False
        except Exception as e:
            logging.error(str(e))
            return False

    def search(api_key, queries, args, technology):
        results = []
        limit_result = args.limit
        query_limit = args.query_limit
        country_code = args.country
        net = args.netblock
        domain_name = args.domain_name
        asn = getattr(args, "asn", None)

        try:
            for q in queries:
                if net:
                    q = f"{q} ip=\"{net}\""
                if country_code:
                    q = f"{q} country=\"{country_code}\""
                if domain_name:
                    q = f"{q} domain=\"{domain_name}\""
                if asn:
                    q = f"{q} asn={asn}"

                page = 1
                counter = 0

                while counter < int(limit_result):
                    page_size = min(100, int(limit_result) - counter)
                    params = {
                        "query": q,
                        "auth_key": api_key,
                        "page": page,
                        "page_size": page_size,
                        "start_time": "2024-01-01",
                        "end_time": "2025-12-31"
                    }
                    response = requests.get(
                        "https://hunter.how/open-api",
                        params=params,
                        timeout=10
                    )

                    if response.status_code != 200:
                        logging.debug(
                            f"HunterHow - request failed with status {response.status_code} for query: {q}"
                        )
                        break

                    js = response.json()
                    if js.get("code") != 200:
                        logging.debug(f"HunterHow - API error: {js.get('message')} for query: {q}")
                        break

                    data = js.get("data", {})
                    arr = data.get("arr", [])
                    total = data.get("total", 0)
                    logging.debug(f"HunterHow - total result: {total} for query: {q}")

                    if not arr:
                        break

                    remaining = int(limit_result) - counter
                    matches_to_add = arr[:remaining]

                    for item in matches_to_add:
                        counter += 1
                        if counter > int(limit_result):
                            break
                        banner_dic = {
                            "ip": item.get("ip"),
                            "domain": item.get("domain"),
                            "port": item.get("port"),
                            "country": item.get("country"),
                            "technology": technology,
                            "feed": "hunterhow",
                            "timestamp": item.get("updated_at", datetime.now().isoformat())
                        }
                        results.append(banner_dic)

                    page += 1

                if query_limit.lower() == "yes":
                    break

        except Exception as e:
            logging.error(f"ERROR hunterhow search {e}")

        return results
