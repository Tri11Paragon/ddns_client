import argparse
import json
import requests
import time
import sched
from pathlib import Path


class Env:
    def __init__(self, username, api_key):
        self.username = username
        self.api_key = api_key


class Zone:
    def __init__(self, zone_name, env, records):
        self.zone_name = zone_name
        self.env = env
        self.records = records
        self.zone_id = None


class Zones:
    def __init__(self, ip_provider, r_zones):
        self.ip_provider = ip_provider
        self.zones = r_zones


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
            for site in zone["sites"]:
                sites.append(site)
            zones.append(Zone(zone["zone"], envs[zone["username"]], sites))
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


def fetch_ip(provider):
    print(f"Fetching IP Address with '{provider}'")
    r = requests.get(provider)
    return r.text


def fetch_zone_id(zone_name, key):
    headers = "Authorization: Bearer"
    return "hello"


def run(scheduler, r_args, r_envs, r_zones):
    scheduler.enter(r_args.time, 1, run, (scheduler, r_args, r_envs, r_zones))
    address = fetch_ip(r_zones.ip_provider)

    for zone in r_zones.zones:
        user = zone.env
        if zone.zone_id is None:
            zone.zone_id = fetch_zone_id(zone.zone_name)


if __name__ == '__main__':
    args = parse_arguments()

    if args.install:
        run_install()
    else:
        user_envs = get_env(args.env)
        zones = get_conf(args.config, user_envs)
        runner = sched.scheduler(time.time, time.sleep)
        runner.enter(args.time, 1, run, (runner, args, user_envs, zones))
        runner.run()
