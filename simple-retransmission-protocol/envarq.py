#############################################################
# EnvArq.py - envia um arquivo por um canal ponto-a-ponto confiável
# Parâmetro 1: string com nome do arquivo a ser enviado
# Parâmetro 2: nome/endereço IP do host destino
# Parâmetro 3: porto no host de destino
#############################################################

import pppsrt  
import os,sys

if len(sys.argv) != 4:
    print('Argumentos: ', sys.argv[0],' arquivo host porto')
    exit()

nome_arquivo = sys.argv[1]
host    = sys.argv[2]
port    = sys.argv[3]

pppsrt = pppsrt.PPPSRT( port, host )

arquivo = open(nome_arquivo,'rb')

while True:
    bloco = arquivo.read(1000)  # esse tamanho poderia mudar a cada chamada
    print(bloco)
    if not bloco: break
    pppsrt.send(bloco)

pppsrt.close()
arquivo.close()


