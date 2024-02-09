#!/usr/bin/python3

import socket
import requests
import subprocess
import ipaddress


def get_ipv6_address():
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
    url = f"{server_url}/index.php?identify_ipv6={ipv6}"
    print(url)
    response = requests.get(url)
    return response.text


# Example usage
server_url = "http://ckloth.de/birdhouse"  # Replace <server> with your server's URL
server_ipv6 = get_ipv6_address()

response_text = identify_ipv6(server_url, server_ipv6)
print(response_text)
