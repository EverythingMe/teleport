


example config:

```yaml
providers:
  -
    type: hidemyass
    name: hidemyass
    priority: 50
    debug: false
  
    params:
      concurrency: 5
      bucket_name: dosa
      auth-user-pass: /config/creds/hidemyass.passwd
      ca: /config/creds/hidemyass.ca
      cert: /config/creds/hidemyass.cert
      key: /config/creds/hidemyass.pem
  
    countries: !include hma_hosts.yaml
  -
    type: vpn
    name: ipvanish
    priority: 10
    debug: false
  
    params:
      auth-user-pass: /config/creds/ipvanish.passwd
      ca: /config/creds/ipvanish.ca
      auth: SHA256
      cipher: AES-256-CBC
      comp-lzo: ''
      keysize: 256
      tls-cipher: DHE-RSA-AES256-SHA:DHE-DSS-AES256-SHA:AES256-SHA
      tls-remote: true
    
    countries: !include ipv_hosts.yaml
  
  -
    type: luminati
    name: luminati
    priority: 100
    debug: false

    username: LUMINATI_USERNAME
    password: LUMINATI_PASSWORD
```
