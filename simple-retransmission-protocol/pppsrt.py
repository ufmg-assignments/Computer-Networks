#################################################################
# pppsrt.py - protocolo ponto-a-ponto simples com retransmissão
#           - entrega interface semelhante a um socket
#################################################################
# fornece a classe PPPSRT, que tem os métodos:
#
# contrutor: pode receber um ou dois parâmetros, para criar um
#            canal que implementa o protocolo PPPSRT;
#            - o servidor cria o objeto apenas com o porto;
#            - o cliente cria o objeto com host e porto.
# close: encerra o enlace
# send(m): envia o array de bytes m pelo canal, calculando o 
#           checksum, fazendo o enquadramento e controlando a
#           retransmissão, se necessário.
# recv(): recebe um quadro e retorna-o como um array de bytes,
#         conferindo o enquadramento, conferindo o checksum e
#         enviando uma mensagem de confirmação, se for o caso.
# OBS: o tamanho da mensagem enviada/recebida pode variar, 
#      mas não deve ser maior que 1500 bytes.
################################################################
# PPPSRT utiliza o módulo dcc023_tp1 como API para envio e recepção
#        pelo enlace; o qual não deve ser alterado.
# PPPSRT não pode utilizar a interface de sockets diretamente.
################################################################

import dcc023_tp1

#Constantes
FLAG = b'\x7e'
ADDRESS = b'\xff'
DATA_CONTROL = b'\x03'
CONFIRMATION_CONTROL = b'\x07'
ESCAPE = b'\x7d'
ESCAPED_FLAG = b'\x5e'
ESCAPED_ESCAPE = b'\x5d'

class PPPSRT:
  
    def __init__(self, port, host='' ):
        self.link = dcc023_tp1.Link(port,host)
        self.sended_protocols = 1
        self.last_received_protocol = 0

    def close(self):
        self.link.close()
        
####################################################################
# A princípio, só é preciso alterar as duas funções a seguir.
  
    def get_checksum(self, message):
        checksum = 0
        for i in range(0, len(message)//2 + 1, 2):
            checksum += int.from_bytes(message[i:i+2], "big")
            checksum = checksum % 65536

        if len(message)%2 == 1:
            checksum += message[-1]
            checksum = checksum % 65536

        checksum = checksum.to_bytes(2, "big")

        return checksum

    def send(self,message):
        # Aqui, PPSRT deve fazer:
        #   - fazer o encapsulamento de cada mensagem em um quadro PPP,

        #   - calcular o Checksum do quadro e incluído,
        payload_and_checksum = message + self.get_checksum(message)

        #   - fazer o byte stuffing durante o envio da mensagem,
        byte_stuffing = b''   
        
        esc = int.from_bytes(ESCAPE, "big")
        flg = int.from_bytes(FLAG, "big")

        for byte in payload_and_checksum:
            if byte == esc:         
                byte_stuffing += ESCAPE + ESCAPED_ESCAPE   
            elif byte == flg:     
                byte_stuffing += ESCAPE + ESCAPED_FLAG
            else:                  
                byte_stuffing += byte.to_bytes(1, 'big')

        quadro = FLAG + ADDRESS + DATA_CONTROL + self.sended_protocols.to_bytes(2, 'big') + byte_stuffing + FLAG
        print("Enviando quadro: ", self.sended_protocols.to_bytes(2, 'big'))
        self.link.send(quadro)
        
        #   - aguardar pela mensagem de confirmação,
        try:
            ack = self.link.recv(1500)
            print("Recebido ACK", self.sended_protocols.to_bytes(2, 'big'))
            self.sended_protocols += 1

        except TimeoutError: # use para tratar temporizações
            #   - retransmitir a mensagem se a confirmação não chegar.
            print("Retransmitindo...", self.sended_protocols.to_bytes(2, 'big'))
            self.send(message)

    def assemble_the_frame(self, processed_frame, corrupt_frame):
        
        for idx, byte in enumerate(processed_frame):
            if byte == FLAG:
                frame_start = idx
                break
        processed_frame.pop(0)
        
        #  identificar endereço
        if processed_frame[0] != ADDRESS:
            print(processed_frame[0], ADDRESS)
            corrupt_frame = True
        processed_frame.pop(0)

        # identificar controle
        if processed_frame[0] != DATA_CONTROL:
            corrupt_frame = True
        processed_frame.pop(0)
        
        # identificar protocolo
        protocol = processed_frame.pop(0) + processed_frame.pop(0)

        # identificar fim de quadro
        frame_end = -1
        for idx, byte in enumerate(processed_frame):
            if byte == FLAG:
                frame_end = idx
                break
        if frame_end == -1:
            corrupt_frame = True
        
        return protocol, processed_frame[:frame_end], corrupt_frame # O que sobrou em processed frame é o payload e o checksum

    def remove_byte_stuffing(self, processed_frame):

        message = b''

        last_was_scape = False
        for byte in processed_frame:
            if last_was_scape:
                last_was_scape = False
                if byte == ESCAPED_FLAG:
                    message += FLAG
                elif byte == ESCAPED_ESCAPE:
                    message += ESCAPE
            else:
                if byte == ESCAPE:
                    last_was_scape = True
                else:
                    message += byte
               
        return message

    def recv(self):

        try:
            frame = self.link.recv(1500)
            processed_frame = [byte.to_bytes(1, 'big') for byte in frame]       

            corrupt_frame = False
            payload = ''
            if len(frame) == 0:
                corrupt_frame = True
            else: 
                # - identificar começo de um quadro, 
                readed_protocol, processed_frame, corrupt_frame = self.assemble_the_frame(processed_frame, corrupt_frame)
                
                # - retirar byte stuffing
                payload_and_checksum = self.remove_byte_stuffing(processed_frame)

                # Separar payload e checksum
                payload = payload_and_checksum[:-2]
                checksum = payload_and_checksum[-2:]

                # - calcular o checksum do quadro recebido
                calculated_checksum = self.get_checksum(payload)
                if calculated_checksum != checksum:
                    corrupt_frame = True

                #   - descartar silenciosamente quadros com erro,
                if corrupt_frame:
                    print(f"O quadro {readed_protocol} foi corrompido")       
                    payload = b''
                    return self.recv()

                # - conferir a ordem dos quadros e descartar quadros repetidos.
                elif self.last_received_protocol + 1 != int.from_bytes(readed_protocol, "big"):
                    print("Duplicata ou fora de ordem")
                    payload = b''
                    return self.recv()
                
                # - enviar uma confirmação para quadros recebidos corretamente, 
                else:
                    ack = FLAG + ADDRESS + CONFIRMATION_CONTROL + checksum + readed_protocol + FLAG
                    print("Enviando ACK", ack)
                    self.last_received_protocol += 1
                    self.link.send(ack) 
            return payload         
        
        except TimeoutError: # use para tratar temporizações
            print("Timeout")
