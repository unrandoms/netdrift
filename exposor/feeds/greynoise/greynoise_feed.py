import requests
import logging
from datetime import datetime


class GreyNoise:
    def auth(api_key):
        try:
            headers = {
                "key": api_key,
                "Accept": "application/json"
            }
            response = requests.get(
                "https://api.greynoise.io/ping",
                headers=headers,
                timeout=10
            )
            if response.status_code == 200:
                logging.info("Authentication successful for greynoise")
                return True
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

        headers = {
            "key": api_key,
            "Accept": "application/json"
        }

        try:
            for q in queries:
                if net:
                    q = f"{q} ip:{net}"
                if country_code:
                    q = f"{q} metadata.country_code:{country_code}"
                if domain_name:
                    q = f"{q} metadata.rdns:*{domain_name}*"
                if asn:
                    q = f"{q} metadata.asn:AS{asn}"

                params = {
                    "query": q,
                    "size": min(int(limit_result), 100)
                }

                response = requests.get(
                    "https://api.greynoise.io/v2/experimental/gnql",
                    headers=headers,
                    params=params,
                    timeout=15
                )

                if response.status_code != 200:
                    logging.debug(
                        f"GreyNoise - request failed with status {response.status_code} for query: {q}"
                    )
                    if query_limit.lower() == "yes":
                        break
                    continue

                js = response.json()
                data = js.get("data", [])
                total = js.get("count", 0)
                logging.debug(f"GreyNoise - total result: {total} for query: {q}")

                for item in data[:int(limit_result)]:
                    metadata = item.get("metadata", {})
                    banner_dic = {
                        "ip": item.get("ip"),
                        "domain": metadata.get("rdns"),
                        "port": None,
                        "country": metadata.get("country_code"),
                        "technology": technology,
                        "feed": "greynoise",
                        "timestamp": item.get("last_seen", datetime.now().isoformat())
                    }
                    results.append(banner_dic)

                if query_limit.lower() == "yes":
                    break

        except Exception as e:
            logging.error(f"ERROR greynoise search {e}")

        return results

    def enrich_ip(api_key, ip):
        """Enrich a single IP via GreyNoise Community API.

        Returns classification string: 'benign', 'malicious', or 'unknown'.
        """
        try:
            headers = {
                "key": api_key,
                "Accept": "application/json"
            }
            response = requests.get(
                f"https://api.greynoise.io/v3/community/{ip}",
                headers=headers,
                timeout=10
            )
            if response.status_code == 200:
                js = response.json()
                return js.get("classification", "unknown")
            elif response.status_code == 404:
                return "unknown"
            else:
                logging.debug(f"GreyNoise enrich {ip}: status {response.status_code}")
                return "unknown"
        except Exception as e:
            logging.error(f"GreyNoise enrich_ip {ip}: {e}")
            return "unknown"

    def enrich_results(api_key, results):
        """Post-pass: annotate each result dict with greynoise_classification.

        Deduplicates IP lookups so each IP is queried at most once.
        """
        seen_ips = {}
        for item in results:
            ip = item.get("ip")
            if not ip:
                item["greynoise_classification"] = "unknown"
                continue
            if ip not in seen_ips:
                seen_ips[ip] = GreyNoise.enrich_ip(api_key, ip)
                logging.debug(
                    f"GreyNoise enrichment: {ip} => {seen_ips[ip]}"
                )
            item["greynoise_classification"] = seen_ips[ip]
        return results
