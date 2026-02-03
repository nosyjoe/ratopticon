# Ratpi ansible configuration for automatic setup

## Basic config

User: ratpi

password is set, but not required

## Find your Pis on the network

`arp-scan` seems to work well:

```bash
sudo arp-scan --interface <your interface> --localnet --numeric --ignoredups
```

## Install pipenv

```
pipenv install
```
## Edit hostfile 



