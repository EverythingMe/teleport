# teleport

## what?

teleport is a python library that provides a context manager to execute code with in the context of a specific country, it is intented to run inside a docker container as it takes over the entire network "namespace".

## why?

a typical use case for teleport would be when a service returns different results based on geographic location, for example when doing an app search in google's playstore it will show search results only if app is available to the country google things you're searching from.

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

## usage:

please checkout the example.py file in the examples directory, it also includes a sample configuration file and the basic config directory structure
