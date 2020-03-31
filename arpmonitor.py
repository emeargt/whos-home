from scapy.all import *
import time, pygame, yaml, sys, os, threading
from pygame.locals import *

class Roommate:
    def __init__(self, name, mac, image, coord, shift, lock):
        self._name = name
        self._mac = mac
        self._coord = coord
        self._home_coord = [coord[0], coord[1]]
        self._shift_x = shift
        self._at_home = False
        self._pending_away = False

        print("Creating", self._name, "instance")

        self._image = pygame.image.load(os.path.join(image))
        self._image.convert()
        self._image = pygame.transform.scale(self._image, (105, 435))

    def set_at_home(self, val):
        self._at_home = val

    def get_at_home(self):
        return self._at_home

    def set_pending_away(self, val):
        self._pending_away = val

    def get_pending_away(self):
        return self._pending_away

    def get_mac(self):
        return self._mac

    def update_pos(self):
        if self._at_home and (not self.__at_home_coord()):
            self.__shift(-self._shift_x)
        elif (not self._at_home) and self.__at_home_coord():
            self.__shift(self._shift_x)

    def get_coord(self):
        return self._coord

    def get_x(self):
        return self._coord[0]

    def get_y(self):
        return self._coord[1]

    def get_image(self):
        return self._image

    def __at_home_coord(self):
        if self._coord == self._home_coord:
            return True
        else:
            return False

    def __grow(self):
        self._image = pygame.transform.scale(self._image, (105,435))

    def __move(self, coord):
        self._coord = coord

    def __shift(self, horiz):
        self._coord[0] += horiz

class CheckHomeThread(threading.Thread):
    def __init__(self, network, guys, lock, name='CheckHomeThread'):
        self._network = network
        self._roommates = guys
        self._lock = lock
        self._stop_event = threading.Event()
        self._wait = 10

        threading.Thread.__init__(self, name=name)

    def run(self):
        print(self.getName()," starts")
        macs=[]
        for guy in self._roommates:
            macs.append(guy.get_mac())
        while not self._stop_event.isSet():
            self._stop_event.wait(self._wait)
            print(self.getName() + ":", "Sending arp")
            ans, unans = srp(Ether(dst=macs)/ARP(op="who-has", pdst=self._network), timeout=10, verbose=0)
            for guy in self._roommates:
                for snd,rcv in ans:
                    if rcv.sprintf(r"%ARP.hwsrc%") == guy.get_mac():
                        if not guy.get_at_home():
                            print(self.getName() + ":", "Acquiring pos_lock")
                            self._lock.acquire()
                            guy.set_at_home(True)
                            self._lock.release()
                        guy.set_pending_away(False)
                        break
                    else:
                        guy.set_pending_away(True)
                if guy.get_pending_away() or len(ans) == 0:
                    if guy.get_at_home():
                        self._lock.acquire()
                        guy.set_at_home(False)
                        self._lock.release()
                    guy.set_pending_away(False)
        print(self.getName(), "ends")

    def join(self, timeout=None):
        self._stop_event.set()
        threading.Thread.join(self, timeout)

class PosThread(threading.Thread):
    def __init__(self, roommates, lock, wait, name='PosThread'):
        self._roommates = roommates
        self._lock = lock
        self._wait = wait
        self._stop_event = threading.Event()

        threading.Thread.__init__(self, name=name)

    def run(self):
        print(self.getName(), " starts")
        while not self._stop_event.isSet():
            self._stop_event.wait(self._wait)
            print(self.getName() + ":", "Acquiring pos_lock")
            self._lock.acquire()
            for guy in self._roommates:
                guy.update_pos()
            self._lock.release()
        print(self.getName(), "ends")

    def join(self, timeout=None):
        self._stop_event.set()
        threading.Thread.join(self, timeout)

def load_image(image, scale):
    ret = pygame.image.load(os.path.join(image))
    ret.convert()
    ret = pygame.transform.scale(ret, scale)
    return ret

def main():
    # Define background colour
    background_colour = (255, 243, 226)

    # Initialize display
    pygame.init()
    pygame.display.init()
    screen = pygame.display.set_mode([1920,1080], pygame.RESIZABLE)
    pygame.display.set_caption("Who's Home?")
    screen.fill(background_colour)
    pygame.display.flip()

    # Load sprites
    home = load_image("./graphics/home.png", (450,120))
    away = load_image("./graphics/away.png", (450,120))
    couch = load_image("./graphics/couch.png", (480,240))
    blackboard = load_image("./graphics/blackboard.png", (480,320))

    net_lock = threading.Lock()

    # Create roommatesi
    roommates = []
    with open(r'./yaml/info.yaml') as file:
        data = yaml.safe_load(file)
    for p in data.get("roommates").values():
        roommates.append(Roommate(p.get("name"), p.get("mac"), p.get("img"), p.get("coord"), p.get("shift"), net_lock))

    network = data.get("network")
    pos_lock = threading.Lock()
    t1 = PosThread(roommates, pos_lock, 10)
    t2 = CheckHomeThread(network, roommates, pos_lock)
    t1.start()
    t2.start()
    
    try:
        while True:
            for event in pygame.event.get():
                if event.type == pygame.KEYDOWN:
                    if event.key == K_RETURN:
                        pygame.display.toggle_fullscreen()
                    if event.key == K_ESCAPE:
                        pygame.display.quit()
                        t1.join()
                        t2.join()
                        raise KeyboardInterrupt
           
            screen.fill(background_colour)
            screen.blit(home, (263, 100))
            screen.blit(away, (1207, 100))
            screen.blit(couch, (248, 560))
            screen.blit(blackboard, (1192, 320))
            pos_lock.acquire()
            for guy in roommates:
                screen.blit(guy.get_image(), (guy.get_x(), guy.get_y()))
            pos_lock.release()
            pygame.display.flip()

    except KeyboardInterrupt:
        pass
    finally:
        print("Exiting")
        pygame.quit()

if __name__ == "__main__":
    main()
