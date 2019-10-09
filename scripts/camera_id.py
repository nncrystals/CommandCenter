from typing import List, Any

from genicam2.gentl import DeviceInfo
from harvesters.core import Harvester
import argparse
import os
import glob
from genicam2 import gentl, genapi

def get_cti_list():
    genicam_paths = os.environ["GENICAM_GENTL64_PATH"].split(":")
    cti_list = []
    for genicam_path in genicam_paths:
        glob_path = os.path.join(genicam_path, "*.cti")
        cti = glob.glob(glob_path)
        cti_list.extend(cti)
    return cti_list

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("--cti", required=False, help="Path to .cti file", default=None)
    args = parser.parse_args()

    cti = args.cti
    if cti is None:
        # get from env
        cti = get_cti_list()

    if isinstance(cti, str):
        cti = list(cti)

    driver = Harvester()
    for cti_path in cti:
        driver.add_cti_file(cti_path)
    print (cti)
    driver.update_device_info_list()
    info_list: List[DeviceInfo] = driver.device_info_list
    for i, info in enumerate(info_list):
        print(f"Device {i}: ID={info.id_}")



