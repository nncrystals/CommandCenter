import time

from harvesters.core import Harvester

def process(ia):
    ia.fetch_buffer().queue()
    print("buffer")

if __name__ == '__main__':
    h = Harvester()
    h.add_cti_file("/opt/mvIMPACT_Acquire/lib/x86_64/mvGenTLProducer.cti")
    h.update_device_info_list()

    for i in range(10):
        ia = h.create_image_acquirer(id_="VID1AB2_PID0001_671090012")
        print(f"{i}:Created")
        ia.on_new_buffer_arrival = lambda: process(ia)
        ia.start_image_acquisition()
        print(f"{i}:started")

        time.sleep(2)

        ia.stop_image_acquisition()
        print(f"{i}:stopped")

        ia.destroy()
        print(f"{i}:Destroyed")