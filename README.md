# ratopticon
Records rat videos

Setup Debian machine

```shell
mkdir flask-app
cd flask-app
git clone https://github.com/nosyjoe/ratopticon.git

pythopython3 -m venv venv
source venv/bin/activate

python3 -m pip install --upgrade pip

python3 -m pip install flask gunicorn psutils
```

Run with 

```
# working folder flask-app
python -m flask --app ratopticon run --port 8000 -h 0.0.0.0 --debug

```

# Useful commands

## Set ip-address

```
sudo nmcli con mod 'Wired connection 1' ipv4.addresses 192.168.0.254/24 ipv4.method manual
sudo nmcli con up 'Wired connection 1'

# gateway not needed atm
sudo nmcli con mod eth0 ipv4.gateway 192.168.0.1
```

# Enter dev mode in Pi

```
sudo systemctl stop ratopticon
cd ratopticon/
source venv/bin/activate
python -m flask --app ratopticon run --port 8000 -h 0.0.0.0 --debug
```

