import rx
from rx import disposable

from services.image_sources import ImageSource
from services.service_provider import ImageSourceProvider
from services.sop import register_sop, BaseSOP


@register_sop
class NoDilutionSOP(BaseSOP):
    def __init__(self) -> None:
        super().__init__()

    def exec(self) -> rx.Observable:
        return rx.create(self._subscribe)

    @staticmethod
    def get_name() -> str:
        return "No Dilution (Continuous)"

    def _subscribe(self, observer, scheduler=None):
        subscription = disposable.Disposable()
        def action(sc, state=None):
            self.logger.info("Start continuous SOP")
            self.logger.info("Starting image source")

            image_source: ImageSource = ImageSourceProvider().get_instance()
            image_source.start()

            self.logger.info("Starting analyzer")

        scheduler.schedule(action)
        return subscription

