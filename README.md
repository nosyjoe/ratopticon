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
python3 -m flask --app ratopticon run --port 8000 --debug

```


