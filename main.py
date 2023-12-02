import socket
import threading
import time
from flags import flag

SERVER_IP = "127.0.0.1"
SERVER_PORT = 25005
CLIENT_IP = "127.0.0.1"
CLIENT_PORT = 25004

MAX_FRAGMENT_SIZE = 1400
MAX_FRAGMENT_SIZE_NO_HEADER = MAX_FRAGMENT_SIZE - 8

STOP_EVENT = threading.Event()


# 2-KA (Keep alive request)
# 3-IA (I'm alive response)
# 4-NACK (negative ACK)
# 5-ACK (ACK)
# 6-FIN (finalised)
# 7-SW (switch roles)
# 8-INFO (i guess)
# 9-DATA
# 10- MSG

# FLAG 1B | ČÍSLO FRAGMENTU 3B | CRC32 4B | DATA

def crc32(data):
    POLYNOMIAL = 0xEDB88320
    crc = 0xFFFFFFFF

    for byte in data:
        crc ^= byte
        for _ in range(8):
            crc = (crc >> 1) ^ POLYNOMIAL if crc & 1 else crc >> 1

    return crc ^ 0xFFFFFFFF


class Server:

    def __init__(self):
        print((SERVER_IP, SERVER_PORT))

        self.addr = None
        self.ka_time = None
        self.server = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.server.bind((SERVER_IP, SERVER_PORT))

        self.thread_prijimac = threading.Thread(target=self.recieve)
        self.thread_vysielac = threading.Thread(target=self.run)
        self.thread_keep_alive = threading.Thread(target=self.keep_alive)

        self.stop = 0

        self.thread_prijimac.start()
        self.thread_vysielac.start()
        self.thread_keep_alive.start()

        self.thread_prijimac.join()
        self.thread_vysielac.join()
        self.thread_keep_alive.join()

        self.server.close()

        self.stop = 1

    def run(self):
        vyber = None
        while not STOP_EVENT.is_set():
            while vyber != 1 or vyber != 2 or vyber != 3:
                try:
                    vyber = int(input("1)Zmeniť rolu\n2)Ukončiť\n+++++++++++++++++++++++++++++++++++++++++++++++++\n"))
                except:
                    exit(0)

            if vyber == 1:
                pass
            elif vyber == 2:
                pass

    def recieve(self):
        self.server.settimeout(10)
        global MAX_FRAGMENT_SIZE
        posledny_fragment_id = None

        zasobnik = []

        while not STOP_EVENT.is_set():
            try:
                sprava, self.addr = self.server.recvfrom(MAX_FRAGMENT_SIZE)
                print(sprava)

                if int.from_bytes(sprava, byteorder="big") == flag.KA.value:
                    self.ka_time = time.time()
                    self.server.sendto(flag.IA.value.to_bytes(1, byteorder="big"), self.addr)  # ia

                elif sprava[0] == flag.INFO.value:

                    posledny_fragment_id = int.from_bytes(sprava[1:4], byteorder="big") - 1
                    print("Posledny frame ID: " + str(posledny_fragment_id))

                elif sprava[0] == flag.MSG.value:
                    print("Pooper")

                    print(int.from_bytes(sprava[1:4], byteorder="big"))
                    if not posledny_fragment_id == None and posledny_fragment_id == int.from_bytes(sprava[1:4],
                                                                                                   byteorder="big"):
                        if crc32(sprava[8:MAX_FRAGMENT_SIZE]) == int.from_bytes(sprava[4:8], byteorder="big"):
                            print("Zasobnik appened 1")

                            if  sprava[8:] not in zasobnik:
                                zasobnik.append(sprava[8:])

                                novy_flag = flag.ACK.value.to_bytes(1, byteorder="big")
                                hlavicka = novy_flag
                                self.server.sendto(hlavicka, (CLIENT_IP, CLIENT_PORT))

                                self.zobraz_spravu(zasobnik)
                                continue

                        else:
                            print("Znova posielanie dat 1")
                            novy_flag = flag.NACK.value.to_bytes(1, byteorder="big")
                            hlavicka = novy_flag

                            self.server.sendto(hlavicka, (CLIENT_IP, CLIENT_PORT))
                    else:
                        if sprava[8:] in zasobnik:
                            pass
                        else:
                            if crc32(sprava[8:MAX_FRAGMENT_SIZE]) == int.from_bytes(sprava[4:8], byteorder="big"):
                                if not sprava[8:0] in zasobnik:
                                    zasobnik.append(sprava[8:])

                                print("Zasobnik appened 2")

                                novy_flag = flag.ACK.value.to_bytes(1, byteorder="big")
                                hlavicka = novy_flag
                                self.server.sendto(hlavicka, (CLIENT_IP, CLIENT_PORT))

                            else:
                                novy_flag = flag.NACK.value.to_bytes(1, byteorder="big")
                                hlavicka = novy_flag

                                print("Znova posielanie dat 2")

                                self.server.sendto(hlavicka, (CLIENT_IP, CLIENT_PORT))

            except socket.timeout as e:
                STOP_EVENT.set()
                exit(0)

    def zobraz_spravu(self, zasobnik):
        sprava = ""

        for data in zasobnik:
            sprava += data.decode("utf-8")

        print(sprava)

    def zmen_rolu(self):
        pass

    def keep_alive(self):
        while not STOP_EVENT.is_set():
            if self.ka_time is not None and time.time() - self.ka_time > 1200:
                print("10s nebolo ka...")
                STOP_EVENT.set()
                exit(0)
                # plus nejak to skoncit


