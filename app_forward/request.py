#!/usr/bin/python3

import requests
import subprocess
from dotenv import load_dotenv
import sys
import os

dotenv_path = os.path.join(os.path.dirname(__file__), '../.env')
load_dotenv(dotenv_path)


def get_env(var_name):
    """
    get value from .env-file if exists

    Args:
        var_name (str): key in .env file
    Returns:
        Any: value from .env file
    """
    try:
        value = os.environ[var_name]
    except Exception as e:
        value = None
    return value


def get_ipv6_address():
    """
    identify IPv6 address of the server where this script is running
    """
    # Use subprocess to execute 'ip' command to get IPv6 address
    result = subprocess.run(['ip', '-6', 'address', 'show', 'scope', 'global'], stdout=subprocess.PIPE)
    output = result.stdout.decode('utf-8')

    # Parse the output to extract the IPv6 address
    for line in output.split('\n'):
        if 'inet6' in line:
            parts = line.split()
            address = parts[1].split('/')[0]
            if not address.startswith('fe80'):  # Skip link-local addresses
                return address

    return None


def identify_ipv6(server_url, ipv6):
    """
    create URL with IPv6 and send request to external server

    Args:
        server_url (str): server url
        ipv6 (str): IPv6 address
    """
    url = f"{server_url}?identify_ipv6={ipv6}&identify_birdhouse=" + str(get_env("BIRDHOUSE_ID"))
    url += "&http=" + get_env("BIRDHOUSE_HTTP_PORT")
    url += "&api=" + get_env("BIRDHOUSE_API_PORT")
    print(url)
    response = requests.get(url)
    return response.text


if len(sys.argv) > 1:
    print("Send request to '"+sys.argv[1]+"' ...")
    param_server_url = sys.argv[1]
else:
    print("Send request to '"+str(get_env("BIRDHOUSE_APP_FORWARD"))+"' ...")
    param_server_url = str(get_env("BIRDHOUSE_APP_FORWARD"))

param_server_ipv6 = get_ipv6_address()
response_text = identify_ipv6(param_server_url, param_server_ipv6)
print(response_text)
