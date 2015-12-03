# teleport

## what?

teleport is a python library that provides a context manager to execute code with in the context of a specific country, it is intented to run inside a docker container as it takes over the entire network "namespace".

## why?

a typical use case for teleport would be when you have users from all over the world and you're serving some 3rd party content that's uses client's ip to resolve its geo location so with teleport + docker you could run all sorts of tests that need to run in a country specific context.

## how?

it's basically an absration above vpns and proxies, these are called 'providers' and a basic provider has a name, type, what countries it can 'teleport' to and its proiority. so when asked to teleport to a country, the context manager:

1. goes over the list of providers that can teleport there, and by the order of priority tries teleporting. 
2. after teleportation established it verifies that networking is indeed ip->geo resolves to the specified location
3. then it make sure no networking could 'leak' outside the vpn/proxy by setting iptables rules
4. when context manager exists, it undoes the vpn and firewall.

## plugins

### ipvanish

support for https://www.ipvanish.com vpn service provider (tools folder includes a script to generate ipvanish configuration map of country code to vpn ips)

### hidemyass

support for https://www.hidemyass.com vpn service provider, it also includes a distributed concurrency limiter on top of https://consul.io/ (tools folder includes a script to generate hidemyass configuration map of country code to vpn ips)

### luminati

support for https://luminati.io/ p2p proxy service provider

## usage

```python
    with Teleporter(config, country, dns_servers=dns_servers) as t:
        proxy = ''
        proxy_auth = ''

        if t.is_proxy:
            proxy = t.get_proxy_address()
            proxy_auth = t.get_proxy_auth(country)

        do_stuff(proxy, proxy_auth)
```

```config``` is a python dict that specifies providers (please see config/config.yaml example in the examples folder) and the t.is_proxy is to determine if the teleportation was done with a proxy, and if so, you'll want to pass the proxy and proxy_auth variables to whatever is making the http requests, (i.e requests/curl)

```dns_servers``` is a list of dns servers, it is needed to we can exclude them from the firewall rules, so we can make dns requests, you could use that if you want to exclude other ips too.

please checkout the example.py file in the examples directory for a more detailed example, it also includes a sample configuration file and the basic config directory structure
