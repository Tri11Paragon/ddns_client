import argparse
import json
import requests
import time
import sched
from pathlib import Path


def make_headers(key: str):
    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json"
    }
    return headers


class Env:
    def __init__(self, username, api_key):
        self.username = username
        self.api_key = api_key


class Zone:
    def __init__(self, env, records):
        self.env = env
        self.records = records
        self.zone_id = None
        self.zone_name = None

    def fetch_zone_id(self):
        if self.zone_name is None:
            print("Zone name is none! Must set at least zone name or zone id!")
            exit(1)

        r = requests.get(f"https://api.cloudflare.com/client/v4/zones", headers=make_headers(self.env.api_key))
        if r.status_code == 200:
            data = json.loads(r.text)
            results = data["result"]
            for result in results:
                if result["name"] == self.zone_name:
                    self.zone_id = result["id"]
                    return
            print("Failed to find zone id, does this zone exist?")
            return
        print(f"Error has occurred, status code: {r.status_code}")
        print(r.text)

    def update_record(self, address, record):
        print(f"record {record['name']} has address {record['content']} but requires updating!")
        r = requests.patch(f"https://api.cloudflare.com/client/v4/zones/{self.zone_id}/dns_records/{record['id']}",
                           headers=make_headers(self.env.api_key), data=json.dumps({
                                "content": address,
                                "name": record['name'],
                                "type": record['type'],
                                "comment": record['comment'],
                                "ttl": record['ttl'],
                                "tags": record['tags'],
                                "proxied": record['proxied']
                            }))
        if r.status_code:
            print(f"record {record['name']} has been updated to {address}")
        else:
            print(f"Failed to update record {record['name']}")
            print(r.text)

    def update_records(self, address):
        r = requests.get(f"https://api.cloudflare.com/client/v4/zones/{self.zone_id}/dns_records?type=A",
                         headers=make_headers(self.env.api_key))
        if r.status_code != 200:
            return None
        record_data = json.loads(r.text)["result"]
        for record in record_data:
            if record["name"] not in self.records:
                continue
            if record["content"] == address:
                continue
            self.update_record(address, record)


class Zones:
    def __init__(self, ip_provider, zones):
        self.ip_provider = ip_provider
        self.zones = zones

    def fetch_ip(self):
        r = requests.get(self.ip_provider)
        print(f"Fetching IP Address with '{self.ip_provider}' returned '{r.text}'")
        return r.text


def parse_arguments():
    parser = argparse.ArgumentParser(description="Silly little DDNS client", prog="Brett's DDNS Client")
    parser.add_argument("--env", "-e", default="/etc/bddns/users.conf", required=False)
    parser.add_argument("--config", "-c", default="/etc/bddns/sites.conf", required=False)
    parser.add_argument("--time", "-u", default=300, required=False, help="Time between updates in seconds")
    parser.add_argument("--install", action="store_true", default=False, required=False,
                        help="Runs installer, will create config files")

    return parser.parse_args()


def get_env(env_path):
    with open(env_path, "r") as f:
        json_env = json.load(f)
        envs = {}
        for user in json_env["users"]:
            envs[user['username']] = Env(user['username'], user['api_key'])
        return envs


def get_conf(conf_path, envs):
    with open(conf_path, "r") as f:
        json_env = json.load(f)
        zones = []
        for zone in json_env["zones"]:
            sites = []
            for site in zone["records"]:
                sites.append(site)
            zn = Zone(envs[zone["username"]], sites)
            if "zone" in zone:
                zn.zone_name = zone["zone"]
            if "id" in zone:
                zn.zone_id = zone["id"]
            zones.append(zn)
        return Zones(json_env["ip_provider"], zones)


def run_install():
    config_folder = Path("/etc/bddns/")
    users_path = Path(config_folder / "users.conf")
    sites_path = Path(config_folder / "sites.conf")
    print(f"Installing to {config_folder}")
    print(f"\tUsers path: {users_path}")
    print(f"\tSites path: {sites_path}")
    if not config_folder.is_dir():
        config_folder.mkdir()
    if not users_path.exists():
        users_path.touch()
        with open(users_path, "w") as f:
            json.dump({"users": [
                {"username": "user@email.com", "api_key": "<KEY>"},
                {"username": "another-user@email.com", "api_key": "<KEY>"},
            ]}, f, indent=4)
    else:
        print(f"Warning {users_path} already exists, skipping!")
    if not sites_path.exists():
        sites_path.touch()
        with open(sites_path, "w") as f:
            json.dump({
                "ip_provider": "https://api.ipify.org/",
                "zones": [
                    {
                        "zone": "<zone_name.tld>",
                        "username": "user@email.com",
                        "sites": [
                            "site.tld",
                            "subdomain.site.tld"
                        ]
                    }
                ]
            }, f, indent=4)
    else:
        print(f"Warning {sites_path} already exists, skipping!")


def run(scheduler, args, zones):
    scheduler.enter(args.time, 1, run, (scheduler, args, zones))
    address = zones.fetch_ip()

    for zone in zones.zones:
        if zone.zone_id is None:
            zone.fetch_zone_id()
            print(f"Fetched zone {zone.zone_name} with id {zone.zone_id}")
        zone.update_records(address)


def main():
    args = parse_arguments()

    if args.install:
        run_install()
    else:
        user_envs = get_env(args.env)
        zones = get_conf(args.config, user_envs)
        runner = sched.scheduler(time.time, time.sleep)
        run(runner, args, zones)
        runner.run()


if __name__ == '__main__':
    main()