# dobre

class Client:
    global STOP_EVENT
    global MAX_FRAGMENT_SIZE
    global MAX_FRAGMENT_SIZE_NO_HEADER
    data_na_poslanie = []
    odpoved = False
    ack_counter = 3

    def __init__(self):
        print((CLIENT_IP, CLIENT_PORT))

        self.ka_time = None
        self.client = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.client.bind((CLIENT_IP, CLIENT_PORT))
        self.thread_prijimac = threading.Thread(target=self.recieve)
        self.thread_vysielac = threading.Thread(target=self.run)
        self.thread_keep_alive = threading.Thread(target=self.keep_alive)

        self.stop = 0

        self.thread_prijimac.start()
        self.thread_vysielac.start()
        self.thread_keep_alive.start()

        self.thread_prijimac.join()
        self.thread_vysielac.join()
        self.thread_keep_alive.join()

        self.client.close()

        self.stop = 1

    def run(self):
        vyber = None
        while not STOP_EVENT.is_set():
            while vyber != 1 and vyber != 2 and vyber != 3 and vyber != 4 and vyber != 5:
                try:
                    vyber = int(input(
                        "1)Poslať správu\n2)Poslať súbor\n3)Zmeniť rolu\n4)Testovať chybu\n5)Ukončiť\n+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++\n"))
                except:
                    exit(0)

            if vyber == 1:
                self.posli_spravu()
                vyber = None
            elif vyber == 2:
                pass
            elif vyber == 3:
                pass
            elif vyber == 4:
                pass
            elif vyber == 5:
                pass

    def recieve(self):
        while not STOP_EVENT.is_set():
            try:
                sprava, _ = self.client.recvfrom(MAX_FRAGMENT_SIZE)
                sprava = int.from_bytes(sprava, byteorder="big")
                print(sprava)

                try:
                    if self.pocuvaj_ack == True and sprava != flag.ACK.value:
                        self.ack_counter -= 1
                except:
                    print("tu je nas errorko zababuseny")
                    pass


                if sprava == flag.IA.value:  # ia
                    self.ka_time = time.time()

                elif sprava == flag.NACK.value:  # nack
                    self.odpoved = False
                    pass
                elif sprava == flag.ACK.value:  # ack

                    self.odpoved = True
                    pass
                elif sprava == flag.FIN.value:  # fin
                    # koncime spojenie
                    pass
                elif sprava == flag.SW.value:  # sw
                    # menime rolicky rohlicky
                    pass
            except:
                print("Pripojenie zlyhalo ...")
                STOP_EVENT.set()
                exit(0)

    def zmen_rolu(self):
        pass

    def keep_alive(self):
        while not STOP_EVENT.is_set():
            if self.ka_time is not None and time.time() - self.ka_time > 1200:
                print("10s nebolo ia...")
                STOP_EVENT.is_set()
                return
                # plus nejak to skoncit

            self.client.sendto(flag.KA.value.to_bytes(1, byteorder="big"), (SERVER_IP, SERVER_PORT))  # ka
            time.sleep(2)

    # patino idem na wc - uži si to baby

    def posli_spravu(self):
        self.data_na_poslanie = []
        id = 0

        sprava = input("Napíšte správu - nejakú zádušnú: ")
        sprava = sprava.encode('utf-8')

        for i in range(0, len(sprava), MAX_FRAGMENT_SIZE_NO_HEADER):
            fragment = sprava[i:i + MAX_FRAGMENT_SIZE_NO_HEADER]

            fragment = self.pridaj_hlavicku(fragment, id, flag.MSG.value) + fragment
            id += 1

            self.data_na_poslanie.append(fragment)

        flag_info = flag.INFO.value.to_bytes(1, byteorder="big")
        posledny_fragment_id = id.to_bytes(3, byteorder="big")

        naloz = flag_info + posledny_fragment_id

        self.client.sendto(naloz, (SERVER_IP, SERVER_PORT))

        self.posli_fragmenty()

    def posli_suborik(self):
        pass

    def pokaz_fragment(self):  # hej??
        pass

    def posli_fragmenty(self):

        for fragment in self.data_na_poslanie:
            self.pocuvaj_ack = True

            try:
                while self.odpoved != True and self.ack_counter > 0:
                    self.client.sendto(fragment, (SERVER_IP, SERVER_PORT))

                    if self.ack_counter==0:
                        return
                    else:
                        self.odpoved = False
                        self.ack_counter = 3
                        self.pocuvaj_ack=False

            except socket.timeout:
                print("Neprichádzajú žiadne ACK")

    def pridaj_hlavicku(self, data, id, typ_prenosu):
        flag = typ_prenosu.to_bytes(1, byteorder="big")
        id = id.to_bytes(3, byteorder="big")
        crc = crc32(data).to_bytes(4, byteorder="big")

        hlavicka = flag + id + crc

        return hlavicka


def ja_neviem_more():
    # pisem po slovensky a mam to hlboko v píííííííííííííííči

    volba = 0
    while volba != 3:
        print("1 SERVER\n2 CLIENT\n3 EXIT\n")
        while volba != 1 or volba != 2:
            try:
                volba = int(input("Zvol si svoju velectenu ulohu:\n"))
            except:
                return

            if volba == 1:
                server = Server()
                while server.stop != 1:
                    pass
                volba = 0
                # urobime serverik
            elif volba == 2:
                client = Client()
                while client.stop != 1:
                    pass
                volba = 0

                # urobime clientika


ja_neviem_more()
