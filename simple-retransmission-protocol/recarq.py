#############################################################
# RecArq.py - recebe um arquivo por um canal ponto-a-ponto confiável
# Parâmetro 1: string com nome do arquivo a ser enviado
# Parâmetro 2: porto a ser usado 
#############################################################

import pppsrt 
import os,sys

if len(sys.argv) != 3:
    print('Argumentos: ', sys.argv[0],' arquivo porto')
    exit()

nome_arquivo = sys.argv[1]
port    = sys.argv[2]


pppsrt = pppsrt.PPPSRT( port )

arquivo = open(nome_arquivo,'wb')

while True:
    bloco = pppsrt.recv()  # esse tamanho poderia mudar a cada chamada
    print(bloco)
    if not bloco: break
    arquivo.write(bloco)

pppsrt.close()
arquivo.close()


