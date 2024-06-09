import requests
import argparse
import json
from pathlib import Path


class Env:
    def __init__(self, username, api_key):
        self.username = username
        self.api_key = api_key


class Zone:
    def __init__(self, zone_id, env, records):
        self.zone_id = zone_id
        self.env = env
        self.records = records


def parse_arguments():
    parser = argparse.ArgumentParser(description="Silly little DDNS client", prog="Brett's DDNS Client")
    parser.add_argument("--env", "-e", default="/etc/bddns.env", required=False)
    parser.add_argument("--config", "-c", default="/etc/bddns.conf", required=False)

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
            zones.append(Zone(zone["zone_id"], envs[zone["username"]], sites))
        return zones


if __name__ == '__main__':
    args = parse_arguments()
    user_envs = get_env(args.env)


