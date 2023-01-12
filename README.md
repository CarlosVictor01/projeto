# projeto

pip install openssl
openssl ecparam -name prime256v1 -genkey -out private_key.pem
openssl ec -in private_key.pem -pubout -out public_key.pem
openssl req -new -x509 -key private_key.pem -out certificado.pem -days 1825 -subj '/C=BR/ST=Brasilia/L=Brasilia/O=IFB/CN=TCC'

pip install pillow
pip install ecdsa
pip install qrcode
pip install mrz
pip install hashlib
pip install psycopg2
pip install psycopg2-binary
