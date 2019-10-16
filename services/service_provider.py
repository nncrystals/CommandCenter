import typing as T

from services import subjects, image_sources, analyzers
from services.image_encoder import ImageEncoder, JPEGEncoder
from services.result_processor import ResultProcessor
from services.result_saver import ResultSaver
from services.simex_io import SimexIO


class ServiceProvider(object):
    name_mapping: T.Dict[str, type] = {}
    default_type = None
    interface_typing: type = None
    _instance: object = None

    def __init__(self):
        pass

    def _create_instance(self, class_type: T.Union[str, type], *args, **kwargs):
        if isinstance(class_type, str):
            class_type = self.name_mapping[class_type]

        if not issubclass(class_type, self.interface_typing):
            raise RuntimeError(f"type {class_type.__name__} is not a subclass of {self.interface_typing.__name__}")

        return class_type(*args, **kwargs)

    def _unload_service(self):
        """
        clean up when the service should be unloaded or replaced.
        :return:
        """
        pass

    def _check_allow_unload(self) -> bool:
        return True

    def get_instance(self, *args, **kwargs) -> object:
        """
        Return instance or fail
        :return:
        """
        if self._instance is None:
            raise RuntimeError("instance is not created, cannot get_instance")

        return self._instance

    def get_or_create_instance(self, class_type, *args, **kwargs):
        """
        return instance or create
        :param class_type:
        :param args:
        :param kwargs:
        :return:
        """
        if class_type is None:
            if self.default_type is None:
                raise RuntimeError(
                    f"{type(self).__name__} does not have default_type. get_or_create_instance must be used with a type"
                )
            else:
                class_type = self.default_type

        if self._instance is None:
            self._assign_instance(self._create_instance(class_type, *args, **kwargs))

        return self._instance

    def replace_instance_with(self, new_object: T.Union[str, object], *args, **kwargs):
        """

        :param new_object: type name or the new instance. If the new instance is not a subclass of interface_typing, Exception will be thrown.
        :return:
        """

        if self._instance is not None:
            # Instance should be disposed.
            if not self._check_allow_unload():
                raise RuntimeError("The service is not at unload-able state")
            self._unload_service()

        if isinstance(new_object, str):
            class_type = self.name_mapping[new_object]
            self._assign_instance(self._create_instance(class_type, *args, **kwargs))

        elif isinstance(new_object, self.interface_typing):
            self._assign_instance(new_object)

    def _assign_instance(self, new_instance: object):
        if not isinstance(new_instance, self.interface_typing):
            raise TypeError(
                f"{type(new_instance).__name__} is not a subclass of {type(self.interface_typing).__name__}")
        self._instance = new_instance


class ImageSourceProvider(ServiceProvider):
    interface_typing = image_sources.ImageSource
    name_mapping = {
        "test": image_sources.MockImageSource,
        "harvesters": image_sources.HarvestersSource,
        "files": image_sources.MediaFileSource,
    }
    _instance: image_sources.ImageSource

    def __init__(self):
        super(ImageSourceProvider, self).__init__()

    def _unload_service(self):
        self._instance.stop()

    def _check_allow_unload(self) -> bool:
        return not self._instance.is_running()


class SubjectProvider(ServiceProvider):
    interface_typing = subjects.Subjects
    default_type = subjects.Subjects
    name_mapping = {
        "subjects": subjects.Subjects
    }


class AnalyzerProvider(ServiceProvider):
    interface_typing = analyzers.Analyzer
    name_mapping = {
        "remote": analyzers.RemoteAnalyzer,
        "test": analyzers.TestAnalyzer,
    }
    _instance: analyzers.Analyzer

    def _unload_service(self):
        self._instance.stop()

    def _check_allow_unload(self) -> bool:
        return not self._instance.is_running()


class ResultProcessorProvider(ServiceProvider):
    interface_typing = ResultProcessor
    default_type = ResultProcessor
    name_mapping = {
        "default": ResultProcessor
    }
    _instance: ResultProcessor

    def _unload_service(self):
        self._instance.finalize()


class ResultSaverProvider(ServiceProvider):
    interface_typing = ResultSaver
    default_type = ResultSaver
    name_mapping = {
        "default": ResultSaver
    }
    _instance: ResultSaver

    def _unload_service(self):
        self._instance.finalize()


class SimexIOProvider(ServiceProvider):
    interface_typing = SimexIO
    default_type = SimexIO
    name_mapping = {
        "default": SimexIO
    }
    _instance: SimexIO


class ImageEncoderProvider(ServiceProvider):
    interface_typing = ImageEncoder
    default_type = JPEGEncoder
    name_mapping = {
        "default": JPEGEncoder
    }
    _instance: ImageEncoder
