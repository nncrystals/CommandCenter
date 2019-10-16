"""
Encode ndarray into bytes
"""
import numpy as np
import turbojpeg as tj
from services import config
import sys


class ImageEncoder(object):
    def encode(self, image: np.ndarray):
        pass


class JPEGEncoder(ImageEncoder):
    config_prefix = "JPEGEncoder"

    def __init__(self):
        self.config = config.SettingAccessor(self.config_prefix)
        self.encoder = tj.TurboJPEG(self.config["turbo_jpeg_library"])

    @staticmethod
    @config.DefaultSettingRegistration(config_prefix)
    def default_settings(config_prefix):
        if sys.platform == "linux":
            default_path = "/usr/lib/x86_64-linux-gnu/libturbojpeg.so.0"
        elif sys.platform == "win32":
            default_path = "C:\\libjpeg-turbo64\\bin\\turbojpeg.dll"
        else:
            default_path = ""
        config.default_settings(config_prefix, [
            config.SettingRegistry("turbo_jpeg_library", default_path, type="str", title="Path to TurboJPEG library"),
            config.SettingRegistry("quality", 90, type="int", title="JPEG encoding quality"),
        ])

    def encode(self, image: np.ndarray):
        if len(image.shape) == 2:
            return self.encoder.encode(image[:, :, np.newaxis], quality=self.config["quality"],
                                       jpeg_subsample=tj.TJSAMP_GRAY, pixel_format=tj.TJPF_GRAY)

        else:
            raise NotImplementedError("Multi-channel image encoding is not supported.")
